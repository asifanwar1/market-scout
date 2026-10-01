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

   API docs are at http://localhost:8000/docs. If something else already uses port 8000, pick another (`--port 8010`) and point the frontend's `VITE_API_URL` at it, and add the frontend's address to `CORS_ORIGINS`.

8. **Run tests and the linter** (the linter needs `pip install -r requirements-dev.txt`)

   ```bash
   pytest
   ruff check .
   ```

   Tests run against a throwaway SQLite file and roll back after every test; nothing touches the network (Google and OpenStreetMap are replaced by fakes). Besides the feature tests there are guards that fail when someone forgets something: every route's access level is listed in `tests/test_hardening.py`, `.env.example` must list every setting, and `alembic check` must find the models and migrations in agreement.

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
- **Do-not-contact** (`/api/v1/compliance/do-not-contact`, and `POST /businesses/{id}/do-not-contact`) — anyone can record "please stop contacting us" for a business, a phone number or an email; only an admin can lift it. Blocking a business also blocks its phones and emails, so if a later scrape finds the same shop as a new record with the same number, it's refused too. Blocked people are removed from every leads endpoint (a blocked business is "not found"), and refused during runs (counted as `blocked` in the run stats). Exports and the live sheet use the same filter.

## Export and the Google Sheet

- **CSV export** — `GET /api/v1/exports/leads.csv` (any signed-in user) takes the same filters and sorting as the leads list and returns one row per lead: contact details, WhatsApp chat link, status, notes, assignee, place, sources and dates. It opens correctly in Excel (UTF-8, so Urdu names survive), and text that could run as a formula is neutralised.
- **Live Google Sheet** (`/api/v1/sheets`, admin only) — a one-way mirror, app → sheet. Each sync rewrites the whole **Leads** worksheet from the database, so it is always exactly what the CSV would contain, and running it twice changes nothing. Edits made in the sheet are overwritten; sales work in the app. Share the sheet with the team as **view only**.
  - It signs in as a Google **service account**. Paste the key file's JSON on the Google Sheet screen (stored encrypted, never shown again) or set `GOOGLE_SERVICE_ACCOUNT_JSON`. The sheet must be shared with the service account's email as Editor.
  - `POST /sheets/sync` ("Sync now") runs in the background; poll `GET /sheets` until `is_syncing` is false. After a run finishes, or a lead is edited or put on do-not-contact, the sheet refreshes by itself after `SHEETS_AUTO_SYNC_DELAY_SECONDS` (a burst of edits shares one refresh; an unchanged sheet is not rewritten). This can be switched off on the screen.
  - It only touches the worksheet called "Leads" and refuses one that already holds someone else's data. Anyone on the do-not-contact list is never written.

## Insights

`GET /api/v1/insights/...` (any signed-in user) turns what runs have stored into market intelligence. Every number goes through the same do-not-contact filter as the leads list.

- `overview` — leads, how many have a phone / WhatsApp-capable number / email / website, new in 7 and 30 days, counts by status.
- `coverage?profile_id=` — a city × segment matrix (every target city appears, even with none).
- `gaps?profile_id=&threshold=` — target cities with fewer leads than the threshold, split into "never searched" and "searched, little found", with the segments still missing.
- `timeline` — new leads per day / week / month with a running total.
- `sources` — per source: leads found, leads only it found, with phone / WhatsApp / email / website, billable requests and estimated cost (per lead for paid ones), so you can judge whether a paid source earns its cost.
- `movers` — businesses seen recently whose review count grew most since the search before (each run records a rating / review-count snapshot per business it sees).

## Project Structure

