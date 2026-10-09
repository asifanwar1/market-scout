import json
import logging
import time
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.constants import BYTES_PER_MEGABYTE, FIRST_PAGE
from app.core.database import WorkerSessionLocal, WriteSessionLocal
from app.core.exceptions import BadRequestException, NotFoundException
from app.core.importing.cities import CityMatcher
from app.core.importing.files import ImportFileError, Table, read_table
from app.core.importing.lookup import OvertureLookup, fill_from
from app.core.importing.mapping import (
    SKIP_NO_CONTACT,
    SKIP_NO_NAME,
    Mapping,
    parse_row,
    suggest_mapping,
)
from app.core.scouting import place_store
from app.core.scouting.normalize import normalize_name
from app.core.scouting.types import RawBusiness, SearchArea
from app.features.businesses import ingest as businesses_ingest
from app.features.businesses.ingest import STAT_FIELDS, IngestContext
from app.features.geographies.models import Geography, GeographyLevel
from app.features.imports.models import Import, ImportStatus
from app.features.imports.schemas import ImportOptions
from app.features.imports.worker import import_worker
from app.features.profiles.models import Profile
from app.features.sheets import service as sheets_service

FILENAME_MAX_LENGTH = 200


DEFAULT_LIMIT = 10


logger = logging.getLogger(__name__)

BATCH_SIZE = 100
SAMPLE_ROWS = 8


def _now() -> datetime:
    return datetime.now(UTC)


def _rows_file(import_id: int) -> Path:
    return Path(settings.IMPORTS_DIR) / f"{import_id}.jsonl"


def read_upload(filename: str, content: bytes) -> Table:
    limit = settings.IMPORT_MAX_MB * BYTES_PER_MEGABYTE
    if len(content) > limit:
        raise BadRequestException(f"That file is larger than {settings.IMPORT_MAX_MB} MB. Split it into smaller files.")
    if not content:
        raise BadRequestException("The file is empty.")
    try:
        return read_table(filename, content, settings.IMPORT_MAX_ROWS)
    except ImportFileError as exc:
        raise BadRequestException(str(exc)) from exc


def preview(filename: str, content: bytes) -> dict:
    table = read_upload(filename, content)
    return {
        "filename": filename,
        "columns": table.headers,
        "row_count": len(table.rows),
        "sample": [dict(zip(table.headers, row, strict=True)) for row in table.rows[:SAMPLE_ROWS]],
        "suggested_mapping": suggest_mapping(table.headers),
    }


def _validate(db: Session, table: Table, options: ImportOptions) -> tuple[Profile, Geography | None]:
    mapping = Mapping(**options.mapping.model_dump())
    headers = set(table.headers)
    unknown = sorted({h for h in mapping.referenced_headers() if h not in headers})
    if unknown:
        raise BadRequestException(f"These columns aren't in the file: {', '.join(unknown)}")
    if bool(mapping.latitude) != bool(mapping.longitude):
        raise BadRequestException("Map both latitude and longitude, or neither.")
    if not (mapping.phones or mapping.emails or mapping.website) and options.require_contact and not options.lookup_contacts:
        raise BadRequestException(
            "Map at least one phone, email or website column, or turn off \"skip rows with no contact details\", "
            "or let the app look up the phones in Overture Maps."
        )

    profile = db.get(Profile, options.profile_id)
    if profile is None:
        raise BadRequestException("That profile doesn't exist")
    if options.segment_slug and options.segment_slug not in {s.slug for s in profile.segments}:
        raise BadRequestException("That business type isn't part of the chosen profile")

    geography = None
    if options.default_geography_id is not None:
        geography = db.get(Geography, options.default_geography_id)
        if geography is None or geography.level != GeographyLevel.CITY.value:
            raise BadRequestException("The default city must be one of the cities")
    return profile, geography


