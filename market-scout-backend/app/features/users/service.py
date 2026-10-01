from sqlalchemy.orm import Session

from app.core.constants import FIRST_PAGE
from app.core.exceptions import BadRequestException, ConflictException, NotFoundException
from app.core.security import hash_password
from app.features.users.models import User, UserRole
from app.features.users.schemas import UserCreate, UserUpdate

DEFAULT_LIMIT = 10



def _normalize_email(email: str) -> str:
    return email.strip().lower()


def get_users(
    db: Session,
    page: int = FIRST_PAGE,
    limit: int = DEFAULT_LIMIT,
    search: str | None = None,
    role: UserRole | None = None,
) -> dict:
    query = db.query(User)

    if role is not None:
        query = query.filter(User.role == role.value)

    if search:
        normalized_search = search.strip()
        if normalized_search:
            search_term = f"%{normalized_search}%"
            query = query.filter(User.email.ilike(search_term) | User.full_name.ilike(search_term))

    total_count = query.count()
    offset = (page - 1) * limit
    users = query.order_by(User.created_at.desc(), User.id.desc()).offset(offset).limit(limit).all()
    return {"data": users, "count": total_count}


def get_user_by_id(db: Session, user_id: int) -> User:
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise NotFoundException("User not found")
    return user


def get_user_by_email(db: Session, email: str) -> User | None:
    return db.query(User).filter(User.email == _normalize_email(email)).first()


def create_user(db: Session, user_in: UserCreate) -> User:
    email = _normalize_email(user_in.email)
    if get_user_by_email(db, email):
        raise ConflictException("A user with this email already exists")

    user = User(
        email=email,
        full_name=user_in.full_name.strip(),
        role=user_in.role.value,
        hashed_password=hash_password(user_in.password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def update_user(db: Session, user_id: int, user_in: UserUpdate, acting_user_id: int) -> User:
    user = get_user_by_id(db, user_id)
    update_data = user_in.model_dump(exclude_unset=True)

    if user.id == acting_user_id:
        if update_data.get("is_active") is False:
            raise BadRequestException("You cannot deactivate your own account")
        if "role" in update_data and update_data["role"] != UserRole.ADMIN:
            raise BadRequestException("You cannot remove your own admin role")

    if "full_name" in update_data and update_data["full_name"] is not None:
        user.full_name = update_data["full_name"].strip()
    if update_data.get("role") is not None:
        user.role = update_data["role"].value
    if update_data.get("is_active") is not None:
        user.is_active = update_data["is_active"]
    if update_data.get("password") is not None:
        user.hashed_password = hash_password(update_data["password"])

    if {"role", "is_active", "password"} & update_data.keys():
        user.token_version += 1

    db.commit()
    db.refresh(user)
    return user
