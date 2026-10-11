import logging
from collections import defaultdict
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.database import WorkerSessionLocal
from app.core.exceptions import NotFoundException
from app.core.scouting.enrichment.website import SiteProbe, WebsiteEnricher
from app.core.scouting.verify import EmailCheck, MailDomainChecker
from app.features.businesses import ingest as businesses_ingest
from app.features.businesses.models import (
    Business,
    BusinessClassification,
    CheckStatus,
    ContactKind,
    ContactPoint,
    SourceRecord,
    WebsiteStatus,
)
from app.features.compliance import service as compliance_service
from app.features.jobs import service as jobs_service
from app.features.jobs.handler import JobHandler
from app.features.jobs.models import JobKind
from app.features.profiles.models import Profile
from app.features.quality import duplicates
from app.features.quality.models import ACTIVE_TASK_STATUSES, QualityTask, QualityTaskKind, QualityTaskStatus
from app.features.quality.schemas import CheckRequest, QualitySettings, QualitySettingsUpdate
from app.features.sheets.models import AppSetting
from app.features.sources import service as sources_service

SETTINGS_KEY = "quality"
FRESH_DAYS = 30
SHARED_PHONE_MIN_BUSINESSES = 3
CHECK_THREADS = 4
PHONE_KINDS = (ContactKind.PHONE.value, ContactKind.WHATSAPP.value)
SHARED_PHONE_NOTE = "This number is listed for {count} businesses, so it may be a switchboard or a directory"
INTERRUPTED_MESSAGE = "Interrupted by a server restart. Start it again to continue."
UNEXPECTED_MESSAGE = "Unexpected error (see the server log)."
NOTHING_FOUND_MESSAGE = "None of those leads were found"
TASK_NOT_FOUND_MESSAGE = "Task not found"
COUNT_FIELDS = (
    "leads", "skipped", "emails_ok", "emails_bad", "emails_unknown", "websites_ok", "websites_dead", "websites_unknown",
    "phones_shared", "rescored",
)


logger = logging.getLogger(__name__)

MailCheckerFactory = Callable[[], MailDomainChecker]
EnricherFactory = Callable[[], WebsiteEnricher]


@dataclass
class LeadFacts:
    business_id: int
    website: str | None
    website_fresh: bool
    emails: list[tuple[int, str, bool]]
    phones: list[tuple[int, str, str | None]]


@dataclass
class LeadResults:
    emails: dict[int, EmailCheck]
    site: SiteProbe | None


def _now() -> datetime:
    return datetime.now(UTC)


