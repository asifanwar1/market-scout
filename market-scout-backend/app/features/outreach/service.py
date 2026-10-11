import re
from datetime import UTC, datetime, timedelta
from urllib.parse import quote

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.constants import FIRST_PAGE, NAME_MIN_LENGTH
from app.core.exceptions import BadRequestException, ConflictException, ForbiddenException, NotFoundException
from app.features.businesses.models import Business, CheckStatus, ContactKind, ContactPoint, LeadStatus
from app.features.compliance import service as compliance_service
from app.features.outreach.models import (
    MessageChannel,
    MessageStatus,
    MessageTemplate,
    OutreachMessage,
    TemplateChannel,
)
from app.features.outreach.schemas import (
    BODY_MAX_LENGTH,
    SUBJECT_MAX_LENGTH,
    DecisionRequest,
    PrepareRequest,
    PreviewRequest,
    TemplateCreate,
    TemplateUpdate,
)
from app.features.pipeline import service as pipeline_service
from app.features.pipeline.models import ActivityKind
from app.features.pipeline.schemas import SUMMARY_MAX_LENGTH
from app.features.users.models import User
from app.features.webhooks import events as webhook_events
from app.features.webhooks import service as webhooks_service
from app.features.webhooks.models import WebhookEvent

DEFAULT_LIMIT = 20
RECENT_DAYS = 14
PLACEHOLDER_PATTERN = re.compile(r"\{(\w+)\}")
NON_DIGITS_PATTERN = re.compile(r"\D")
WHATSAPP_LINK = "https://wa.me/{number}?text={text}"
MAIL_LINK = "mailto:{address}?subject={subject}&body={body}"
MAIL_ADDRESS_SAFE = "@"

PLACEHOLDERS = {
    "business_name": ("Business name", None),
    "city": ("City", "your city"),
    "contact_name": ("Contact person", "there"),
}

TEMPLATE_NOT_FOUND_MESSAGE = "Template not found"
MESSAGE_NOT_FOUND_MESSAGE = "Message not found"
CONTACT_NOT_FOUND_MESSAGE = "That contact doesn't belong to this lead"
UNKNOWN_PLACEHOLDER_MESSAGE = "Unknown placeholder {{{key}}}. Use only: {allowed}"
NAME_TAKEN_MESSAGE = "A template with that name already exists"
NAME_TOO_SHORT_MESSAGE = "Give the template a name"
NOTHING_TO_UPDATE_MESSAGE = "Send at least one thing to change"
NEEDS_BODY_MESSAGE = "Choose a template or write the message text"
WRONG_CONTACT_WHATSAPP_MESSAGE = "WhatsApp needs a phone or WhatsApp number"
WRONG_CONTACT_EMAIL_MESSAGE = "Email needs an email address"
BAD_EMAIL_MESSAGE = "That email address was checked and its domain can't receive mail"
NO_DIGITS_MESSAGE = "That number has no digits to dial"
TEMPLATE_CHANNEL_MESSAGE = "That template is for {channel}"
ALREADY_DECIDED_MESSAGE = "This message was already marked"
NOT_YOURS_MESSAGE = "Only the person who wrote this message or an admin can mark it"
SUBJECT_PREFIX = "Subject: {subject}\n"
TEMPLATE_PREFIX = "Template \"{name}\"\n"

ACTIVITY_KIND_BY_CHANNEL = {
    MessageChannel.WHATSAPP.value: ActivityKind.WHATSAPP,
    MessageChannel.EMAIL.value: ActivityKind.EMAIL,
}
CONTACT_KINDS_BY_CHANNEL = {
    MessageChannel.WHATSAPP.value: {ContactKind.PHONE.value, ContactKind.WHATSAPP.value},
    MessageChannel.EMAIL.value: {ContactKind.EMAIL.value},
}
WRONG_CONTACT_BY_CHANNEL = {
    MessageChannel.WHATSAPP.value: WRONG_CONTACT_WHATSAPP_MESSAGE,
    MessageChannel.EMAIL.value: WRONG_CONTACT_EMAIL_MESSAGE,
}


def _now() -> datetime:
    return datetime.now(UTC)


