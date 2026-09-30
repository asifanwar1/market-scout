from sqlalchemy.orm import Session

from app.core.exceptions import BadRequestException, ConflictException, NotFoundException
from app.core.utils import slugify
from app.features.geographies.models import Geography, GeographyLevel
from app.features.geographies.schemas import GeographyCreate, GeographyUpdate

_PARENT_LEVEL: dict[GeographyLevel, GeographyLevel | None] = {
    GeographyLevel.COUNTRY: None,
    GeographyLevel.PROVINCE: GeographyLevel.COUNTRY,
    GeographyLevel.CITY: GeographyLevel.PROVINCE,
}


def _generate_unique_slug(db: Session, name: str) -> str:
    base_slug = slugify(name, fallback="location")
    slug = base_slug
    counter = 2

    while db.query(Geography).filter(Geography.slug == slug).first():
        slug = f"{base_slug}-{counter}"
        counter += 1
    return slug


def _validate_parent(db: Session, level: GeographyLevel, parent_id: int | None) -> None:
    expected_level = _PARENT_LEVEL[level]
    if expected_level is None:
        if parent_id is not None:
            raise BadRequestException("A country cannot have a parent")
        return

    if parent_id is None:
        raise BadRequestException(f"A {level.value} needs a parent {expected_level.value}")

    parent = db.query(Geography).filter(Geography.id == parent_id).first()
    if not parent:
        raise NotFoundException("Parent location not found")
    if parent.level != expected_level.value:
        raise BadRequestException(f"A {level.value} must belong to a {expected_level.value}")


def _ensure_name_available(db: Session, name: str, parent_id: int | None, exclude_id: int | None = None) -> None:
    query = db.query(Geography).filter(Geography.parent_id == parent_id, Geography.name == name)
    if exclude_id is not None:
        query = query.filter(Geography.id != exclude_id)
    if query.first():
        raise ConflictException(f"'{name}' already exists in this location")


def get_geographies(
    db: Session,
    page: int = 1,
    limit: int = 50,
    search: str | None = None,
    level: GeographyLevel | None = None,
    parent_id: int | None = None,
) -> dict:
    query = db.query(Geography)

    if level is not None:
        query = query.filter(Geography.level == level.value)
    if parent_id is not None:
        query = query.filter(Geography.parent_id == parent_id)
    if search:
        normalized_search = search.strip()
        if normalized_search:
            query = query.filter(Geography.name.ilike(f"%{normalized_search}%"))

    total_count = query.count()
    offset = (page - 1) * limit
    geographies = query.order_by(Geography.name, Geography.id).offset(offset).limit(limit).all()
    return {"data": geographies, "count": total_count}


def get_geography_tree(db: Session) -> list[dict]:
    geographies = db.query(Geography).order_by(Geography.name, Geography.id).all()
    nodes = {
        g.id: {
            "id": g.id,
            "name": g.name,
            "slug": g.slug,
            "level": g.level,
            "latitude": g.latitude,
            "longitude": g.longitude,
            "radius_km": g.radius_km,
            "children": [],
        }
        for g in geographies
    }

    roots: list[dict] = []
    for g in geographies:
        if g.parent_id in nodes:
            nodes[g.parent_id]["children"].append(nodes[g.id])
        else:
            roots.append(nodes[g.id])
    return roots


def get_city_ids(db: Session, geography_id: int) -> list[int]:
    """The city itself, or every city inside a province / country."""
    geography = get_geography_by_id(db, geography_id)
    city_ids: list[int] = []
    frontier = [geography]
    while frontier:
        current = frontier.pop()
        if current.level == GeographyLevel.CITY.value:
            city_ids.append(current.id)
        else:
            frontier.extend(current.children)
    return city_ids


def get_geography_by_id(db: Session, geography_id: int) -> Geography:
    geography = db.query(Geography).filter(Geography.id == geography_id).first()
    if not geography:
        raise NotFoundException("Location not found")
    return geography


def get_geography_by_slug(db: Session, slug: str) -> Geography | None:
    return db.query(Geography).filter(Geography.slug == slug).first()


def create_geography(db: Session, geography_in: GeographyCreate) -> Geography:
    _validate_parent(db, geography_in.level, geography_in.parent_id)
    _ensure_name_available(db, geography_in.name, geography_in.parent_id)

    geography = Geography(
        **geography_in.model_dump(exclude={"level"}),
        level=geography_in.level.value,
        slug=_generate_unique_slug(db, geography_in.name),
    )
    db.add(geography)
    db.commit()
    db.refresh(geography)
    return geography


def update_geography(db: Session, geography_id: int, geography_in: GeographyUpdate) -> Geography:
    geography = get_geography_by_id(db, geography_id)
    update_data = geography_in.model_dump(exclude_unset=True)
    level = GeographyLevel(geography.level)

    if "parent_id" in update_data:
        if update_data["parent_id"] == geography.id:
            raise BadRequestException("A location cannot be its own parent")
        _validate_parent(db, level, update_data["parent_id"])

    if "name" in update_data or "parent_id" in update_data:
        _ensure_name_available(
            db,
            update_data.get("name", geography.name),
            update_data.get("parent_id", geography.parent_id),
            exclude_id=geography.id,
        )

    if level == GeographyLevel.CITY:
        area = [update_data.get(f, getattr(geography, f)) for f in ("latitude", "longitude", "radius_km")]
        if None in area:
            raise BadRequestException("Cities need latitude, longitude and radius_km")

    # The slug is deliberately not regenerated on rename: it is the stable identifier
    # other data and seed scripts refer to.
    for field, value in update_data.items():
        setattr(geography, field, value)
    db.commit()
    db.refresh(geography)
    return geography


def delete_geography(db: Session, geography_id: int) -> None:
    geography = get_geography_by_id(db, geography_id)
    if db.query(Geography).filter(Geography.parent_id == geography.id).first():
        raise ConflictException("Remove or move the locations inside this one first")
    db.delete(geography)
    db.commit()
