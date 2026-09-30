"""Imports every ORM model in one place.

SQLAlchemy resolves relationships between models by name ("Business" on Geography), which
only works once every model class has been imported. Entry points that don't go through
``app.main`` (Alembic, scripts, a shell) would otherwise fail with "failed to locate a name".
Add each new model here.
"""
from app.features.users.models import User  # noqa: F401
from app.features.geographies.models import Geography  # noqa: F401
from app.features.profiles.models import Profile, ProfileSegment, ProfileSearchTerm  # noqa: F401
from app.features.sources.models import DataSource  # noqa: F401
from app.features.businesses.models import (  # noqa: F401
    Business, ContactPoint, SourceRecord, BusinessClassification,
)
from app.features.compliance.models import DoNotContact  # noqa: F401
from app.features.runs.models import Run, RunTask, run_geographies  # noqa: F401