def get_config() -> dict:
    return {
        "placeholders": [
            {"key": key, "label": label, "fallback": fallback} for key, (label, fallback) in PLACEHOLDERS.items()
        ],
        "template_channels": [channel.value for channel in TemplateChannel],
        "subject_max_length": SUBJECT_MAX_LENGTH,
        "body_max_length": BODY_MAX_LENGTH,
        "recent_days": RECENT_DAYS,
    }


def check_placeholders(*texts: str | None) -> None:
    for text in texts:
        for key in PLACEHOLDER_PATTERN.findall(text or ""):
            if key not in PLACEHOLDERS:
                raise BadRequestException(UNKNOWN_PLACEHOLDER_MESSAGE.format(key=key, allowed=", ".join(PLACEHOLDERS)))


def render(text: str | None, values: dict[str, str]) -> str | None:
    if text is None:
        return None
    check_placeholders(text)
    return PLACEHOLDER_PATTERN.sub(lambda match: values[match.group(1)], text)


def placeholder_values(business: Business) -> dict[str, str]:
    city = business.geography.name if business.geography is not None else None
    return {
        "business_name": business.name,
        "city": city or PLACEHOLDERS["city"][1],
        "contact_name": (business.contact_name or "").strip() or PLACEHOLDERS["contact_name"][1],
    }


def _template_view(template: MessageTemplate) -> dict:
    return {
        "id": template.id, "name": template.name, "channel": template.channel, "subject": template.subject,
        "body": template.body, "created_at": template.created_at, "updated_at": template.updated_at,
    }


def _get_template(db: Session, template_id: int) -> MessageTemplate:
    template = db.query(MessageTemplate).filter(MessageTemplate.id == template_id).first()
    if template is None:
        raise NotFoundException(TEMPLATE_NOT_FOUND_MESSAGE)
    return template


def _name_taken(db: Session, name: str, except_id: int | None = None) -> bool:
    query = db.query(MessageTemplate.id).filter(func.lower(MessageTemplate.name) == name.lower())
    if except_id is not None:
        query = query.filter(MessageTemplate.id != except_id)
    return query.first() is not None


def _subject_for(channel: str, subject: str | None) -> str | None:
    return None if channel == TemplateChannel.WHATSAPP.value else subject


def list_templates(db: Session, channel: TemplateChannel | None = None) -> dict:
    query = db.query(MessageTemplate)
    if channel is not None and channel != TemplateChannel.ANY:
        query = query.filter(MessageTemplate.channel.in_([channel.value, TemplateChannel.ANY.value]))
    rows = query.order_by(func.lower(MessageTemplate.name)).all()
    return {"data": [_template_view(row) for row in rows], "count": len(rows)}


def create_template(db: Session, template_in: TemplateCreate, actor_id: int) -> dict:
    check_placeholders(template_in.subject, template_in.body)
    if _name_taken(db, template_in.name):
        raise ConflictException(NAME_TAKEN_MESSAGE)
    template = MessageTemplate(
        name=template_in.name, channel=template_in.channel.value, body=template_in.body, created_by_id=actor_id,
        subject=_subject_for(template_in.channel.value, template_in.subject),
    )
    db.add(template)
    db.commit()
    db.refresh(template)
    return _template_view(template)


def update_template(db: Session, template_id: int, update_in: TemplateUpdate) -> dict:
    template = _get_template(db, template_id)
    data = update_in.model_dump(exclude_unset=True)
    if not data:
        raise BadRequestException(NOTHING_TO_UPDATE_MESSAGE)
    if "name" in data:
        name = (data["name"] or "").strip()
        if len(name) < NAME_MIN_LENGTH:
            raise BadRequestException(NAME_TOO_SHORT_MESSAGE)
        if _name_taken(db, name, except_id=template.id):
            raise ConflictException(NAME_TAKEN_MESSAGE)
        template.name = name
    if data.get("channel") is not None:
        template.channel = data["channel"].value
    if "body" in data:
        body = (data["body"] or "").strip()
        if not body:
            raise BadRequestException(NEEDS_BODY_MESSAGE)
        template.body = body
    if "subject" in data:
        template.subject = (data["subject"] or "").strip() or None
    template.subject = _subject_for(template.channel, template.subject)
    check_placeholders(template.subject, template.body)
    db.commit()
    db.refresh(template)
    return _template_view(template)