```
app/
├── core/         # Cross-cutting concerns (security, exceptions, rate limiter, crypto)
│   ├── sheets/   # Google Sheets client + service-account sign-in (pure Python, no database)
│   └── scouting/ # The engine: sources, website enrichment, phone/name normalisation, de-duplication,
│                 #   classification. Pure Python: no database or web framework.
├── features/     # Feature modules (auth, users, profiles, geographies, sources, runs, businesses, compliance, exports, sheets, insights)
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

## Operating notes

Read these before putting it on a server.

- **Secrets.** `SECRET_KEY` must be at least 32 characters (the app refuses to start otherwise). Saved API keys and the Google service-account key are encrypted with `ENCRYPTION_KEY` (or a key derived from `SECRET_KEY`: rotating either means re-entering saved keys, and the screens say so). Never commit `.env`.
- **One process.** Runs execute on a background thread inside the server, and the Sheets sync lock and the automatic-refresh timer are per process. Run **one** server process (one uvicorn worker). Running several would start duplicate workers; moving to a real queue (Celery/RQ) is the step to take before scaling out.
- **Database.** SQLite is fine for one machine (WAL mode is on). It allows one writer at a time, so every request that changes data, and the background run, take the write lock up front and wait their turn (up to 15 s); reads never wait. Keep write transactions short and never hold one across a network call: the run worker is written that way, and `tests/test_concurrency.py` fails if that changes. Back it up by copying `market_scout.db` while the server is stopped, or with `sqlite3 market_scout.db ".backup copy.db"`. For PostgreSQL, see the note below.
- **Health check.** `GET /health` answers 200 only if the database does (503 otherwise), for a monitor or load balancer. `GET /` is a cheap "is it running".
- **Logs.** `LOG_LEVEL` controls the app's own logging (failed syncs, crashed runs, database conflicts). Errors shown to users are plain sentences; the technical detail goes to the log only.
- **HTTPS.** Put it behind a reverse proxy that terminates TLS when it leaves your machine; tokens travel in headers.
- **Being a good neighbour.** The free sources are shared public services: the app identifies itself (`SCOUT_CONTACT_EMAIL`), honours robots.txt when reading websites, spaces out OpenStreetMap requests and stays well below its limits. Keep it that way.
- **Outreach.** The app records where every lead came from and honours do-not-contact, but how your team contacts people (unsolicited messages, WhatsApp bulk-sending limits) is a business decision worth a second look.

## Troubleshooting

- **The frontend says "Network Error".** Wrong port or origin: check `VITE_API_URL` in the frontend and `CORS_ORIGINS` here. Another app (for example another project's backend) may be holding port 8000: `netstat -ano | findstr :8000`.
- **OpenStreetMap searches fail with "refused this app's identification (HTTP 406)".** Overpass turns away placeholder contact addresses. Set `SCOUT_CONTACT_EMAIL` to a real address or leave it blank.
- **A run's OpenStreetMap searches fail or are slow.** The public Overpass server throttles and sometimes times out. The run retries with backoff and keeps what it found; repeat the run later, or set `OVERPASS_URL` to another Overpass server.
- **"The service account can't open this spreadsheet".** Share the sheet with the service account's email (shown on the Google Sheet screen) as Editor. "Sheets API isn't switched on" means enabling it in that Google Cloud project.
- **A saved key "can no longer be read".** `SECRET_KEY` or `ENCRYPTION_KEY` changed since it was saved; enter it again.

## Notes

- **Error responses.** A database conflict the service layer didn't anticipate comes back as `409` (not a 500), and even a genuine `500` carries the CORS headers for allowed origins, so the browser shows the real error instead of an opaque "Network Error".

- The first migration was generated on SQLite. When moving to PostgreSQL, point `DATABASE_URL` at a fresh database and regenerate the initial migration (or review it) before deploying.

## Status

In development. Completed: foundation, auth, user management, profiles, locations, seed data, scouting engine, sources, runs, leads API, do-not-contact, CSV export, Google Sheet mirror, insights. Hardening done (lint, guard tests, concurrency, clean-install check). Not built on purpose: two-way sheet sync, sending messages, LLM classification, a job queue (see Operating notes).
