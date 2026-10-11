from datetime import UTC, date, datetime
from enum import Enum

from sqlalchemy import case, func
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.constants import FIRST_PAGE
from app.core.exceptions import BadRequestException, NotFoundException
from app.features.businesses.models import Business, LeadStatus
from app.features.compliance import service as compliance_service
from app.features.pipeline.models import (
    ActivityKind,
    LeadActivity,
    LeadOutcome,
    LeadTask,
    OutcomeKind,
)
from app.features.pipeline.schemas import ActivityCreate, OutcomeInput, TaskCreate, TaskUpdate
from app.features.users.models import User
from app.features.webhooks import events as webhook_events
from app.features.webhooks import service as webhooks_service
from app.features.webhooks.models import WebhookEvent

DEFAULT_ACTIVITY_LIMIT = 50
DEFAULT_TASK_LIMIT = 50
UNASSIGNED_LABEL = "Unassigned"

CLOSING_STATUSES = {
    LeadStatus.CUSTOMER.value: OutcomeKind.WON,
    LeadStatus.NOT_INTERESTED.value: OutcomeKind.LOST,
}
WON_REJECTS_REASON_MESSAGE = "A reason for losing doesn't apply to a lead that became a customer"
LOST_REJECTS_DEAL_MESSAGE = "A deal value and product don't apply to a lead that is not interested"
NOT_CLOSED_MESSAGE = "An outcome can only be recorded for a customer or a lead that is not interested"
ASSIGNEE_MESSAGE = "That user doesn't exist or is inactive"
NOTHING_TO_UPDATE_MESSAGE = "Send at least one thing to change"


class TaskScope(str, Enum):
    OPEN = "open"
    OVERDUE = "overdue"
    TODAY = "today"
    UPCOMING = "upcoming"
    DONE = "done"


def _now() -> datetime:
    return datetime.now(UTC)


def _today() -> date:
    return _now().date()


def _require_business(db: Session, business_id: int) -> Business:
    business = db.query(Business).filter(Business.id == business_id, compliance_service.not_blocked_filter()).first()
    if business is None:
        raise NotFoundException("Business not found")
    return business


def _require_user(db: Session, user_id: int) -> User:
    user = db.query(User).filter(User.id == user_id, User.is_active.is_(True)).first()
    if user is None:
        raise BadRequestException(ASSIGNEE_MESSAGE)
    return user


def _people(db: Session, user_ids: set[int | None]) -> dict[int, dict]:
    ids = {user_id for user_id in user_ids if user_id is not None}
    if not ids:
        return {}
    rows = db.query(User.id, User.full_name).filter(User.id.in_(ids)).all()
    return {user_id: {"id": user_id, "full_name": full_name} for user_id, full_name in rows}


def add_system_activity(
    db: Session, business_id: int, kind: ActivityKind, actor_id: int | None, *, summary: str | None = None,
    from_value: str | None = None, to_value: str | None = None,
) -> LeadActivity:
    activity = LeadActivity(
        business_id=business_id, kind=kind.value, summary=summary, from_value=from_value, to_value=to_value,
        created_by_id=actor_id,
    )
    db.add(activity)
    return activity


def record_assignment(db: Session, business_id: int, before: str | None, after: str | None, actor_id: int | None) -> None:
    if before == after:
        return
    add_system_activity(
        db, business_id, ActivityKind.ASSIGNMENT, actor_id,
        from_value=before or UNASSIGNED_LABEL, to_value=after or UNASSIGNED_LABEL,
    )


def _validate_outcome(new_status: str, outcome_in: OutcomeInput | None) -> None:
    if outcome_in is None:
        return
    kind = CLOSING_STATUSES.get(new_status)
    if kind is None:
        raise BadRequestException(NOT_CLOSED_MESSAGE)
    if kind == OutcomeKind.WON and outcome_in.loss_reason is not None:
        raise BadRequestException(WON_REJECTS_REASON_MESSAGE)
    if kind == OutcomeKind.LOST and (outcome_in.value is not None or outcome_in.product):
        raise BadRequestException(LOST_REJECTS_DEAL_MESSAGE)