def delete_template(db: Session, template_id: int) -> None:
    template = _get_template(db, template_id)
    db.delete(template)
    db.commit()


def _require_business(db: Session, business_id: int) -> Business:
    business = db.query(Business).filter(Business.id == business_id, compliance_service.not_blocked_filter()).first()
    if business is None:
        raise NotFoundException("Business not found")
    return business


def _resolve_text(db: Session, template_id: int | None, subject: str | None, body: str | None) -> tuple[str | None, str]:
    if template_id is not None:
        template = _get_template(db, template_id)
        return (subject if subject is not None else template.subject), (body if body is not None else template.body)
    if body is None or not body.strip():
        raise BadRequestException(NEEDS_BODY_MESSAGE)
    return subject, body


def preview(db: Session, preview_in: PreviewRequest) -> dict:
    business = _require_business(db, preview_in.business_id)
    subject, body = _resolve_text(db, preview_in.template_id, preview_in.subject, preview_in.body)
    values = placeholder_values(business)
    return {"subject": render((subject or "").strip() or None, values), "body": render(body.strip(), values)}


def _require_contact(db: Session, business_id: int, contact_id: int, channel: str) -> ContactPoint:
    contact = db.query(ContactPoint).filter(ContactPoint.id == contact_id, ContactPoint.business_id == business_id).first()
    if contact is None:
        raise BadRequestException(CONTACT_NOT_FOUND_MESSAGE)
    if contact.kind not in CONTACT_KINDS_BY_CHANNEL[channel]:
        raise BadRequestException(WRONG_CONTACT_BY_CHANNEL[channel])
    if channel == MessageChannel.EMAIL.value and contact.check_status == CheckStatus.BAD.value:
        raise BadRequestException(BAD_EMAIL_MESSAGE)
    return contact


def build_link(channel: str, to_value: str, subject: str | None, body: str) -> str:
    if channel == MessageChannel.WHATSAPP.value:
        number = NON_DIGITS_PATTERN.sub("", to_value)
        if not number:
            raise BadRequestException(NO_DIGITS_MESSAGE)
        return WHATSAPP_LINK.format(number=number, text=quote(body, safe=""))
    return MAIL_LINK.format(
        address=quote(to_value, safe=MAIL_ADDRESS_SAFE), subject=quote(subject or "", safe=""), body=quote(body, safe="")
    )


def _people(db: Session, user_ids: set[int | None]) -> dict[int, dict]:
    ids = {user_id for user_id in user_ids if user_id is not None}
    if not ids:
        return {}
    rows = db.query(User.id, User.full_name).filter(User.id.in_(ids)).all()
    return {user_id: {"id": user_id, "full_name": full_name} for user_id, full_name in rows}


def _recent_send(db: Session, business_id: int) -> OutreachMessage | None:
    since = _now() - timedelta(days=RECENT_DAYS)
    return (
        db.query(OutreachMessage)
        .filter(
            OutreachMessage.business_id == business_id,
            OutreachMessage.status == MessageStatus.SENT.value,
            OutreachMessage.decided_at >= since,
        )
        .order_by(OutreachMessage.decided_at.desc())
        .first()
    )


def prepare(db: Session, prepare_in: PrepareRequest, actor_id: int) -> dict:
    business = _require_business(db, prepare_in.business_id)
    channel = prepare_in.channel.value
    contact = _require_contact(db, business.id, prepare_in.contact_id, channel)

    template_name = None
    if prepare_in.template_id is not None:
        template = _get_template(db, prepare_in.template_id)
        if template.channel not in (channel, TemplateChannel.ANY.value):
            raise BadRequestException(TEMPLATE_CHANNEL_MESSAGE.format(channel=template.channel))
        template_name = template.name

    values = placeholder_values(business)
    subject = render((prepare_in.subject or "").strip() or None, values) if channel == MessageChannel.EMAIL.value else None
    body = render(prepare_in.body, values)
    link = build_link(channel, contact.value, subject, body)

    recent = _recent_send(db, business.id)
    message = OutreachMessage(
        business_id=business.id, template_id=prepare_in.template_id, template_name=template_name, channel=channel,
        to_value=contact.value, subject=subject, body=body, status=MessageStatus.OPENED.value, created_by_id=actor_id,
    )
    db.add(message)
    db.commit()
    db.refresh(message)

    people = _people(db, {recent.created_by_id}) if recent is not None else {}
    return {
        "id": message.id, "channel": channel, "to_value": message.to_value, "subject": subject, "body": body, "link": link,
        "last_sent_at": recent.decided_at if recent is not None else None,
        "last_sent_by": people.get(recent.created_by_id) if recent is not None else None,
    }


