import logging
import math
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.constants import FIRST_PAGE, PRICE_DIGITS, SECONDS_PER_MINUTE
from app.core.database import WorkerSessionLocal, WriteSessionLocal
from app.core.exceptions import BadRequestException, ConflictException, NotFoundException
from app.core.scouting.enrichment.website import EnrichmentError, WebsiteContacts, WebsiteEnricher
from app.core.scouting.sources.base import KIND_DISCOVERY, Source, SourceAuthError, SourceError
from app.core.scouting.sources.registry import CATALOG, ENRICHMENT_KEY, get_source_info
from app.core.scouting.types import RawBusiness, SearchArea, SearchQuery
from app.features.businesses import ingest as businesses_ingest
from app.features.businesses.ingest import IngestContext, ProfileScoring
from app.features.businesses.models import Business, SourceRecord
from app.features.geographies.models import Geography, GeographyLevel
from app.features.profiles.models import Profile, ProfileSearchTerm
from app.features.runs.models import Run, RunStatus, RunTask, TaskStatus
from app.features.runs.schemas import RunCreate
from app.features.runs.worker import worker
from app.features.sheets import service as sheets_service
from app.features.sources import service as sources_service

TASK_ERROR_MAX_LENGTH = 500


DEFAULT_LIMIT = 10
DEFAULT_TASKS_LIMIT = 50


logger = logging.getLogger(__name__)

ENRICHMENT_RECHECK_DAYS = 30

SourceBuilder = Callable[[Session, list[str]], dict[str, Source]]
EnricherFactory = Callable[[], WebsiteEnricher]

_SEARCH_STAT_FIELDS = (
    "tasks_done", "tasks_failed", "found", "new", "merged", "blocked",
    "with_phone", "with_website", "with_email", "errors", "requests",
)
_ENRICH_STAT_FIELDS = ("visited", "with_email", "with_whatsapp", "with_social", "blocked_by_robots", "failed")


def _now() -> datetime:
    return datetime.now(UTC)


@dataclass(frozen=True)
class TaskPlan:
    source_key: str
    geography: Geography
    term: ProfileSearchTerm

    @property
    def cache_key(self) -> tuple[str, int, str, str]:
        return (self.source_key, self.geography.id, self.term.text, self.term.language)


def _term_supported(source_key: str, term: ProfileSearchTerm) -> bool:
    return get_source_info(source_key).supports_term(term.osm_filter)


def _filter_dependent_source_names() -> str:
    names = [info.name for info in CATALOG if info.kind == KIND_DISCOVERY and info.supports_filter is not None]
    return ", ".join(names[:-1]) + f" and {names[-1]}" if len(names) > 1 else "".join(names)


def _resolve_cities(db: Session, geography_ids: list[int]) -> list[Geography]:
    found = db.query(Geography).filter(Geography.id.in_(geography_ids)).all()
    missing = set(geography_ids) - {geography.id for geography in found}
    if missing:
        raise NotFoundException(f"Location {sorted(missing)[0]} not found")

    cities: dict[int, Geography] = {}
    frontier = list(found)
    while frontier:
        geography = frontier.pop()
        if geography.level == GeographyLevel.CITY.value:
            cities[geography.id] = geography
        else:
            frontier.extend(geography.children)

    if not cities:
        raise BadRequestException("The selected locations don't contain any cities")
    return sorted(cities.values(), key=lambda city: (city.name, city.id))


def _validated_source_keys(db: Session, source_keys: list[str]) -> list[str]:
    available = set(sources_service.get_available_discovery_keys(db))
    for key in source_keys:
        info = get_source_info(key)
        if info is None or info.kind != KIND_DISCOVERY:
            raise BadRequestException(f"'{key}' is not a source that can be searched")
        if key not in available:
            if info.requires_api_key:
                reason = "is switched off or has no API key"
            elif info.requires_dataset:
                reason = "is switched off or its data has not been downloaded"
            else:
                reason = "is switched off"
            raise BadRequestException(f"{info.name} {reason}")
    return source_keys