def apply_status_change(
    db: Session, business: Business, new_status: str, actor_id: int | None, outcome_in: OutcomeInput | None = None
) -> bool:
    _validate_outcome(new_status, outcome_in)
    before = business.lead_status
    changed = before != new_status
    if changed:
        add_system_activity(db, business.id, ActivityKind.STATUS_CHANGE, actor_id, from_value=before, to_value=new_status)
        business.lead_status = new_status
    _sync_outcome(db, business.id, new_status, changed, outcome_in, actor_id)
    if changed:
        webhooks_service.emit(
            db,
            WebhookEvent.LEAD_STATUS_CHANGED,
            lambda: {
                "lead": webhook_events.lead_snapshot(db, business),
                "from_status": before,
                "to_status": new_status,
                "outcome": webhook_events.outcome_snapshot(db, business.id),
            },
        )
    return changed


def _sync_outcome(
    db: Session, business_id: int, status: str, changed: bool, outcome_in: OutcomeInput | None, actor_id: int | None
) -> None:
    kind = CLOSING_STATUSES.get(status)
    existing = db.query(LeadOutcome).filter(LeadOutcome.business_id == business_id).first()

    if kind is None:
        if existing is not None:
            db.delete(existing)
        return

    is_new_close = existing is None or existing.kind != kind.value
    if existing is None:
        existing = LeadOutcome(business_id=business_id, kind=kind.value, closed_at=_now(), closed_by_id=actor_id)
        db.add(existing)
    elif is_new_close:
        existing.kind = kind.value
        existing.value = existing.product = existing.loss_reason = existing.note = None
        existing.closed_at = _now()
        existing.closed_by_id = actor_id

    if outcome_in is None:
        return
    given = outcome_in.model_fields_set
    if "value" in given:
        existing.value = outcome_in.value
    if "product" in given:
        existing.product = (outcome_in.product or "").strip() or None
    if "loss_reason" in given:
        existing.loss_reason = outcome_in.loss_reason.value if outcome_in.loss_reason else None
    if "note" in given:
        existing.note = (outcome_in.note or "").strip() or None
    if not is_new_close and not changed:
        add_system_activity(db, business_id, ActivityKind.OUTCOME_UPDATED, actor_id)


def get_outcome(db: Session, business_id: int) -> dict | None:
    outcome = db.query(LeadOutcome).filter(LeadOutcome.business_id == business_id).first()
    if outcome is None:
        return None
    return {
        "kind": outcome.kind,
        "value": outcome.value,
        "product": outcome.product,
        "loss_reason": outcome.loss_reason,
        "note": outcome.note,
        "closed_at": outcome.closed_at,
        "closed_by": _people(db, {outcome.closed_by_id}).get(outcome.closed_by_id),
    }


def get_activities(db: Session, business_id: int, page: int = FIRST_PAGE, limit: int = DEFAULT_ACTIVITY_LIMIT) -> dict:
    _require_business(db, business_id)
    query = db.query(LeadActivity).filter(LeadActivity.business_id == business_id)
    total = query.count()
    rows = query.order_by(LeadActivity.created_at.desc(), LeadActivity.id.desc()).offset((page - 1) * limit).limit(limit).all()
    people = _people(db, {row.created_by_id for row in rows})
    return {
        "data": [
            {
                "id": row.id, "kind": row.kind, "summary": row.summary, "from_value": row.from_value,
                "to_value": row.to_value, "created_by": people.get(row.created_by_id), "created_at": row.created_at,
            }
            for row in rows
        ],
        "count": total,
    }


def add_activity(db: Session, business_id: int, activity_in: ActivityCreate, actor_id: int) -> dict:
    _require_business(db, business_id)
    activity = LeadActivity(
        business_id=business_id, kind=activity_in.kind.value, summary=activity_in.summary, created_by_id=actor_id
    )
    db.add(activity)
    db.commit()
    db.refresh(activity)
    return get_activity_view(db, activity)


def get_activity_view(db: Session, activity: LeadActivity) -> dict:
    return {
        "id": activity.id, "kind": activity.kind, "summary": activity.summary, "from_value": activity.from_value,
        "to_value": activity.to_value, "created_by": _people(db, {activity.created_by_id}).get(activity.created_by_id),
        "created_at": activity.created_at,
    }


def _task_rows(db: Session):
    return (
        db.query(LeadTask, Business.name)
        .join(Business, Business.id == LeadTask.business_id)
        .filter(compliance_service.not_blocked_filter())
    )


def _scoped(query, scope: TaskScope, today: date):
    if scope == TaskScope.DONE:
        return query.filter(LeadTask.completed_at.isnot(None))
    query = query.filter(LeadTask.completed_at.is_(None))
    if scope == TaskScope.OVERDUE:
        return query.filter(LeadTask.due_on < today)
    if scope == TaskScope.TODAY:
        return query.filter(LeadTask.due_on == today)
    if scope == TaskScope.UPCOMING:
        return query.filter(LeadTask.due_on > today)
    return query


