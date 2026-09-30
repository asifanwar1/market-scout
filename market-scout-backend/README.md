# Market Scout Backend

The API backend for Market Scout, a reusable business-discovery and market-intelligence system (first use: finding solar dealers, installers, importers and contractors across Pakistan). Built with FastAPI and Python; the React UI lives in the sibling `market-scout` folder.

## Tech Stack

- **FastAPI** + **Uvicorn**
- **SQLAlchemy** + **Alembic** (migrations) on **SQLite** for now, written so PostgreSQL is a config change later
- **Pydantic** / **Pydantic Settings**
- **python-jose** + **bcrypt** (auth), **SlowAPI** (rate limiting)
- **Pytest**

## Prerequisites

- **Python** 3.11+
- `pip` and `venv`

## Getting Started

1. **Create and activate a virtual environment**

   ```bash
   python -m venv venv
   venv\Scripts\activate   # Windows
   source venv/bin/activate  # macOS/Linux
   ```

2. **Install dependencies**

   ```bash
   pip install -r requirements.txt
   ```

3. **Configure environment variables**

   Copy `.env.example` to `.env` and set `SECRET_KEY` (generate one with
   `python -c "import secrets; print(secrets.token_urlsafe(48))"`).

4. **Run database migrations**

   ```bash
   alembic upgrade head
   ```

5. **Create the first admin** (users can only be created by an admin through the API)

   ```bash
   python -m scripts.create_admin --email you@example.com --password "Str0ng!Pass" --name "Your Name"
   ```

6. **Load the default data** (Pakistan's provinces and cities, and the solar profile).
   Safe to run again; anything that already exists is left untouched.

   ```bash
   python -m scripts.seed
   ```

7. **Start the development server**

   ```bash
   uvicorn app.main:app --reload
   ```

   API docs are at http://localhost:8000/docs.

8. **Run tests**

   ```bash
   pytest
   ```

   Tests run against a throwaway SQLite file and roll back after every test.

## Roles

- **admin** — everything, including managing users, profiles, locations, sources and runs, and lifting do-not-contact blocks.
- **sales** — works the leads: list/filter/search them, change status, notes and assignee, mark a business "do not contact". Can read profiles and locations. Can't see or start runs, change sources, or manage users.

## Profiles and locations

- A **profile** is an industry pack: segments (e.g. dealer, importer), search terms and scoring weights. Solar is the first; new industries are added through the API/UI with no code changes.
- Each search term has `text` (for text-search sources such as Google Places) and an optional `osm_filter` (for OpenStreetMap). Terms without an `osm_filter` are skipped by OpenStreetMap.
- **Locations** form a country → province → city hierarchy. A city's latitude, longitude and `radius_km` define the area that is searched (the square that contains that radius, or an explicit `bbox`); the seeded values are approximations you can adjust.

## Data sources and runs

A **run** searches a profile's terms in chosen cities using chosen sources, then reads each found business's own website for more contact details. Everything is done by a single background thread inside the server (started on boot, `RUN_WORKER_ENABLED`); progress is polled from `GET /api/v1/runs/{id}`.

- **Sources** (`/api/v1/sources`, admin only) are switched on/off, and given an API key, from the UI — no code change.
  - **OpenStreetMap** — free, no key. Phone numbers are patchy in Pakistan, and the public Overpass server throttles, so requests are spaced out and retried with backoff.
  - **Google Places API** — needs a key (saved encrypted from the UI, or `GOOGLE_PLACES_API_KEY`). Billed per request, so a run can carry a request cap and `POST /runs/estimate` previews the number of searches and cost first.
  - **Website enrichment** — reads each business's own site (robots.txt honoured, public addresses only) for email, WhatsApp and social pages.
- Results from all sources are merged into one business (same website, same phone with a similar name, or same spot with a near-identical name). Every phone/email records which source reported it, and each source's raw answer is kept.
- Each run stores per-source quality (found / new / merged / with phone / website / email) so you can see whether a paid source is worth it.
- A search that finished within `RUN_TASK_CACHE_DAYS` is skipped by later runs unless `refresh` is set. A run interrupted by a restart can be resumed.

## Leads and do-not-contact

- **Leads** (`/api/v1/businesses`) — the businesses runs have found. `GET /` filters by profile, segment, location (a city, province or the country), phone / WhatsApp-capable / email / website, status, assignee, source, minimum score, and a text search over name, address, phone (typed any way: `0300…`, `+92 300…`) and email. It sorts by score (default when a profile is chosen), newest, last seen or name. `PATCH /{id}` edits only the sales fields (status, notes, assignee); `POST /bulk-update` changes status/assignee for up to 500 at once.
- **Score** is the sum of a profile's weights for the signals a lead has (phone, WhatsApp-capable mobile, website, email, reviews, name matches its segment).
- **Do-not-contact** (`/api/v1/compliance/do-not-contact`, and `POST /businesses/{id}/do-not-contact`) — anyone can record "please stop contacting us" for a business, a phone number or an email; only an admin can lift it. Blocking a business also blocks its phones and emails, so if a later scrape finds the same shop as a new record with the same number, it's refused too. Blocked people are removed from every leads endpoint (a blocked business is "not found"), and refused during runs (counted as `blocked` in the run stats). Exports and the live sheet will use the same filter.

## Project Structure

```
app/
├── core/         # Cross-cutting concerns (security, exceptions, rate limiter, crypto)
│   └── scouting/ # The engine: sources, website enrichment, phone/name normalisation, de-duplication,
│                 #   classification. Pure Python: no database or web framework.
├── features/     # Feature modules (auth, users, profiles, geographies, sources, runs, businesses, compliance)
│                 #   each with router/service/schemas/models
├── models.py     # Imports every ORM model (add new ones here)
├── config.py     # App configuration/settings
├── database.py   # Engine/session setup (SQLite pragmas applied here)
├── dependencies.py  # Shared FastAPI dependencies
└── main.py       # Application entry point

alembic/          # Database migrations
scripts/          # Utility/maintenance scripts (create_admin, seed + seed_data/)
tests/            # Test suite
```

## Notes

- **Error responses.** A database conflict the service layer didn't anticipate comes back as `409` (not a 500), and even a genuine `500` carries the CORS headers for allowed origins, so the browser shows the real error instead of an opaque "Network Error".

- The first migration was generated on SQLite. When moving to PostgreSQL, point `DATABASE_URL` at a fresh database and regenerate the initial migration (or review it) before deploying.

## Status

In development. Completed: foundation, auth, user management, profiles, locations, seed data, scouting engine, sources, runs, leads API, do-not-contact. Still to come: the UI, Sheets sync and export, and insights.