def _plan(db: Session, run_in: RunCreate) -> tuple[Profile, list[Geography], list[TaskPlan]]:
    profile = db.query(Profile).filter(Profile.id == run_in.profile_id).first()
    if profile is None:
        raise NotFoundException("Profile not found")
    if not profile.is_active:
        raise BadRequestException("This profile is switched off")

    cities = _resolve_cities(db, run_in.geography_ids)
    source_keys = _validated_source_keys(db, run_in.source_keys)

    if run_in.segment_slugs is not None:
        unknown = set(run_in.segment_slugs) - {segment.slug for segment in profile.segments}
        if unknown:
            raise BadRequestException(f"Unknown segment '{sorted(unknown)[0]}'")

    terms = [
        term for term in profile.search_terms
        if term.is_active and (run_in.segment_slugs is None or term.segment_slug in run_in.segment_slugs)
    ]
    plans = [
        TaskPlan(source_key, city, term)
        for source_key in source_keys
        for city in cities
        for term in terms
        if _term_supported(source_key, term)
    ]
    if not plans:
        raise BadRequestException(
            "Nothing to search: no active search terms fit the chosen sources "
            f"({_filter_dependent_source_names()} only search terms that have an OSM filter)"
        )
    return profile, cities, plans


def _recently_searched(db: Session, plans: list[TaskPlan]) -> set[tuple[str, int, str, str]]:
    cutoff = _now() - timedelta(days=settings.RUN_TASK_CACHE_DAYS)
    rows = (
        db.query(RunTask.source_key, RunTask.geography_id, RunTask.term_text, RunTask.term_language)
        .filter(
            RunTask.status == TaskStatus.DONE.value,
            RunTask.finished_at >= cutoff,
            RunTask.source_key.in_({plan.source_key for plan in plans}),
            RunTask.geography_id.in_({plan.geography.id for plan in plans}),
        )
        .distinct()
        .all()
    )
    return {tuple(row) for row in rows}


def _too_many_searches_message(count: int) -> str:
    return (
        f"That would be {count} searches, and the limit for one run is {settings.RUN_MAX_TASKS}. "
        "Pick fewer cities, segments or sources."
    )


def _requests_possible(entry: dict) -> int:
    searches = entry["tasks"] - entry["tasks_skipped"]
    return searches * get_source_info(entry["source_key"]).max_requests_per_search


def estimate_run(db: Session, run_in: RunCreate) -> dict:
    profile, cities, plans = _plan(db, run_in)
    searched = set() if run_in.refresh else _recently_searched(db, plans)

    by_source = []
    paid_requests_max = 0
    paid_cost_max = 0.0
    seconds = 0.0
    tasks_to_run_total = 0

    for source_key in run_in.source_keys:
        info = get_source_info(source_key)
        source_plans = [plan for plan in plans if plan.source_key == source_key]
        skipped = sum(1 for plan in source_plans if plan.cache_key in searched)
        to_run = len(source_plans) - skipped
        tasks_to_run_total += to_run

        max_requests = None
        cost = None
        if info.is_paid:
            max_requests = to_run * info.max_requests_per_search
            if run_in.max_paid_requests is not None:
                max_requests = min(max_requests, run_in.max_paid_requests)
            cost = round(max_requests * info.cost_per_request(settings), PRICE_DIGITS)
            paid_requests_max += max_requests
            paid_cost_max += max_requests * info.cost_per_request(settings)
        seconds += to_run * info.search_seconds(settings)

        by_source.append(
            {
                "source_key": source_key,
                "name": info.name,
                "is_paid": info.is_paid,
                "tasks": len(source_plans),
                "tasks_skipped": skipped,
                "max_requests": max_requests,
                "estimated_cost_usd": cost,
            }
        )

    tasks_skipped = len(plans) - tasks_to_run_total
    allowed = len(plans) <= settings.RUN_MAX_TASKS
    warnings: list[str] = []
    if not allowed:
        warnings.append(_too_many_searches_message(len(plans)))
    if tasks_skipped:
        verb = "search was" if tasks_skipped == 1 else "searches were"
        warnings.append(
            f"{tasks_skipped} {verb} completed recently and will be skipped "
            "(turn on refresh to repeat them)."
        )
    for entry in by_source:
        if not entry["is_paid"]:
            continue
        if run_in.max_paid_requests is None:
            warnings.append(
                f"No request cap is set: {entry['name']} may make up to {entry['max_requests']} billable "
                f"requests (about ${entry['estimated_cost_usd']:.2f} at the configured rate)."
            )
        elif _requests_possible(entry) > run_in.max_paid_requests:
            warnings.append(
                f"The cap of {run_in.max_paid_requests} requests may stop {entry['name']} before every search runs."
            )

    return {
        "profile_name": profile.name,
        "cities": len(cities),
        "tasks_total": len(plans),
        "tasks_to_run": tasks_to_run_total,
        "tasks_skipped": tasks_skipped,
        "by_source": by_source,
        "paid_requests_max": paid_requests_max,
        "estimated_cost_usd": round(paid_cost_max, PRICE_DIGITS),
        "estimated_minutes": math.ceil(seconds / SECONDS_PER_MINUTE) if tasks_to_run_total else 0,
        "allowed": allowed,
        "warnings": warnings,
    }