def create_import(db: Session, filename: str, content: bytes, options: ImportOptions, created_by_id: int) -> Import:
    table = read_upload(filename, content)
    profile, default_city = _validate(db, table, options)

    mapping = Mapping(**options.mapping.model_dump())
    source_key = f"import:{options.label}"
    matcher = CityMatcher(
        {name: city_id for city_id, name in db.query(Geography.id, Geography.name).filter(Geography.level == GeographyLevel.CITY.value)}
    )

    skipped: dict[str, int] = {}
    parsed_rows = []
    for number, row in enumerate(table.rows, start=2):
        parsed = parse_row(
            number, dict(zip(table.headers, row, strict=True)), mapping, source_key,
            options.require_contact and not options.lookup_contacts,
        )
        if parsed.skipped or parsed.raw is None:
            reason = parsed.skipped or SKIP_NO_NAME
            skipped[reason] = skipped.get(reason, 0) + 1
            continue
        parsed_rows.append((number, parsed))

    city_by_row = {
        number: (
            matcher.from_city_text(parsed.city_text)
            or matcher.from_address(parsed.raw.address)
            or (default_city.id if default_city else None)
        )
        for number, parsed in parsed_rows
    }
    found_places: dict[int, RawBusiness] = {}
    if options.lookup_contacts:
        found_places = _look_up_contacts(db, parsed_rows, city_by_row)
        if options.require_contact:
            kept = []
            for number, parsed in parsed_rows:
                if parsed.raw.phones or parsed.raw.emails or parsed.raw.website:
                    kept.append((number, parsed))
                else:
                    skipped[SKIP_NO_CONTACT] = skipped.get(SKIP_NO_CONTACT, 0) + 1
            parsed_rows = kept

    shared_phones = _shared_phones([parsed.raw for _, parsed in parsed_rows])
    no_city = 0
    lines: list[str] = []
    for number, parsed in parsed_rows:
        parsed.raw.unreliable_phones = [phone for phone in parsed.raw.phones if phone in shared_phones]
        city_id = city_by_row[number]
        no_city += city_id is None
        entry = {"row": number, "geography_id": city_id, "raw": asdict(parsed.raw)}
        place = found_places.get(number)
        if place is not None:
            place.unreliable_phones = [phone for phone in place.phones if phone in shared_phones]
            entry["place"] = asdict(place)
        lines.append(json.dumps(entry, ensure_ascii=False))

    if not lines:
        raise BadRequestException(_nothing_to_import(len(table.rows), skipped))

    record = Import(
        label=options.label,
        filename=filename[:FILENAME_MAX_LENGTH],
        profile_id=profile.id,
        profile_name=profile.name,
        segment_slug=options.segment_slug,
        default_geography_id=default_city.id if default_city else None,
        default_geography_name=default_city.name if default_city else None,
        require_contact=options.require_contact,
        lookup_contacts=options.lookup_contacts,
        mapping=options.mapping.model_dump(),
        created_by_id=created_by_id,
        status=ImportStatus.QUEUED.value,
        rows_total=len(table.rows),
        rows_to_import=len(lines),
        skipped=skipped,
        stats={**dict.fromkeys(STAT_FIELDS, 0), "no_city": no_city, "shared_phones": len(shared_phones), "looked_up": len(found_places)},
    )
    db.add(record)
    db.commit()

    path = _rows_file(record.id)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    import_worker.enqueue(record.id)
    db.refresh(record)
    return record


def _look_up_contacts(db: Session, parsed_rows: list, city_by_row: dict[int, int | None]) -> dict[int, RawBusiness]:
    try:
        lookup = OvertureLookup(settings.OVERTURE_DB_PATH, settings.OVERTURE_MIN_CONFIDENCE)
    except place_store.StoreError as exc:
        raise BadRequestException(f"Overture Maps can't be used to look up contacts: {exc}") from exc

    areas = {
        city.id: SearchArea(city.latitude, city.longitude, city.radius_km, city.name, tuple(city.bbox) if city.bbox else None).rectangle
        for city in db.query(Geography).filter(Geography.level == GeographyLevel.CITY.value)
    }
    found: dict[int, RawBusiness] = {}
    with lookup:
        for number, parsed in parsed_rows:
            if parsed.raw.phones:
                continue
            city_id = city_by_row[number]
            place = lookup.find(parsed.raw.name, areas.get(city_id) if city_id is not None else None)
            if place is None:
                continue
            parsed.raw = fill_from(parsed.raw, place)
            found[number] = place
    return found


SHARED_PHONE_MIN_COMPANIES = 3


def _shared_phones(rows: list[RawBusiness]) -> set[str]:
    companies_by_phone: dict[str, set[str]] = {}
    for raw in rows:
        name = normalize_name(raw.name)
        for phone in raw.phones:
            companies_by_phone.setdefault(phone, set()).add(name)
    return {phone for phone, names in companies_by_phone.items() if len(names) >= SHARED_PHONE_MIN_COMPANIES}


def _nothing_to_import(total: int, skipped: dict[str, int]) -> str:
    reasons = []
    if skipped.get(SKIP_NO_NAME):
        reasons.append(f"{skipped[SKIP_NO_NAME]} had no name")
    if skipped.get(SKIP_NO_CONTACT):
        reasons.append(f"{skipped[SKIP_NO_CONTACT]} had no phone, email or website")
    return f"None of the {total} rows can be imported ({'; '.join(reasons)}). Check which columns are mapped."


def get_imports(db: Session, page: int = FIRST_PAGE, limit: int = DEFAULT_LIMIT) -> dict:
    query = db.query(Import)
    total = query.count()
    rows = query.order_by(Import.id.desc()).offset((page - 1) * limit).limit(limit).all()
    return {"data": rows, "count": total}


