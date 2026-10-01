from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, field_validator, model_validator

from app.core.constants import NAME_MAX_LENGTH, NAME_MIN_LENGTH
from app.features.geographies.models import GeographyLevel

BBOX_LENGTH = 4
LATITUDE_LIMIT = 90
LONGITUDE_LIMIT = 180
RADIUS_KM_MAX = 100



def _validate_bbox(value: Optional[list[float]]) -> Optional[list[float]]:
    if value is None:
        return value
    if len(value) != BBOX_LENGTH:
        raise ValueError("bbox must be [south, west, north, east]")
    south, west, north, east = value
    if not (-LATITUDE_LIMIT <= south < north <= LATITUDE_LIMIT) or not (-LONGITUDE_LIMIT <= west < east <= LONGITUDE_LIMIT):
        raise ValueError("bbox must be [south, west, north, east] with south < north and west < east")
    return value


class GeographyBase(BaseModel):
    name: str = Field(min_length=NAME_MIN_LENGTH, max_length=NAME_MAX_LENGTH)
    parent_id: Optional[int] = None
    latitude: Optional[float] = Field(default=None, ge=-LATITUDE_LIMIT, le=LATITUDE_LIMIT)
    longitude: Optional[float] = Field(default=None, ge=-LONGITUDE_LIMIT, le=LONGITUDE_LIMIT)
    radius_km: Optional[float] = Field(default=None, gt=0, le=RADIUS_KM_MAX)
    bbox: Optional[list[float]] = None

    @field_validator("bbox")
    @classmethod
    def validate_bbox(cls, v: Optional[list[float]]) -> Optional[list[float]]:
        return _validate_bbox(v)


class GeographyCreate(GeographyBase):
    level: GeographyLevel

    @model_validator(mode="after")
    def validate_level_requirements(self) -> "GeographyCreate":
        if self.level == GeographyLevel.COUNTRY and self.parent_id is not None:
            raise ValueError("A country cannot have a parent")
        if self.level != GeographyLevel.COUNTRY and self.parent_id is None:
            raise ValueError("parent_id is required for provinces and cities")
        if self.level == GeographyLevel.CITY and None in (self.latitude, self.longitude, self.radius_km):
            raise ValueError("Cities need latitude, longitude and radius_km (they define the search area)")
        return self


class GeographyUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=NAME_MIN_LENGTH, max_length=NAME_MAX_LENGTH)
    parent_id: Optional[int] = None
    latitude: Optional[float] = Field(default=None, ge=-LATITUDE_LIMIT, le=LATITUDE_LIMIT)
    longitude: Optional[float] = Field(default=None, ge=-LONGITUDE_LIMIT, le=LONGITUDE_LIMIT)
    radius_km: Optional[float] = Field(default=None, gt=0, le=RADIUS_KM_MAX)
    bbox: Optional[list[float]] = None

    @field_validator("bbox")
    @classmethod
    def validate_bbox(cls, v: Optional[list[float]]) -> Optional[list[float]]:
        return _validate_bbox(v)


class GeographyResponse(GeographyBase):
    id: int
    slug: str
    level: GeographyLevel
    created_at: datetime

    model_config = {"from_attributes": True}


class GeographyListResponse(BaseModel):
    data: list[GeographyResponse]
    count: int


class GeographyTreeNode(BaseModel):
    id: int
    name: str
    slug: str
    level: GeographyLevel
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    radius_km: Optional[float] = None
    children: list["GeographyTreeNode"] = Field(default_factory=list)