def create_run(db: Session, run_in: RunCreate, created_by_id: int) -> Run:
    profile, cities, plans = _plan(db, run_in)
    if len(plans) > settings.RUN_MAX_TASKS:
        raise BadRequestException(_too_many_searches_message(len(plans)))

    searched = set() if run_in.refresh else _recently_searched(db, plans)
    run = Run(
        profile_id=profile.id,
        profile_name=profile.name,
        created_by_id=created_by_id,
        status=RunStatus.QUEUED.value,
        source_keys=run_in.source_keys,
        segment_slugs=run_in.segment_slugs,
        enrich_websites=run_in.enrich_websites,
        refresh=run_in.refresh,
        max_paid_requests=run_in.max_paid_requests,
        tasks_total=len(plans),
        tasks_skipped=sum(1 for plan in plans if plan.cache_key in searched),
        stats={},
    )
    run.geographies = cities
    db.add(run)
    db.flush()

    for plan in plans:
        already_done = plan.cache_key in searched
        db.add(
            RunTask(
                run_id=run.id,
                source_key=plan.source_key,
                geography_id=plan.geography.id,
                geography_name=plan.geography.name,
                search_term_id=plan.term.id,
                term_text=plan.term.text,
                term_language=plan.term.language,
                segment_slug=plan.term.segment_slug,
                status=TaskStatus.SKIPPED.value if already_done else TaskStatus.PENDING.value,
                error="Searched recently; skipped" if already_done else None,
            )
        )
    db.commit()
    db.refresh(run)
    worker.enqueue(run.id)
    return run


def get_runs(db: Session, page: int = FIRST_PAGE, limit: int = DEFAULT_LIMIT, status: RunStatus | None = None) -> dict:
    query = db.query(Run)
    if status is not None:
        query = query.filter(Run.status == status.value)

    total_count = query.count()
    runs = query.order_by(Run.id.desc()).offset((page - 1) * limit).limit(limit).all()
    return {"data": runs, "count": total_count}


def get_run_by_id(db: Session, run_id: int) -> Run:
    run = db.query(Run).filter(Run.id == run_id).first()
    if not run:
        raise NotFoundException("Run not found")
    return run


def get_run_tasks(
    db: Session, run_id: int, page: int = FIRST_PAGE, limit: int = DEFAULT_TASKS_LIMIT, status: TaskStatus | None = None
) -> dict:
    get_run_by_id(db, run_id)
    query = db.query(RunTask).filter(RunTask.run_id == run_id)
    if status is not None:
        query = query.filter(RunTask.status == status.value)

    total_count = query.count()
    tasks = query.order_by(RunTask.id).offset((page - 1) * limit).limit(limit).all()
    return {"data": tasks, "count": total_count}


def cancel_run(db: Session, run_id: int) -> Run:
    run = get_run_by_id(db, run_id)
    if run.status == RunStatus.QUEUED.value:
        pending = db.query(RunTask).filter(RunTask.run_id == run.id, RunTask.status == TaskStatus.PENDING.value)
        run.tasks_skipped += pending.update(
            {"status": TaskStatus.SKIPPED.value, "error": "Run cancelled"}, synchronize_session=False
        )
        run.status = RunStatus.CANCELLED.value
        run.finished_at = _now()
    elif run.status == RunStatus.RUNNING.value:
        run.status = RunStatus.CANCELLING.value
    elif run.status != RunStatus.CANCELLING.value:
        raise ConflictException("This run has already finished")
    db.commit()
    db.refresh(run)
    return run