def _summary(message: OutreachMessage) -> str:
    prefix = TEMPLATE_PREFIX.format(name=message.template_name) if message.template_name else ""
    subject = SUBJECT_PREFIX.format(subject=message.subject) if message.subject else ""
    return f"{prefix}{subject}{message.body}"[:SUMMARY_MAX_LENGTH]


def decide(db: Session, message_id: int, decision_in: DecisionRequest, actor: User) -> dict:
    message = db.query(OutreachMessage).filter(OutreachMessage.id == message_id).first()
    if message is None:
        raise NotFoundException(MESSAGE_NOT_FOUND_MESSAGE)
    if message.created_by_id != actor.id and not actor.is_admin:
        raise ForbiddenException(NOT_YOURS_MESSAGE)
    if message.status != MessageStatus.OPENED.value:
        raise ConflictException(ALREADY_DECIDED_MESSAGE)

    business = _require_business(db, message.business_id)
    message.status = MessageStatus.SENT.value if decision_in.sent else MessageStatus.NOT_SENT.value
    message.decided_at = _now()
    if decision_in.sent:
        pipeline_service.add_system_activity(
            db, business.id, ACTIVITY_KIND_BY_CHANNEL[message.channel], actor.id, summary=_summary(message)
        )
        if business.lead_status == LeadStatus.NEW.value:
            pipeline_service.apply_status_change(db, business, LeadStatus.CONTACTED.value, actor.id)
        webhooks_service.emit(
            db,
            WebhookEvent.MESSAGE_SENT,
            lambda: {
                "message": {
                    "id": message.id, "channel": message.channel, "to": message.to_value, "subject": message.subject,
                    "body": message.body, "template": message.template_name,
                },
                "lead": webhook_events.lead_snapshot(db, business),
                "sent_by": actor.full_name,
            },
        )
    db.commit()
    return get_message_view(db, message.id)


def _message_rows(db: Session):
    return db.query(OutreachMessage, Business.name).join(Business, Business.id == OutreachMessage.business_id)


def _message_view(message: OutreachMessage, business_name: str, people: dict[int, dict]) -> dict:
    return {
        "id": message.id, "business_id": message.business_id, "business_name": business_name,
        "template_name": message.template_name, "channel": message.channel, "to_value": message.to_value,
        "subject": message.subject, "body": message.body, "status": message.status,
        "created_by": people.get(message.created_by_id), "created_at": message.created_at, "decided_at": message.decided_at,
    }


def get_message_view(db: Session, message_id: int) -> dict:
    message, business_name = _message_rows(db).filter(OutreachMessage.id == message_id).one()
    return _message_view(message, business_name, _people(db, {message.created_by_id}))


def list_messages(
    db: Session, *, business_id: int | None = None, mine_id: int | None = None, status: MessageStatus | None = None,
    page: int = FIRST_PAGE, limit: int = DEFAULT_LIMIT,
) -> dict:
    query = _message_rows(db).filter(compliance_service.not_blocked_filter())
    if business_id is not None:
        query = query.filter(OutreachMessage.business_id == business_id)
    if mine_id is not None:
        query = query.filter(OutreachMessage.created_by_id == mine_id)
    if status is not None:
        query = query.filter(OutreachMessage.status == status.value)
    total = query.count()
    rows = (
        query.order_by(OutreachMessage.created_at.desc(), OutreachMessage.id.desc())
        .offset((page - 1) * limit).limit(limit).all()
    )
    people = _people(db, {message.created_by_id for message, _ in rows})
    return {"data": [_message_view(message, name, people) for message, name in rows], "count": total}