def _task_view(task: LeadTask, business_name: str, people: dict[int, dict]) -> dict:
    return {
        "id": task.id, "business_id": task.business_id, "business_name": business_name, "title": task.title,
        "due_on": task.due_on, "assigned_to": people.get(task.assigned_to_id), "completed_at": task.completed_at,
        "created_at": task.created_at,
    }


def get_tasks(
    db: Session, *, scope: TaskScope, today: date | None, assigned_to_id: int | None, business_id: int | None,
    page: int, limit: int,
) -> dict:
    today = today or _today()
    query = _scoped(_task_rows(db), scope, today)
    if assigned_to_id is not None:
        query = query.filter(LeadTask.assigned_to_id == assigned_to_id)
    if business_id is not None:
        query = query.filter(LeadTask.business_id == business_id)
    total = query.count()
    order = (LeadTask.completed_at.desc(), LeadTask.id.desc()) if scope == TaskScope.DONE else (LeadTask.due_on, LeadTask.id)
    rows = query.order_by(*order).offset((page - 1) * limit).limit(limit).all()
    people = _people(db, {task.assigned_to_id for task, _ in rows})
    return {"data": [_task_view(task, name, people) for task, name in rows], "count": total}


def get_task_summary(db: Session, today: date | None, assigned_to_id: int | None) -> dict:
    today = today or _today()
    query = _scoped(_task_rows(db), TaskScope.OPEN, today)
    if assigned_to_id is not None:
        query = query.filter(LeadTask.assigned_to_id == assigned_to_id)
    overdue, due_today, total = query.with_entities(
        func.coalesce(func.sum(case((LeadTask.due_on < today, 1), else_=0)), 0),
        func.coalesce(func.sum(case((LeadTask.due_on == today, 1), else_=0)), 0),
        func.count(LeadTask.id),
    ).one()
    return {"overdue": int(overdue), "due_today": int(due_today), "open": int(total)}


def _get_task(db: Session, task_id: int) -> tuple[LeadTask, str]:
    row = _task_rows(db).filter(LeadTask.id == task_id).first()
    if row is None:
        raise NotFoundException("Task not found")
    return row


def create_task(db: Session, business_id: int, task_in: TaskCreate, actor_id: int) -> dict:
    _require_business(db, business_id)
    assignee_id = task_in.assigned_to_id if "assigned_to_id" in task_in.model_fields_set else actor_id
    if assignee_id is not None:
        _require_user(db, assignee_id)
    task = LeadTask(
        business_id=business_id, title=task_in.title, due_on=task_in.due_on, assigned_to_id=assignee_id,
        created_by_id=actor_id,
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    return get_task_view(db, task.id)


def get_task_view(db: Session, task_id: int) -> dict:
    task, name = _get_task(db, task_id)
    return _task_view(task, name, _people(db, {task.assigned_to_id}))


def update_task(db: Session, task_id: int, update_in: TaskUpdate, actor_id: int) -> dict:
    task, _ = _get_task(db, task_id)
    given = update_in.model_fields_set
    if not given:
        raise BadRequestException(NOTHING_TO_UPDATE_MESSAGE)
    if "title" in given and update_in.title is None:
        raise BadRequestException("A task needs a title")
    if "due_on" in given and update_in.due_on is None:
        raise BadRequestException("A task needs a due date")
    if "done" in given and update_in.done is None:
        raise BadRequestException("done must be true or false")
    if update_in.assigned_to_id is not None:
        _require_user(db, update_in.assigned_to_id)

    if "title" in given:
        task.title = update_in.title
    if "due_on" in given:
        task.due_on = update_in.due_on
    if "assigned_to_id" in given:
        task.assigned_to_id = update_in.assigned_to_id
    if "done" in given:
        if update_in.done and task.completed_at is None:
            task.completed_at = _now()
            task.completed_by_id = actor_id
            add_system_activity(db, task.business_id, ActivityKind.TASK_COMPLETED, actor_id, summary=task.title)
        elif not update_in.done:
            task.completed_at = None
            task.completed_by_id = None
    db.commit()
    return get_task_view(db, task_id)


def delete_task(db: Session, task_id: int) -> None:
    task, _ = _get_task(db, task_id)
    db.delete(task)
    db.commit()


def get_config() -> dict:
    return {"deal_currency": settings.DEAL_CURRENCY}