def resume_run(db: Session, run_id: int) -> Run:
    run = get_run_by_id(db, run_id)
    has_pending = (
        db.query(RunTask.id).filter(RunTask.run_id == run.id, RunTask.status == TaskStatus.PENDING.value).first()
    )
    if run.status != RunStatus.FAILED.value or not has_pending:
        raise ConflictException("Only an interrupted run with searches left can be resumed")

    run.status = RunStatus.QUEUED.value
    run.error = None
    run.finished_at = None
    db.commit()
    db.refresh(run)
    worker.enqueue(run.id)
    return run


def _empty_stats(fields: tuple[str, ...]) -> dict[str, int]:
    return {field: 0 for field in fields}


def _snapshot(stats: dict[str, dict[str, int]]) -> dict[str, dict[str, int]]:
    return {key: dict(values) for key, values in stats.items()}


_profile_scoring = businesses_ingest.build_profile_scoring


def _default_enricher() -> WebsiteEnricher:
    return WebsiteEnricher(user_agent=sources_service.user_agent())


def execute_run(
    db: Session,
    run_id: int,
    *,
    source_builder: SourceBuilder | None = None,
    enricher_factory: EnricherFactory | None = None,
) -> Run | None:
    run = db.get(Run, run_id)
    if run is None or run.status != RunStatus.QUEUED.value:
        return run

    run.status = RunStatus.RUNNING.value
    run.started_at = _now()
    db.commit()

    profile = db.get(Profile, run.profile_id) if run.profile_id else None
    if profile is None:
        return _finish(db, run, RunStatus.FAILED, "The profile for this run no longer exists")
    scoring = _profile_scoring(profile)

    try:
        sources = (source_builder or sources_service.build_sources)(db, list(run.source_keys))
    except ValueError as exc:
        return _finish(db, run, RunStatus.FAILED, str(exc))

    stats: dict[str, dict[str, int]] = {key: _empty_stats(_SEARCH_STAT_FIELDS) for key in run.source_keys}
    _run_search_tasks(db, run, scoring, sources, stats)

    if (
        run.status != RunStatus.CANCELLING.value
        and run.enrich_websites
        and sources_service.is_enrichment_enabled(db)
    ):
        _enrich_websites(db, run, scoring, enricher_factory or _default_enricher, stats)

    return _finalize(db, run, stats)


def _run_search_tasks(
    db: Session, run: Run, scoring: ProfileScoring, sources: dict[str, Source], stats: dict[str, dict[str, int]]
) -> None:
    tasks = (
        db.query(RunTask)
        .filter(RunTask.run_id == run.id, RunTask.status == TaskStatus.PENDING.value)
        .order_by(RunTask.id)
        .all()
    )
    unusable_sources: dict[str, str] = {}

    for task in tasks:
        db.refresh(run, ["status"])
        if run.status == RunStatus.CANCELLING.value:
            return
        try:
            _run_task(db, run, task, scoring, sources, stats, unusable_sources)
        except Exception:
            logger.exception("Run %s: task %s failed unexpectedly", run.id, task.id)
            db.rollback()
            _fail_task(db, run, db.get(RunTask, task.id), "Unexpected error (see the server log)", stats)


