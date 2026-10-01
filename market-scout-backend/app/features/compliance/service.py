from collections import defaultdict
from collections.abc import Iterable

from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session

from app.core.exceptions import BadRequestException, NotFoundException
from app.core.scouting.normalize import extract_phones, normalize_email
from app.features.businesses.models import Business, ContactKind, ContactPoint
from app.features.compliance.models import DoNotContact
from app.features.compliance.schemas import DoNotContactCreate

_PHONE_KINDS = (ContactKind.PHONE.value, ContactKind.WHATSAPP.value)


# ---- the blocking rule ----------------------------------------------------------
#
# A business is blocked if (a) it was blocked directly, or (b) any of its phone numbers or
# emails matches a blocked identifier. Everything that shows leads to a person (lists,
# detail, exports, the live sheet) and everything that stores them (ingest) goes through
# these two helpers so the rule lives in one place.

def not_blocked_filter():
    """SQLAlchemy condition that keeps only businesses that may be contacted."""
    # The NULL filter on blocked_directly is load-bearing: standalone phone/email rows have no
    # business_id, and "id NOT IN (..., NULL)" is never true in SQL, which would silently hide
    # every business as soon as one such row exists. (The other two are only defensive.)
    blocked_directly = select(DoNotContact.business_id).where(DoNotContact.business_id.isnot(None))
    blocked_phones = select(DoNotContact.phone).where(DoNotContact.phone.isnot(None))
    blocked_emails = select(DoNotContact.email).where(DoNotContact.email.isnot(None))
    by_phone = select(ContactPoint.business_id).where(
        ContactPoint.kind.in_(_PHONE_KINDS), ContactPoint.value.in_(blocked_phones)
    )
    by_email = select(ContactPoint.business_id).where(
        ContactPoint.kind == ContactKind.EMAIL.value, ContactPoint.value.in_(blocked_emails)
    )
    return ~or_(Business.id.in_(blocked_directly), Business.id.in_(by_phone), Business.id.in_(by_email))


def is_business_blocked(db: Session, business_id: int) -> bool:
    return db.query(Business.id).filter(Business.id == business_id, ~not_blocked_filter()).first() is not None


def identifiers_blocked(db: Session, phones: Iterable[str], emails: Iterable[str]) -> bool:
    """Whether any of these (normalised) phones/emails is on the list, whoever owns it."""
    phones, emails = list(phones), list(emails)
    conditions = []
    if phones:
        conditions.append(DoNotContact.phone.in_(phones))
    if emails:
        conditions.append(DoNotContact.email.in_(emails))
    if not conditions:
        return False
    return db.query(DoNotContact.id).filter(or_(*conditions)).first() is not None


# ---- adding / removing ------------------------------------------------------------

def block_business(db: Session, business_id: int, reason: str | None, added_by_id: int) -> DoNotContact:
    business = db.query(Business).filter(Business.id == business_id).first()
    if business is None:
        raise NotFoundException("Business not found")

    existing = (
        db.query(DoNotContact)
        .filter(DoNotContact.business_id == business.id, DoNotContact.phone.is_(None), DoNotContact.email.is_(None))
        .first()
    )
    if existing:
        return existing  # blocking twice is harmless

    root = DoNotContact(business_id=business.id, reason=reason, added_by_id=added_by_id)
    db.add(root)
    contacts = (
        db.query(ContactPoint.kind, ContactPoint.value)
        .filter(ContactPoint.business_id == business.id, ContactPoint.kind.in_([*_PHONE_KINDS, ContactKind.EMAIL.value]))
        .all()
    )
    for kind, value in dict.fromkeys(contacts):
        is_email = kind == ContactKind.EMAIL.value
        db.add(
            DoNotContact(
                business_id=business.id,
                phone=None if is_email else value,
                email=value if is_email else None,
                reason=reason,
                added_by_id=added_by_id,
            )
        )
    db.commit()
    db.refresh(root)
    return root


