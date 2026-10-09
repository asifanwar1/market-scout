import json
import os
import sqlite3
from collections.abc import Iterable, Iterator
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from app.core.scouting.normalize import normalize_name

SCHEMA_VERSION = "2"
STATUS_PERMANENTLY_CLOSED = "permanently_closed"
EMPTY_STORE_MESSAGE = "There were no places to save, so the existing file was left as it is."

_BATCH_SIZE = 5000

_CREATE = """
CREATE TABLE meta (key TEXT PRIMARY KEY, value TEXT NOT NULL);
CREATE TABLE places (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    name_key TEXT NOT NULL,
    categories TEXT NOT NULL,
    confidence REAL NOT NULL,
    status TEXT,
    phones TEXT NOT NULL,
    websites TEXT NOT NULL,
    emails TEXT NOT NULL,
    socials TEXT NOT NULL,
    address TEXT,
    city TEXT,
    latitude REAL NOT NULL,
    longitude REAL NOT NULL,
    dataset TEXT
);
"""
_INDEXES = (
    "CREATE INDEX ix_places_position ON places (latitude, longitude);",
    "CREATE INDEX ix_places_name_key ON places (name_key);",
)

_INSERT = """
INSERT OR REPLACE INTO places (id, name, name_key, categories, confidence, status, phones, websites, emails, socials,
                               address, city, latitude, longitude, dataset)
VALUES (:id, :name, :name_key, :categories, :confidence, :status, :phones, :websites, :emails, :socials,
        :address, :city, :latitude, :longitude, :dataset)
"""


class StoreError(Exception):
    pass


@dataclass(frozen=True)
class StoreInfo:
    release: str
    places: int
    built_at: str


@dataclass(frozen=True)
class Place:
    id: str
    name: str
    categories: list[str]
    confidence: float
    phones: list[str]
    websites: list[str]
    emails: list[str]
    socials: list[str]
    address: str | None
    city: str | None
    latitude: float
    longitude: float
    dataset: str | None


def category_text(categories: Iterable[str | None]) -> str:
    names = [name for name in dict.fromkeys(categories) if name]
    return f"|{'|'.join(names)}|" if names else "|"


def write_store(path: str | Path, places: Iterable[dict], release: str) -> int:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    building = target.with_name(target.name + ".building")
    building.unlink(missing_ok=True)

    connection = sqlite3.connect(building)
    try:
        connection.executescript(_CREATE)
        batch: list[dict] = []
        for place in places:
            batch.append(_encode(place))
            if len(batch) >= _BATCH_SIZE:
                connection.executemany(_INSERT, batch)
                batch.clear()
        if batch:
            connection.executemany(_INSERT, batch)
        for statement in _INDEXES:
            connection.execute(statement)
        count = connection.execute("SELECT COUNT(*) FROM places").fetchone()[0]
        connection.executemany(
            "INSERT INTO meta (key, value) VALUES (?, ?)",
            [
                ("schema_version", SCHEMA_VERSION),
                ("release", release),
                ("places", str(count)),
                ("built_at", datetime.now(UTC).isoformat(timespec="seconds")),
            ],
        )
        connection.commit()
        if count == 0:
            raise StoreError(EMPTY_STORE_MESSAGE)
    except BaseException:
        connection.close()
        building.unlink(missing_ok=True)
        raise
    connection.close()

    os.replace(building, target)
    return count


def _encode(place: dict) -> dict:
    return {
        "id": place["id"],
        "name": place["name"],
        "name_key": normalize_name(place["name"]),
        "categories": category_text(place.get("categories") or []),
        "confidence": float(place.get("confidence") or 0),
        "status": place.get("status"),
        "phones": json.dumps(place.get("phones") or []),
        "websites": json.dumps(place.get("websites") or []),
        "emails": json.dumps(place.get("emails") or []),
        "socials": json.dumps(place.get("socials") or []),
        "address": place.get("address"),
        "city": place.get("city"),
        "latitude": place["latitude"],
        "longitude": place["longitude"],
        "dataset": place.get("dataset"),
    }


def connect(path: str | Path) -> sqlite3.Connection:
    file = Path(path)
    if not file.is_file():
        raise StoreError("The place data has not been downloaded yet.")
    try:
        connection = sqlite3.connect(f"{file.resolve().as_uri()}?mode=ro", uri=True)
        _check_layout(connection)
    except sqlite3.DatabaseError as exc:
        raise StoreError(f"The place data file can't be read ({exc}). Download it again.") from exc
    return connection


def _check_layout(connection: sqlite3.Connection) -> None:
    row = connection.execute("SELECT value FROM meta WHERE key = 'schema_version'").fetchone()
    if row is None or row[0] != SCHEMA_VERSION:
        connection.close()
        raise StoreError("The place data file is from an older version of the app. Download it again.")


def read_info(path: str | Path) -> StoreInfo:
    connection = connect(path)
    try:
        meta = dict(connection.execute("SELECT key, value FROM meta").fetchall())
    finally:
        connection.close()
    return StoreInfo(release=meta.get("release", "unknown"), places=int(meta.get("places", 0)), built_at=meta.get("built_at", ""))


def rows_to_places(rows: Iterable[sqlite3.Row | tuple]) -> Iterator[Place]:
    for row in rows:
        (identifier, name, categories, confidence, phones, websites, emails, socials, address, city, latitude, longitude, dataset) = row
        yield Place(
            id=identifier,
            name=name,
            categories=[part for part in categories.split("|") if part],
            confidence=confidence,
            phones=json.loads(phones),
            websites=json.loads(websites),
            emails=json.loads(emails),
            socials=json.loads(socials),
            address=address,
            city=city,
            latitude=latitude,
            longitude=longitude,
            dataset=dataset,
        )


PLACE_COLUMNS = (
    "id, name, categories, confidence, phones, websites, emails, socials, address, city, latitude, longitude, dataset"
)


def find_by_name_key(
    connection: sqlite3.Connection,
    name_key: str,
    rectangle: tuple[float, float, float, float] | None,
    min_confidence: float,
    limit: int = 2,
) -> list[Place]:
    sql = (
        f"SELECT {PLACE_COLUMNS} FROM places "
        "WHERE name_key = ? AND confidence >= ? AND (status IS NULL OR status != ?)"
    )
    params: list = [name_key, min_confidence, STATUS_PERMANENTLY_CLOSED]
    if rectangle is not None:
        south, west, north, east = rectangle
        sql += " AND latitude BETWEEN ? AND ? AND longitude BETWEEN ? AND ?"
        params += [south, north, west, east]
    sql += " ORDER BY confidence DESC, id LIMIT ?"
    params.append(limit)
    return list(rows_to_places(connection.execute(sql, params).fetchall()))