def _run_task(
    db: Session,
    run: Run,
    task: RunTask,
    scoring: ProfileScoring,
    sources: dict[str, Source],
    stats: dict[str, dict[str, int]],
    unusable_sources: dict[str, str],
) -> None:
    info = get_source_info(task.source_key)

    if task.source_key in unusable_sources:
        return _skip_task(db, run, task, unusable_sources[task.source_key])

    remaining = None
    if info.is_paid and run.max_paid_requests is not None:
        remaining = run.max_paid_requests - run.paid_requests_used
        if remaining <= 0:
            return _skip_task(db, run, task, "Request cap reached")

    source = sources.get(task.source_key)
    geography = db.get(Geography, task.geography_id) if task.geography_id else None
    term = db.get(ProfileSearchTerm, task.search_term_id) if task.search_term_id else None
    if source is None or geography is None or term is None:
        return _fail_task(db, run, task, "The source, location or search term is no longer available", stats)

    task.status = TaskStatus.RUNNING.value
    task.started_at = _now()
    db.commit()

    query = SearchQuery(
        text=term.text,
        area=SearchArea(
            latitude=geography.latitude,
            longitude=geography.longitude,
            radius_km=geography.radius_km,
            name=geography.name,
            bbox=tuple(geography.bbox) if geography.bbox else None,
        ),
        language=term.language,
        osm_filter=term.osm_filter,
    )

    try:
        result = source.search(query, max_requests=remaining)
    except SourceAuthError as exc:
        unusable_sources[task.source_key] = f"{info.name} rejected the request: {exc}"
        run.error = run.error or unusable_sources[task.source_key]
        return _fail_task(db, run, task, str(exc), stats)
    except SourceError as exc:
        return _fail_task(db, run, task, str(exc), stats)

    context = IngestContext(
        run_id=run.id,
        geography_id=geography.id,
        hint_segment_slug=task.segment_slug,
        now=_now(),
        profile=scoring,
    )
    counts = _ingest_results(db, result.businesses, context)

    source_stats = stats[task.source_key]
    for field in ("found", "new", "merged", "blocked", "with_phone", "with_website", "with_email", "errors"):
        source_stats[field] += counts[field]
    source_stats["tasks_done"] += 1
    source_stats["requests"] += result.requests_made

    task.status = TaskStatus.DONE.value
    task.results_count = len(result.businesses)
    task.new_count = counts["new"]
    task.requests_made = result.requests_made
    task.error = "Stopped early: request cap reached" if result.truncated else None
    task.finished_at = _now()
    run.tasks_done += 1
    if info.is_paid:
        run.paid_requests_used += result.requests_made
    run.stats = _snapshot(stats)
    db.commit()


def _ingest_results(db: Session, businesses: list[RawBusiness], context: IngestContext) -> dict[str, int]:
    return businesses_ingest.ingest_records(db, ((raw, context) for raw in businesses))


def _fail_task(db: Session, run: Run, task: RunTask, message: str, stats: dict[str, dict[str, int]]) -> None:
    task.status = TaskStatus.FAILED.value
    task.error = message[:TASK_ERROR_MAX_LENGTH]
    task.finished_at = _now()
    run.tasks_failed += 1
    stats[task.source_key]["tasks_failed"] += 1
    run.stats = _snapshot(stats)
    db.commit()


def _skip_task(db: Session, run: Run, task: RunTask, reason: str) -> None:
    task.status = TaskStatus.SKIPPED.value
    task.error = reason
    task.finished_at = _now()
    run.tasks_skipped += 1
    db.commit()


def _fetch_contacts(enricher: WebsiteEnricher, url: str) -> tuple[WebsiteContacts | None, str | None]:
    try:
        return enricher.enrich(url), None
    except EnrichmentError as exc:
        return None, str(exc)
    except Exception as exc:
        logger.exception("Unexpected error reading %s", url)
        return None, exc.__class__.__name__


