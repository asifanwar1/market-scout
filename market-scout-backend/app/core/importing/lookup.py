from dataclasses import replace

from app.core.scouting import overture_store
from app.core.scouting.normalize import normalize_name
from app.core.scouting.sources.overture import place_to_business
from app.core.scouting.types import RawBusiness

MIN_NAME_LENGTH = 4

Rectangle = tuple[float, float, float, float]


class OvertureLookup:
    def __init__(self, path: str, min_confidence: float):
        self._connection = overture_store.connect(path)
        self._min_confidence = min_confidence
        self._release = self._connection.execute("SELECT value FROM meta WHERE key = 'release'").fetchone()[0]

    def close(self) -> None:
        self._connection.close()

    def __enter__(self) -> "OvertureLookup":
        return self

    def __exit__(self, *exc_info) -> None:
        self.close()

    def find(self, name: str, area: Rectangle | None) -> RawBusiness | None:
        key = normalize_name(name)
        if len(key) < MIN_NAME_LENGTH:
            return None
        places = overture_store.find_by_name_key(self._connection, key, area, self._min_confidence, limit=2)
        if len(places) != 1:
            return None
        found = places[0]
        if not (found.phones or found.emails or found.websites or found.socials):
            return None
        return place_to_business(found, self._release)


def fill_from(row: RawBusiness, found: RawBusiness) -> RawBusiness:
    return replace(
        row,
        phones=row.phones or list(found.phones),
        emails=row.emails or list(found.emails),
        website=row.website or found.website,
        latitude=row.latitude if row.latitude is not None else found.latitude,
        longitude=row.longitude if row.longitude is not None else found.longitude,
        categories=list(dict.fromkeys([*row.categories, *found.categories])),
        raw={**row.raw, "contacts_from": {"source": found.source_key, "id": found.external_id}},
    )
