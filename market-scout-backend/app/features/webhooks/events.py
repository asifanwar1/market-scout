from sqlalchemy import func
from sqlalchemy.orm import Session

from app.features.businesses.models import Business, BusinessClassification, ContactKind, ContactPoint
from app.features.pipeline.models import LeadOutcome

PHONE_KINDS = (ContactKind.PHONE.value, ContactKind.WHATSAPP.value)


def lead_snapshot(db: Session, business: Business) -> dict:
    contacts = (
        db.query(ContactPoint.kind, ContactPoint.value)
        .filter(ContactPoint.business_id == business.id)
        .order_by(ContactPoint.id)
        .all()
    )
    score = db.query(func.max(BusinessClassification.score)).filter(BusinessClassification.business_id == business.id).scalar()
    city = business.geography.name if business.geography is not None else None
    return {
        "id": business.id,
        "name": business.name,
        "city": city,
        "status": business.lead_status,
        "score": score,
        "website": business.website,
        "phones": list(dict.fromkeys(value for kind, value in contacts if kind in PHONE_KINDS)),
        "emails": list(dict.fromkeys(value for kind, value in contacts if kind == ContactKind.EMAIL.value)),
    }


def outcome_snapshot(db: Session, business_id: int) -> dict | None:
    outcome = db.query(LeadOutcome).filter(LeadOutcome.business_id == business_id).first()
    if outcome is None:
        return None
    return {"kind": outcome.kind, "value": outcome.value, "product": outcome.product, "loss_reason": outcome.loss_reason}