def get_import_by_id(db: Session, import_id: int) -> Import:
    record = db.get(Import, import_id)
    if record is None:
        raise NotFoundException("Import not found")
    return record


def cancel_import(db: Session, import_id: int) -> Import:
    record = get_import_by_id(db, import_id)
    if record.status == ImportStatus.QUEUED.value:
        record.status = ImportStatus.CANCELLED.value
        record.finished_at = _now()
        _rows_file(record.id).unlink(missing_ok=True)
    elif record.status == ImportStatus.RUNNING.value:
        record.status = ImportStatus.CANCELLING.value
    else:
        raise BadRequestException("This import has already finished")
    db.commit()
    db.refresh(record)
    return record


def execute_import(db: Session, import_id: int) -> Import | None:
    record = db.get(Import, import_id)
    if record is None or record.status != ImportStatus.QUEUED.value:
        return record

    record.status = ImportStatus.RUNNING.value
    record.started_at = _now()
    db.commit()

    profile = db.get(Profile, record.profile_id) if record.profile_id else None
    if profile is None:
        return _finish(db, record, ImportStatus.FAILED, "The profile for this import no longer exists")
    path = _rows_file(record.id)
    if not path.exists():
        return _finish(db, record, ImportStatus.FAILED, "The uploaded rows are no longer there. Upload the file again.")

    scoring = businesses_ingest.build_profile_scoring(profile)
    totals = dict(record.stats)
    cancelled = False
    with path.open(encoding="utf-8") as handle:
        batch: list[dict] = []
        for line in handle:
            batch.append(json.loads(line))
            if len(batch) >= BATCH_SIZE:
                _store_batch(db, record, batch, scoring, totals)
                batch = []
                time.sleep(settings.IMPORT_BATCH_PAUSE_SECONDS)
                db.refresh(record, ["status"])
                if record.status == ImportStatus.CANCELLING.value:
                    cancelled = True
                    break
        if batch and not cancelled:
            _store_batch(db, record, batch, scoring, totals)

    return _finish(db, record, ImportStatus.CANCELLED if cancelled else ImportStatus.COMPLETED)


def _store_batch(db: Session, record: Import, batch: list[dict], scoring, totals: dict[str, int]) -> None:
    now = _now()

    def context(entry: dict) -> IngestContext:
        return IngestContext(
            run_id=None, geography_id=entry["geography_id"], hint_segment_slug=record.segment_slug, now=now, profile=scoring
        )

    for entry in batch:
        if entry.get("place"):
            created = businesses_ingest.ingest_records(db, [(RawBusiness(**entry["place"]), context(entry))])["new"]
            counts = businesses_ingest.ingest_records(db, [(RawBusiness(**entry["raw"]), context(entry))])
            if created and counts["merged"]:
                counts["new"], counts["merged"] = counts["new"] + 1, counts["merged"] - 1
        else:
            counts = businesses_ingest.ingest_records(db, [(RawBusiness(**entry["raw"]), context(entry))])
        for key, value in counts.items():
            totals[key] = totals.get(key, 0) + value
    record.stats = dict(totals)
    record.rows_done += len(batch)
    db.commit()


def _finish(db: Session, record: Import, status: ImportStatus, error: str | None = None) -> Import:
    record.status = status.value
    record.finished_at = _now()
    if error:
        record.error = error
    _rows_file(record.id).unlink(missing_ok=True)
    db.commit()
    db.refresh(record)
    return record


def run_import_in_new_session(import_id: int) -> None:
    db = WorkerSessionLocal()
    try:
        execute_import(db, import_id)
    except Exception:
        logger.exception("Import %s failed", import_id)
        db.rollback()
        record = db.get(Import, import_id)
        if record is not None and record.is_active:
            _finish(db, record, ImportStatus.FAILED, "Unexpected error (see the server log)")
    finally:
        db.close()
        sheets_service.notify_changed()


def recover_interrupted_imports(db: Session) -> list[int]:
    stuck = db.query(Import).filter(Import.status.in_([ImportStatus.RUNNING.value, ImportStatus.CANCELLING.value])).all()
    for record in stuck:
        record.status = ImportStatus.FAILED.value
        record.error = "Interrupted by a server restart. Import the file again: rows already stored are recognised, not duplicated."
        record.finished_at = _now()
        _rows_file(record.id).unlink(missing_ok=True)
    db.commit()
    return [row[0] for row in db.query(Import.id).filter(Import.status == ImportStatus.QUEUED.value).order_by(Import.id)]


def start_worker() -> None:
    db = WriteSessionLocal()
    try:
        queued = recover_interrupted_imports(db)
    finally:
        db.close()
    import_worker.start(run_import_in_new_session)
    for import_id in queued:
        import_worker.enqueue(import_id)