def _aware(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    return value if value.tzinfo is not None else value.replace(tzinfo=UTC)


def get_settings(db: Session) -> dict:
    row = db.get(AppSetting, SETTINGS_KEY)
    return QualitySettings(**(row.value if row is not None else {})).model_dump()


def update_settings(db: Session, update_in: QualitySettingsUpdate) -> dict:
    value = QualitySettings(**{**get_settings(db), **update_in.model_dump(exclude_none=True)}).model_dump()
    row = db.get(AppSetting, SETTINGS_KEY)
    if row is None:
        db.add(AppSetting(key=SETTINGS_KEY, value=value))
    else:
        row.value = value
    db.commit()
    return value


def _create_task(
    db: Session, kind: QualityTaskKind, user_id: int | None, business_ids: list[int] | None, refresh: bool = False
) -> QualityTask:
    task = QualityTask(
        kind=kind.value, status=QualityTaskStatus.QUEUED.value, business_ids=business_ids, refresh=refresh,
        total=len(business_ids) if business_ids is not None else 0, counts={}, created_by_id=user_id,
    )
    db.add(task)
    db.flush()
    jobs_service.enqueue(db, JobKind.QUALITY, task.id)
    db.commit()
    db.refresh(task)
    return task


def start_checks(db: Session, check_in: CheckRequest, user_id: int) -> QualityTask:
    visible = [
        row[0]
        for row in db.query(Business.id)
        .filter(Business.id.in_(set(check_in.business_ids)), compliance_service.not_blocked_filter())
        .order_by(Business.id)
    ]
    if not visible:
        raise NotFoundException(NOTHING_FOUND_MESSAGE)
    return _create_task(db, QualityTaskKind.CONTACT_CHECK, user_id, visible, check_in.refresh)


def start_duplicate_scan(db: Session, user_id: int) -> QualityTask:
    return _create_task(db, QualityTaskKind.DUPLICATE_SCAN, user_id, None)


def queue_checks_after_run(db: Session, run_id: int) -> None:
    try:
        config = get_settings(db)
        if not config["check_after_runs"]:
            return
        touched = [
            row[0]
            for row in db.query(SourceRecord.business_id)
            .filter(SourceRecord.run_id == run_id)
            .distinct()
            .order_by(SourceRecord.business_id.desc())
            .limit(config["max_checks_per_run"])
        ]
        if touched:
            _create_task(db, QualityTaskKind.CONTACT_CHECK, None, touched)
    except Exception:
        logger.exception("Could not queue contact checks for run %s", run_id)
        db.rollback()


def get_task(db: Session, task_id: int) -> QualityTask:
    task = db.get(QualityTask, task_id)
    if task is None:
        raise NotFoundException(TASK_NOT_FOUND_MESSAGE)
    return task


def _facts(db: Session, business_ids: list[int], refresh: bool) -> list[LeadFacts]:
    cutoff = _now() - timedelta(days=FRESH_DAYS)
    leads = {
        row.id: row
        for row in db.query(Business.id, Business.website, Business.website_checked_at).filter(Business.id.in_(business_ids))
    }
    emails: dict[int, list[tuple[int, str, bool]]] = defaultdict(list)
    phones: dict[int, list[tuple[int, str, str | None]]] = defaultdict(list)
    rows = db.query(
        ContactPoint.id, ContactPoint.business_id, ContactPoint.kind, ContactPoint.value, ContactPoint.checked_at, ContactPoint.check_status
    ).filter(ContactPoint.business_id.in_(business_ids))
    for contact_id, business_id, kind, value, checked_at, check_status in rows:
        if kind == ContactKind.EMAIL.value:
            fresh = not refresh and checked_at is not None and _aware(checked_at) >= cutoff
            emails[business_id].append((contact_id, value, fresh))
        elif kind in PHONE_KINDS:
            phones[business_id].append((contact_id, value, check_status))
    facts = []
    for business_id in business_ids:
        lead = leads.get(business_id)
        if lead is None:
            continue
        website_fresh = not refresh and lead.website_checked_at is not None and _aware(lead.website_checked_at) >= cutoff
        facts.append(LeadFacts(business_id, lead.website, website_fresh, emails[business_id], phones[business_id]))
    return facts


def _probe(facts: LeadFacts, mail: MailDomainChecker, enricher: WebsiteEnricher) -> LeadResults:
    emails = {contact_id: mail.check(value) for contact_id, value, fresh in facts.emails if not fresh}
    site = None
    if facts.website and not facts.website_fresh:
        try:
            site = enricher.probe(facts.website)
        except Exception:
            logger.exception("Unexpected error checking %s", facts.website)
    return LeadResults(emails, site)


def _shared_phone_counts(db: Session, values: set[str]) -> dict[str, int]:
    if not values:
        return {}
    rows = (
        db.query(ContactPoint.value, func.count(func.distinct(ContactPoint.business_id)))
        .filter(ContactPoint.kind.in_(PHONE_KINDS), ContactPoint.value.in_(values))
        .group_by(ContactPoint.value)
        .all()
    )
    return dict(rows)


def _apply_emails(db: Session, results: LeadResults, counts: dict[str, int], now: datetime) -> bool:
    changed = False
    for contact_id, verdict in results.emails.items():
        contact = db.get(ContactPoint, contact_id)
        if contact is None:
            continue
        if verdict.is_deliverable is None:
            counts["emails_unknown"] += 1
            continue
        status = CheckStatus.OK.value if verdict.is_deliverable else CheckStatus.BAD.value
        changed |= (contact.check_status == CheckStatus.BAD.value) != (status == CheckStatus.BAD.value)
        contact.check_status, contact.check_note, contact.checked_at = status, verdict.note, now
        counts["emails_ok" if verdict.is_deliverable else "emails_bad"] += 1
    return changed


def _apply_site(business: Business, probe: SiteProbe | None, counts: dict[str, int], now: datetime) -> bool:
    if probe is None:
        return False
    if probe.is_alive is None:
        counts["websites_unknown"] += 1
        return False
    status = WebsiteStatus.OK.value if probe.is_alive else WebsiteStatus.DEAD.value
    changed = (business.website_status == WebsiteStatus.DEAD.value) != (status == WebsiteStatus.DEAD.value)
    business.website_status, business.website_check_note, business.website_checked_at = status, probe.note, now
    counts["websites_ok" if probe.is_alive else "websites_dead"] += 1
    return changed


def _apply_phones(db: Session, facts: LeadFacts, shared: dict[str, int], counts: dict[str, int], now: datetime) -> None:
    for contact_id, value, previous in facts.phones:
        number = shared.get(value, 0)
        contact = db.get(ContactPoint, contact_id)
        if contact is None:
            continue
        if number >= SHARED_PHONE_MIN_BUSINESSES:
            contact.check_status = CheckStatus.WARNING.value
            contact.check_note = SHARED_PHONE_NOTE.format(count=number)
            contact.checked_at = now
            counts["phones_shared"] += 1
        elif previous == CheckStatus.WARNING.value:
            contact.check_status, contact.check_note, contact.checked_at = None, None, now


def _rescore(db: Session, business: Business, scorings: dict[int, businesses_ingest.ProfileScoring]) -> None:
    db.flush()
    profile_ids = [row[0] for row in db.query(BusinessClassification.profile_id).filter(BusinessClassification.business_id == business.id)]
    for profile_id in profile_ids:
        if profile_id not in scorings:
            profile = db.get(Profile, profile_id)
            if profile is None:
                continue
            scorings[profile_id] = businesses_ingest.build_profile_scoring(profile)
        businesses_ingest.rescore_business(db, business, scorings[profile_id])


def _default_mail_checker() -> MailDomainChecker:
    return MailDomainChecker()


def _default_enricher() -> WebsiteEnricher:
    return WebsiteEnricher(user_agent=sources_service.user_agent())


def _finish(db: Session, task: QualityTask, status: QualityTaskStatus, error: str | None = None) -> None:
    task.status = status.value
    task.finished_at = _now()
    if error:
        task.error = error
    db.commit()


def run_contact_check(
    db: Session, task: QualityTask, mail_factory: MailCheckerFactory | None, enricher_factory: EnricherFactory | None
) -> None:
    ids = list(task.business_ids or [])[task.done:]
    mail = (mail_factory or _default_mail_checker)()
    enricher = (enricher_factory or _default_enricher)()
    counts = {field: 0 for field in COUNT_FIELDS} | dict(task.counts or {})
    scorings: dict[int, businesses_ingest.ProfileScoring] = {}
    batch_size = CHECK_THREADS * 3

    with ThreadPoolExecutor(max_workers=CHECK_THREADS) as pool:
        for start in range(0, len(ids), batch_size):
            facts = _facts(db, ids[start:start + batch_size], task.refresh)
            db.commit()
            results = list(pool.map(lambda item: _probe(item, mail, enricher), facts))
            shared = _shared_phone_counts(db, {value for item in facts for _, value, _ in item.phones})
            now = _now()
            for item, result in zip(facts, results, strict=True):
                business = db.get(Business, item.business_id)
                if business is None:
                    continue
                counts["leads"] += 1
                if not (item.emails or item.phones or item.website):
                    counts["skipped"] += 1
                changed = _apply_emails(db, result, counts, now)
                changed |= _apply_site(business, result.site, counts, now)
                _apply_phones(db, item, shared, counts, now)
                if changed:
                    _rescore(db, business, scorings)
                    counts["rescored"] += 1
            task.done = min(task.total, task.done + len(ids[start:start + batch_size]))
            task.counts = dict(counts)
            db.commit()
    _finish(db, task, QualityTaskStatus.COMPLETED)


def run_task(
    db: Session, task_id: int, *, mail_factory: MailCheckerFactory | None = None, enricher_factory: EnricherFactory | None = None
) -> QualityTask | None:
    task = db.get(QualityTask, task_id)
    if task is None or task.status != QualityTaskStatus.QUEUED.value:
        return task
    task.status = QualityTaskStatus.RUNNING.value
    task.started_at = _now()
    db.commit()

    if task.kind == QualityTaskKind.DUPLICATE_SCAN.value:
        task.counts = duplicates.scan(db)
        task.done = task.total = task.counts["businesses"]
        _finish(db, task, QualityTaskStatus.COMPLETED)
    else:
        run_contact_check(db, task, mail_factory, enricher_factory)
    return task


def run_task_in_new_session(task_id: int) -> None:
    db = WorkerSessionLocal()
    try:
        run_task(db, task_id)
    except Exception:
        logger.exception("Quality task %s failed", task_id)
        db.rollback()
        task = db.get(QualityTask, task_id)
        if task is not None and task.status in ACTIVE_TASK_STATUSES:
            _finish(db, task, QualityTaskStatus.FAILED, UNEXPECTED_MESSAGE)
    finally:
        db.close()


def recover_task(db: Session, task_id: int, retries_left: bool) -> bool:
    task = db.get(QualityTask, task_id, populate_existing=True)
    if task is None or task.status != QualityTaskStatus.RUNNING.value:
        return False
    if retries_left:
        task.status = QualityTaskStatus.QUEUED.value
        task.error = None
        db.commit()
        return True
    _finish(db, task, QualityTaskStatus.FAILED, INTERRUPTED_MESSAGE)
    return False


def _queued_task_ids(db: Session) -> list[int]:
    query = db.query(QualityTask.id).filter(QualityTask.status == QualityTaskStatus.QUEUED.value).order_by(QualityTask.id)
    return [row[0] for row in query]


def _running_task_ids(db: Session) -> list[int]:
    query = db.query(QualityTask.id).filter(QualityTask.status == QualityTaskStatus.RUNNING.value).order_by(QualityTask.id)
    return [row[0] for row in query]


JOB_HANDLER = JobHandler(
    execute=run_task_in_new_session, recover=recover_task, queued_ids=_queued_task_ids, running_ids=_running_task_ids
)

