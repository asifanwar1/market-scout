# Importing any feature loads every model (see app/models.py), so cross-feature
# relationships always resolve no matter which module a script starts from.
from app import models  # noqa: F401
