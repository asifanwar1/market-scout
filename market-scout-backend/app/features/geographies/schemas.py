from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, field_validator, model_validator
from app.features.geographies.models import GeographyLevel


def _validate_bbox(value: Optional[list[float]]) -> Optional[list[float]]:
    if value is None:
        return value
    if len(value) != 4:
        raise ValueError("bbox must be [south, west, north, east]")
    south, west, north, east = value
    if not (-90 <= south < north <= 90) or not (-180 <= west < east <= 180):
        raise ValueError("bbox must be [south, west, north, east] with south < north and west < east")
    return value


class GeographyBase(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    parent_id: Optional[int] = None
    latitude: Optional[float] = Field(default=None, ge=-90, le=90)
    longitude: Optional[float] = Field(default=None, ge=-180, le=180)
    radius_km: Optional[float] = Field(default=None, gt=0, le=100)
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
    name: Optional[str] = Field(default=None, min_length=2, max_length=100)
    parent_id: Optional[int] = None
    latitude: Optional[float] = Field(default=None, ge=-90, le=90)
    longitude: Optional[float] = Field(default=None, ge=-180, le=180)
    radius_km: Optional[float] = Field(default=None, gt=0, le=100)
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