def _enrich_websites(
    db: Session, run: Run, scoring: ProfileScoring, enricher_factory: EnricherFactory, stats: dict[str, dict[str, int]]
) -> None:
    cutoff = _now() - timedelta(days=ENRICHMENT_RECHECK_DAYS)
    touched_by_run = select(SourceRecord.business_id).where(SourceRecord.run_id == run.id)
    targets = (
        db.query(Business.id, Business.website)
        .filter(
            Business.id.in_(touched_by_run),
            Business.website.isnot(None),
            or_(Business.enriched_at.is_(None), Business.enriched_at < cutoff),
        )
        .all()
    )
    run.enrich_total = len(targets)
    db.commit()
    if not targets:
        return

    enrich_stats = stats.setdefault(ENRICHMENT_KEY, _empty_stats(_ENRICH_STAT_FIELDS))
    enricher = enricher_factory()

    with ThreadPoolExecutor(max_workers=settings.ENRICHMENT_CONCURRENCY) as pool:
        futures = {pool.submit(_fetch_contacts, enricher, url): business_id for business_id, url in targets}
        for future in as_completed(futures):
            db.refresh(run, ["status"])
            if run.status == RunStatus.CANCELLING.value:
                for pending in futures:
                    pending.cancel()
                break

            contacts, error = future.result()
            business = db.get(Business, futures[future])
            business.enriched_at = _now()
            enrich_stats["visited"] += 1

            if contacts is None:
                enrich_stats["failed"] += 1
                logger.info("Run %s: enrichment skipped for business %s: %s", run.id, business.id, error)
            else:
                enrich_stats["blocked_by_robots"] += contacts.blocked_by_robots
                enrich_stats["with_email"] += bool(contacts.emails)
                enrich_stats["with_whatsapp"] += bool(contacts.whatsapp)
                enrich_stats["with_social"] += bool(contacts.facebook or contacts.instagram)
                added = businesses_ingest.add_enrichment_contacts(
                    db, business,
                    emails=contacts.emails, phones=contacts.phones, whatsapp=contacts.whatsapp,
                    facebook=contacts.facebook, instagram=contacts.instagram, source_key=ENRICHMENT_KEY,
                )
                if added:
                    businesses_ingest.rescore_business(db, business, scoring)

            run.enrich_done += 1
            run.stats = _snapshot(stats)
            db.commit()


def _finalize(db: Session, run: Run, stats: dict[str, dict[str, int]]) -> Run:
    run.stats = _snapshot(stats)

    leftover = db.query(RunTask).filter(RunTask.run_id == run.id, RunTask.status == TaskStatus.PENDING.value)
    cancelled = run.status == RunStatus.CANCELLING.value
    if cancelled:
        run.tasks_skipped += leftover.update(
            {"status": TaskStatus.SKIPPED.value, "error": "Run cancelled"}, synchronize_session=False
        )

    if cancelled:
        return _finish(db, run, RunStatus.CANCELLED)
    if run.tasks_done == 0 and run.tasks_failed > 0:
        first_error = (
            db.query(RunTask.error)
            .filter(RunTask.run_id == run.id, RunTask.status == TaskStatus.FAILED.value)
            .order_by(RunTask.id)
            .first()
        )
        return _finish(db, run, RunStatus.FAILED, run.error or (first_error[0] if first_error else None))
    return _finish(db, run, RunStatus.COMPLETED)


def _finish(db: Session, run: Run, status: RunStatus, error: str | None = None) -> Run:
    run.status = status.value
    run.finished_at = _now()
    if error:
        run.error = error
    db.commit()
    db.refresh(run)
    return run


def run_in_new_session(run_id: int) -> None:
    db = WorkerSessionLocal()
    try:
        execute_run(db, run_id)
    except Exception:
        logger.exception("Run %s failed", run_id)
        db.rollback()
        run = db.get(Run, run_id)
        if run is not None and run.is_active:
            _finish(db, run, RunStatus.FAILED, "Unexpected error (see the server log)")
    finally:
        db.close()
        sheets_service.notify_changed()


def recover_interrupted_runs(db: Session) -> list[int]:
    interrupted = db.query(Run).filter(Run.status.in_([RunStatus.RUNNING.value, RunStatus.CANCELLING.value])).all()
    for run in interrupted:
        db.query(RunTask).filter(RunTask.run_id == run.id, RunTask.status == TaskStatus.RUNNING.value).update(
            {"status": TaskStatus.PENDING.value}, synchronize_session=False
        )
        run.status = RunStatus.FAILED.value
        run.error = "Interrupted by a server restart; resume it to continue"
        run.finished_at = _now()
    db.commit()
    return [row[0] for row in db.query(Run.id).filter(Run.status == RunStatus.QUEUED.value).order_by(Run.id)]


def start_worker() -> None:
    db = WriteSessionLocal()
    try:
        queued = recover_interrupted_runs(db)
        sources_service.ensure_sources(db)
    finally:
        db.close()

    worker.start(run_in_new_session)
    for run_id in queued:
        worker.enqueue(run_id)
