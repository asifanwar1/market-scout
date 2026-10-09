import argparse
import sys
import time

import httpx

from app.core.config import settings
from app.core.constants import COUNTRY_CODE_PAKISTAN, PAKISTAN_BOUNDS
from app.core.scouting import place_store

CATALOG_URL = "https://stac.overturemaps.org/catalog.json"
BUCKET = "s3://overturemaps-us-west-2/release"
FETCH_ROWS = 20000

_QUERY = """
SELECT id, names.primary AS name, taxonomy.primary AS category, taxonomy.alternates AS alternates,
       confidence, operating_status, phones, websites, emails, socials,
       addresses[1].freeform AS address, addresses[1].locality AS city,
       bbox.ymin AS latitude, bbox.xmin AS longitude, sources[1].dataset AS dataset
FROM {source}
WHERE bbox.xmin BETWEEN {west} AND {east} AND bbox.ymin BETWEEN {south} AND {north}
  AND addresses[1].country = '{country}'
"""


def latest_release() -> str:
    response = httpx.get(CATALOG_URL, timeout=30, follow_redirects=True)
    response.raise_for_status()
    release = response.json().get("latest")
    if not release:
        raise SystemExit("Could not find Overture's latest release; pass one with --release.")
    return release


def to_place(row: tuple) -> dict | None:
    (identifier, name, category, alternates, confidence, status, phones, websites, emails, socials,
     address, city, latitude, longitude, dataset) = row
    if not name or latitude is None or longitude is None:
        return None
    return {
        "id": identifier,
        "name": name.strip(),
        "categories": [category, *(alternates or [])],
        "confidence": confidence,
        "status": status,
        "phones": phones or [],
        "websites": websites or [],
        "emails": emails or [],
        "socials": socials or [],
        "address": address,
        "city": city,
        "latitude": latitude,
        "longitude": longitude,
        "dataset": dataset,
    }


def stream_places(cursor):
    seen = 0
    while rows := cursor.fetchmany(FETCH_ROWS):
        for row in rows:
            place = to_place(row)
            if place is not None:
                yield place
        seen += len(rows)
        print(f"  read {seen:,} places...", flush=True)


def main() -> None:
    parser = argparse.ArgumentParser(description="Download Pakistan's Overture Maps places for the Overture source.")
    parser.add_argument("--release", help="An Overture release such as 2026-09-23.1 (default: the latest).")
    args = parser.parse_args()

    try:
        import duckdb
    except ImportError:
        raise SystemExit("DuckDB is needed for this step: pip install -r requirements-dev.txt") from None

    release = args.release or latest_release()
    connection = duckdb.connect()
    connection.execute("INSTALL httpfs; LOAD httpfs; SET s3_region='us-west-2';")
    source = f"read_parquet('{BUCKET}/{release}/theme=places/type=place/*', hive_partitioning=1)"

    print(f"Overture release {release}: reading Pakistan's places (this takes a few minutes)...", flush=True)
    started = time.time()
    cursor = connection.execute(_QUERY.format(source=source, country=COUNTRY_CODE_PAKISTAN, **PAKISTAN_BOUNDS))
    count = place_store.write_store(settings.OVERTURE_DB_PATH, stream_places(cursor), release)
    print(f"Done in {time.time() - started:.0f}s: {count:,} places saved to {settings.OVERTURE_DB_PATH}")
    print("No restart needed: the Overture Maps source uses the new file from its next search.")


if __name__ == "__main__":
    sys.exit(main())