def block_identifier(db: Session, data: DoNotContactCreate, added_by_id: int) -> DoNotContact:
    phone = email = None
    if data.phone is not None:
        phones = extract_phones(data.phone)
        if len(phones) != 1:
            raise BadRequestException("Enter one valid phone number")
        phone = phones[0].e164
    else:
        email = normalize_email(str(data.email))
        if email is None:
            raise BadRequestException("Enter a valid email address")

    existing = (
        db.query(DoNotContact)
        .filter(DoNotContact.business_id.is_(None), DoNotContact.phone == phone, DoNotContact.email == email)
        .first()
    )
    if existing:
        return existing

    entry = DoNotContact(phone=phone, email=email, reason=data.reason, added_by_id=added_by_id)
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry


def remove_entry(db: Session, entry_id: int) -> None:
    entry = db.query(DoNotContact).filter(DoNotContact.id == entry_id).first()
    if entry is None:
        raise NotFoundException("Entry not found")

    # Un-blocking a business lifts the whole block: the business row and its identifiers.
    if entry.business_id is not None:
        db.query(DoNotContact).filter(DoNotContact.business_id == entry.business_id).delete(synchronize_session=False)
    else:
        db.delete(entry)
    db.commit()


# ---- reading -------------------------------------------------------------------------

def get_entries(db: Session, page: int = 1, limit: int = 20, search: str | None = None) -> dict:
    """The list people manage: one line per blocked business, plus standalone phones/emails.
    (The per-identifier rows that back a blocked business stay out of sight.)"""
    query = db.query(DoNotContact).outerjoin(Business, Business.id == DoNotContact.business_id).filter(
        or_(
            and_(DoNotContact.business_id.isnot(None), DoNotContact.phone.is_(None), DoNotContact.email.is_(None)),
            and_(DoNotContact.business_id.is_(None), or_(DoNotContact.phone.isnot(None), DoNotContact.email.isnot(None))),
        )
    )
    if search:
        term = f"%{search.strip()}%"
        query = query.filter(
            or_(Business.name.ilike(term), DoNotContact.phone.ilike(term), DoNotContact.email.ilike(term))
        )

    total_count = query.count()
    entries = query.order_by(DoNotContact.id.desc()).offset((page - 1) * limit).limit(limit).all()

    names, identifiers = _lookup(db, entries)
    return {
        "data": [_to_response(entry, names, identifiers) for entry in entries],
        "count": total_count,
    }


def to_response(db: Session, entry: DoNotContact) -> dict:
    names, identifiers = _lookup(db, [entry])
    return _to_response(entry, names, identifiers)


def _lookup(db: Session, entries: list[DoNotContact]) -> tuple[dict[int, str], dict[int, list[str]]]:
    """Business names and blocked identifiers for the entries' businesses, in two queries."""
    business_ids = [entry.business_id for entry in entries if entry.business_id is not None]
    if not business_ids:
        return {}, {}

    names = dict(db.query(Business.id, Business.name).filter(Business.id.in_(business_ids)).all())
    identifiers: dict[int, list[str]] = defaultdict(list)
    rows = db.query(DoNotContact.business_id, DoNotContact.phone, DoNotContact.email).filter(
        DoNotContact.business_id.in_(business_ids), or_(DoNotContact.phone.isnot(None), DoNotContact.email.isnot(None))
    )
    for business_id, phone, email in rows:
        identifiers[business_id].append(phone or email)
    return names, identifiers


def _to_response(entry: DoNotContact, names: dict[int, str], identifiers: dict[int, list[str]]) -> dict:
    if entry.phone is None and entry.email is None:
        kind, value = "business", names.get(entry.business_id, f"Business #{entry.business_id}")
    elif entry.phone is not None:
        kind, value = "phone", entry.phone
    else:
        kind, value = "email", entry.email
    return {
        "id": entry.id,
        "kind": kind,
        "value": value,
        "business_id": entry.business_id,
        "identifiers": sorted(identifiers.get(entry.business_id, [])) if kind == "business" else [],
        "reason": entry.reason,
        "added_by_id": entry.added_by_id,
        "created_at": entry.created_at,
    }
