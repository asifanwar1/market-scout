import argparse
import sys
import time
from datetime import date

from app.core.config import settings
from app.core.constants import COUNTRY_CODE_PAKISTAN, PAKISTAN_BOUNDS
from app.core.scouting import place_store

DATASET_NAME = "foursquare"
FACEBOOK_URL = "https://www.facebook.com/{}"
INSTAGRAM_URL = "https://www.instagram.com/{}"
CONFIDENCE = 1.0
FETCH_ROWS = 20000
DESCRIPTION = "Make the local copy of Pakistan's Foursquare places from Foursquare Open Source Places Parquet files."
PARQUET_HELP = "A Parquet file, a folder pattern such as data/*.parquet, or several of them (repeat the option)."
RELEASE_HELP = "A label for this copy, shown on the Sources screen (default: today's date)."
NO_FILES_MESSAGE = (
    "No Parquet files given. Get the Foursquare Open Source Places files from the Places Portal and pass them with --parquet."
)
DUCKDB_MISSING_MESSAGE = "DuckDB is needed for this step: pip install -r requirements-dev.txt"
NO_PLACES_MESSAGE = "No places in Pakistan were found in those files. Check that they are Foursquare Open Source Places files."
DONE_MESSAGE = "Done in {seconds:.0f}s: {count:,} places saved to {path}"
RESTART_MESSAGE = "No restart needed: the Foursquare Places source uses the new file from its next search."

_QUERY = """
SELECT fsq_place_id, name, fsq_category_labels, date_closed, tel, website, email, facebook_id, instagram,
       address, locality, latitude, longitude
FROM read_parquet(?)
WHERE country = ? AND latitude BETWEEN ? AND ? AND longitude BETWEEN ? AND ?
"""


def to_place(row: tuple) -> dict | None:
    (identifier, name, labels, date_closed, tel, website, email, facebook_id, instagram, address, locality, latitude, longitude) = row
    if not identifier or not name or latitude is None or longitude is None:
        return None
    socials = []
    if facebook_id:
        socials.append(FACEBOOK_URL.format(str(facebook_id).strip()))
    if instagram:
        socials.append(INSTAGRAM_URL.format(instagram.strip().lstrip("@")))
    return {
        "id": identifier,
        "name": name.strip(),
        "categories": list(labels or []),
        "confidence": CONFIDENCE,
        "status": place_store.STATUS_PERMANENTLY_CLOSED if date_closed else None,
        "phones": [tel.strip()] if tel and tel.strip() else [],
        "websites": [website.strip()] if website and website.strip() else [],
        "emails": [email.strip()] if email and email.strip() else [],
        "socials": socials,
        "address": address,
        "city": locality,
        "latitude": float(latitude),
        "longitude": float(longitude),
        "dataset": DATASET_NAME,
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


def build_store(files: list[str], release: str, path: str) -> int:
    import duckdb

    bounds = PAKISTAN_BOUNDS
    connection = duckdb.connect()
    cursor = connection.execute(
        _QUERY, [files, COUNTRY_CODE_PAKISTAN, bounds["south"], bounds["north"], bounds["west"], bounds["east"]]
    )
    return place_store.write_store(path, stream_places(cursor), release)


def main() -> None:
    parser = argparse.ArgumentParser(description=DESCRIPTION)
    parser.add_argument("--parquet", action="append", default=[], help=PARQUET_HELP)
    parser.add_argument("--release", default=date.today().isoformat(), help=RELEASE_HELP)
    args = parser.parse_args()

    if not args.parquet:
        raise SystemExit(NO_FILES_MESSAGE)
    try:
        import duckdb  # noqa: F401
    except ImportError:
        raise SystemExit(DUCKDB_MISSING_MESSAGE) from None

    started = time.time()
    try:
        count = build_store(args.parquet, args.release, settings.FOURSQUARE_DB_PATH)
    except place_store.StoreError:
        raise SystemExit(NO_PLACES_MESSAGE) from None
    print(DONE_MESSAGE.format(seconds=time.time() - started, count=count, path=settings.FOURSQUARE_DB_PATH))
    print(RESTART_MESSAGE)


if __name__ == "__main__":
    sys.exit(main())
