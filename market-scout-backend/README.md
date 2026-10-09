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

   Tests run against a throwaway SQLite file and roll back after every test; nothing touches the network (Google and OpenStreetMap are replaced by fakes). (Overture is tested against small files the tests build.) Besides the feature tests there are guards that fail when someone forgets something: every route's access level is listed in `tests/test_hardening.py`, `.env.example` must list every setting, and `alembic check` must find the models and migrations in agreement.

## Roles

- **admin** — everything, including managing users, profiles, locations, sources and runs, and lifting do-not-contact blocks.
- **sales** — works the leads: list/filter/search them, change status, notes and assignee, mark a business "do not contact". Can read profiles and locations. Can't see or start runs, change sources, or manage users.

## Profiles and locations

- A **profile** is an industry pack: segments (e.g. dealer, importer), search terms and scoring weights. Solar is the first; new industries are added through the API/UI with no code changes.
- Each search term has `text` (for text-search sources such as Google Places) and an optional `osm_filter` (for OpenStreetMap). Terms without an `osm_filter` are skipped by OpenStreetMap and Overture Maps (which reads the same filter, translated).
- **Locations** form a country → province → city hierarchy. A city's latitude, longitude and `radius_km` define the area that is searched (the square that contains that radius, or an explicit `bbox`); the seeded values are approximations you can adjust.

## Data sources and runs

A **run** searches a profile's terms in chosen cities using chosen sources, then reads each found business's own website for more contact details. Everything is done by a single background thread inside the server (started on boot, `RUN_WORKER_ENABLED`); progress is polled from `GET /api/v1/runs/{id}`.

- **Sources** (`/api/v1/sources`, admin only) are switched on/off, and given an API key, from the UI — no code change.
  - **OpenStreetMap** — free, no key. Phone numbers are patchy in Pakistan, and the public Overpass server throttles, so requests are spaced out and retried with backoff.
  - **Overture Maps** — free, no key, no network at search time. It searches a local copy of Pakistan's places (about 217,000, from Overture's open dataset: mostly Meta's and Microsoft's place data, CDLA Permissive 2.0, attribution to Overture Maps Foundation), which is far larger and phone-richer than OpenStreetMap's. Make the copy once, and again whenever you want a newer release (they come monthly):
    ```bash
    pip install -r requirements-dev.txt        # DuckDB, needed for this step only
    python -m scripts.download_overture        # a few minutes, ~50 MB at ./data/overture.sqlite (OVERTURE_DB_PATH)
    ```
    Until the file exists the source shows "Needs a download" on the Sources screen and can't be picked for a run. A search term is translated from its OSM filter: `shop=electrical` means "electronics store, electrical supplier, solar installer..." in Overture's categories, and `name~solar` stays a name pattern (`TAG_CATEGORIES` in `app/core/scouting/sources/overture.py` lists the equivalents). A group whose tags have no Overture equivalent finds nothing rather than too much. Places Overture is unsure exist (`OVERTURE_MIN_CONFIDENCE`) and permanently closed ones are left out.
  - **Foursquare Places** — free, no key, no network at search time, kept on this computer like Overture. It searches Pakistan's places from [Foursquare Open Source Places](https://docs.foursquare.com/data-products/docs/fsq-places-open-source) (Apache 2.0; keep the notice "Copyright 2024 Foursquare Labs, Inc. All rights reserved."). Foursquare no longer publishes the files in a public bucket: register at the [Places Portal](https://places.foursquare.com/), generate an access token, and export or download the `places` table as Parquet files (the portal shows the connection snippet for your tool). Then build the local copy, again whenever you want a newer release:
    ```bash
    pip install -r requirements-dev.txt
    python -m scripts.download_foursquare --parquet "path/to/places/*.parquet" --release 2026-09-30   # ~/data/foursquare.sqlite (FOURSQUARE_DB_PATH)
    ```
    The script keeps rows whose `country` is `PK` inside Pakistan's bounding box, marks places with a `date_closed` as closed, and refuses to replace a good copy with an empty one. Until the file exists the source shows "Needs a download" on the Sources screen. Foursquare labels categories as text such as `Retail > Electronics Store`, so a search term's OSM filter is translated to keywords matched anywhere in a label, ignoring case (`TAG_CATEGORIES` in `app/core/scouting/sources/foursquare.py`). **Those keywords are a first guess from the documented schema and were not checked against the real files**: after your first download, search a city and look at what comes back (`sqlite3 data/foursquare.sqlite "SELECT categories, COUNT(*) FROM places GROUP BY categories ORDER BY 2 DESC LIMIT 50"` lists the labels), then adjust the keywords. Foursquare's open data has no confidence score, so every place is stored with confidence 1.
  - **Google Places API** — needs a key (saved encrypted from the UI, or `GOOGLE_PLACES_API_KEY`). Billed per request, so a run can carry a request cap and `POST /runs/estimate` previews the number of searches and cost first.
  - **HERE Places** and **TomTom Places** — hosted place searches like Google Places: they need a key (saved encrypted from the Sources screen, or `HERE_API_KEY` / `TOMTOM_API_KEY`), start switched off, and are billed per request after each provider's free allowance. HERE answers a search in one request (up to 100 places, no paging); TomTom pages through up to three requests of 100. Set `HERE_COST_PER_REQUEST_USD` and `TOMTOM_COST_PER_REQUEST_USD` to your plan's price once you pass the free allowance: both default to 0, so the run estimate shows $0.00 until you do. The request cap on a run counts every paid source together. **These two were written from the providers' published API documentation and tested against fake responses only, never against the live services**: the first real search is the real test (use the Test connection button, then a small run with a request cap).
    **Storage terms matter for a lead database.** HERE's platform terms (section 6.3e) limit keeping its results outside the HERE platform to 30 days unless they are used only for internal testing, evaluation or audit records; TomTom's Maps API terms restrict storing and caching search results; Google's terms also limit how long Places data may be stored. Each paid source shows a "Storage terms" note on the Sources screen. Read the current terms for the plan you use before keeping leads found this way long term, and ask the provider in writing if in doubt. These sources send the key in the URL (neither accepts it any other way), so the app turns off request-URL logging for its HTTP library; keep that in mind if you add your own logging.
  - **Website enrichment** — reads each business's own site (robots.txt honoured, public addresses only) for email, WhatsApp and social pages.
- Results from all sources are merged into one business (same website, same phone with a similar name, or same spot with a near-identical name). Every phone/email records which source reported it, and each source's raw answer is kept.
- Each run stores per-source quality (found / new / merged / with phone / website / email) so you can see whether a paid source is worth it.
- A search that finished within `RUN_TASK_CACHE_DAYS` is skipped by later runs unless `refresh` is set. A run interrupted by a restart can be resumed.

### Adding a source

A source is one module in `app/core/scouting/sources/` that describes itself, so nothing else has to change:

1. Write the class with `key`, `search(query, max_requests)` and `test_connection()` (the `Source` protocol in `base.py`). For a dataset kept on this computer, subclass `LocalPlaceSource` in `local_places.py` instead: give it a `label`, a `TAG_CATEGORIES` table (OSM tag to category names or keywords) and a `to_business` method, and the filter translation, SQL and error handling come with it. Set `exact_categories = False` when categories are free text matched by keyword.
2. Add `build(context)` (it receives the saved or environment API key, the user agent and `settings`) and an `INFO = SourceInfo(...)` with its name, description, whether it needs a key or is paid, the settings name of its fallback key (`api_key_setting`), its `dataset` (file path and download command) and `supports_filter` (which search terms it can answer). A paid source also declares `max_requests_per_search`, `cost_per_request_setting` (the name of the setting holding its price), `seconds_per_search` and a `terms_note` about storing its results; run estimates, caps, run cost and Insights read those instead of assuming Google.
3. Add `INFO` to `CATALOG` in `registry.py`.

The Sources screen, run planning, validation, the connection test and Insights read everything from `SourceInfo`. New settings go in `app/core/config.py` and `.env.example`; the frontend only needs a display name in `SOURCE_LABELS`.

## Imports (lists you already have)

`/api/v1/imports` (admin only) brings a spreadsheet of businesses (certified installers, chamber directories, customs records) into the leads through exactly the same matching, scoring and do-not-contact checks as a search run.

- **Flow:** `POST /imports/preview` reads a CSV or Excel file and guesses which column is which (nothing is stored). `POST /imports/` takes the file plus the chosen columns and options, cleans the rows straight away (so mistakes are reported at once), then a background thread stores them 100 at a time. Poll `GET /imports/{id}` for progress; `POST /imports/{id}/cancel` stops it between batches and keeps what was stored.
- **What a row needs:** a name, and (unless you untick "skip rows with no contact details") a phone, email or website. Phones are normalised (a mobile typed into Excel as a number, with its leading zero lost, is recovered); an email cell may hold several; a city comes from a City column, or from the end of the address, or from a default city you choose.
- **Provenance:** every lead records `import:<list name>` as where it was found, and keeps the original row. Importing a newer version of the same list under the same name recognises the same companies (by name + number, not by row position) instead of duplicating them. Imported lists appear in Insights next to the search sources.
- **Duplicate matching:** a phone number that appears on three or more *different* companies in one file (a consultant's or agent's mobile, common in government lists) is kept as a contact on each but never used to decide two companies are the same one. A number on the do-not-contact list still blocks every company that lists it.
- **Government installer lists (AEDB, now PPIB):** the Private Power and Infrastructure Board publishes three PDF tables of certified installers on [ppib.gov.pk](https://www.ppib.gov.pk/): **C-1** (large projects, 500 kW and above), **C-2** (up to 500 kW) and **C-3** (up to 250 kW). `python -m scripts.convert_aedb_pdf "List of Certified Installer C-1 (25-10-2024).pdf" c1.csv` (needs `pip install -r requirements-dev.txt`) turns one into a clean CSV with the city and phones/emails split out, ready for the Imports screen. Converted copies of the October 2024 lists are in `sample_data/` (C-1: 210 companies, C-2: 128, C-3: 273). They carry each certificate's "Valid until" date and many have lapsed since: check current status before relying on one. Import each under its own list name (e.g. "PPIB certified installers C-1"); a newer version under the same name updates that list.
- **Lists that only name businesses (chamber directories, customs records, dealer lists):** tick "Look up missing phones in Overture Maps" (needs the Overture data, see Data sources). For each row with no phone, the app looks for a business in Overture with **exactly the same name** (legal suffixes and punctuation ignored) **inside the row's city** and takes its phone, email and website only if **exactly one** such business exists. "Malik Traders" twice in Lahore is left alone, because ringing the wrong company is worse than having no number. The phone is credited to Overture and the lead lists both sources. On the Lahore members of a public chamber directory about 6% of rows matched (15 sampled by eye were all the right business); lists of distinctive company names should do better. A row with no phone or website is told apart from another of the same name by its city and address, so two "Kashif Traders" in different cities stay two leads.
- **Sources that can't be automated, and why:** the **ENF Solar** directory refuses automated access (HTTP 403) and has no export, so it is not scraped; save or copy what you are entitled to use into a spreadsheet and import that. The **Lahore Chamber** directory is public but lists only company name, member contact and address (phones and emails are hidden by the chamber), which is what the lookup above is for. **Customs shipment data** is not public in Pakistan; commercial providers (Volza and others) sell it, and their CSV/Excel exports import like any list.
- **Limits and settings:** `IMPORT_MAX_MB` (10), `IMPORT_MAX_ROWS` (50,000), `IMPORTS_DIR` (cleaned rows wait there while importing), `IMPORT_BATCH_PAUSE_SECONDS` (a short rest between batches: SQLite has one writer at a time, and without it a big import would starve every other save in the app).

## Leads and do-not-contact

- **Leads** (`/api/v1/businesses`) — the businesses runs have found. `GET /` filters by profile, segment, location (a city, province or the country), phone / WhatsApp-capable / email / website, status, assignee, source, minimum score, and a text search over name, address, phone (typed any way: `0300…`, `+92 300…`) and email. It sorts by score (default when a profile is chosen), newest, last seen or name. `PATCH /{id}` edits only the sales fields (status, notes, assignee); `POST /bulk-update` changes status/assignee for up to 500 at once.
- **Score** is the sum of a profile's weights for the signals a lead has (phone, WhatsApp-capable mobile, website, email, reviews, name matches its segment).
- **Do-not-contact** (`/api/v1/compliance/do-not-contact`, and `POST /businesses/{id}/do-not-contact`) — anyone can record "please stop contacting us" for a business, a phone number or an email; only an admin can lift it. Blocking a business also blocks its phones and emails, so if a later scrape finds the same shop as a new record with the same number, it's refused too. Blocked people are removed from every leads endpoint (a blocked business is "not found"), and refused during runs (counted as `blocked` in the run stats). Exports and the live sheet use the same filter.

## Export and the Google Sheet

- **CSV export** — `GET /api/v1/exports/leads.csv` (any signed-in user) takes the same filters and sorting as the leads list and returns one row per lead: contact details, WhatsApp chat link, status, notes, assignee, place, sources and dates. It opens correctly in Excel (UTF-8, so Urdu names survive), and text that could run as a formula is neutralised. `GET /api/v1/exports/leads.xlsx` returns the same rows and columns as an Excel workbook (one "Leads" sheet, bold frozen header row); text is stored as text, so a name like `=SUM(...)` can't run as a formula. The Leads page's **Export** button offers both formats.
- **Live Google Sheet** (`/api/v1/sheets`, admin only) — a one-way mirror, app → sheet. Each sync rewrites the whole **Leads** worksheet from the database, so it is always exactly what the CSV would contain, and running it twice changes nothing. Edits made in the sheet are overwritten; sales work in the app. Share the sheet with the team as **view only**.
  - It signs in as a Google **service account**. Paste the key file's JSON on the Google Sheet screen (stored encrypted, never shown again) or set `GOOGLE_SERVICE_ACCOUNT_JSON`. The sheet must be shared with the service account's email as Editor.
  - `POST /sheets/sync` ("Sync now") runs in the background; poll `GET /sheets` until `is_syncing` is false. After a run finishes, or a lead is edited or put on do-not-contact, the sheet refreshes by itself after `SHEETS_AUTO_SYNC_DELAY_SECONDS` (a burst of edits shares one refresh; an unchanged sheet is not rewritten). This can be switched off on the screen.
  - It only touches the worksheet called "Leads" and refuses one that already holds someone else's data. Anyone on the do-not-contact list is never written.

## Pipeline: history, follow-ups and outcomes

`/api/v1/pipeline` (any signed-in user) turns a lead's single status into a record of what happened and what comes next.

- **Stages.** A lead moves through `new`, `contacted`, `interested`, `meeting`, `quoted` and ends as `customer` (won) or `not_interested` (lost).
- **History.** Every status change and every change of owner is logged automatically with who made it and when, including bulk changes (one entry per lead that actually changed). People add their own entries (`note`, `call`, `whatsapp`, `email`, `meeting`) with `POST /pipeline/leads/{id}/activities`; `GET` lists them newest first. A person cannot log a system entry by hand.
- **Outcomes.** Moving a lead to `customer` or `not_interested` can carry an `outcome` in the same `PATCH /businesses/{id}`: a deal `value`, `product` and `note` for a customer, a `loss_reason` (`price`, `competitor`, `no_need`, `no_response`, `bad_contact_data`, `wrong_business`, `other`) and `note` for a lost lead. Details that do not fit the status are refused before anything changes. Sending only `outcome` corrects the details of a lead that is already closed and is logged as "deal details updated". Moving a lead back to an open stage removes its outcome and keeps the history. A bulk change to `customer` or `not_interested` closes each lead with no details. `DEAL_CURRENCY` sets the currency the screens show; amounts are stored as plain numbers in that one currency.
- **Follow-ups.** `POST /pipeline/leads/{id}/tasks` sets a title and a due date (assigned to the creator unless you say otherwise or pass `null`). `GET /pipeline/tasks` lists them by `scope` (`open`, `overdue`, `today`, `upcoming`, `done`), optionally only `mine` or for one `business_id`; `GET /pipeline/tasks/summary` gives the overdue, due-today and open counts the sidebar badge uses. "Today" is whatever date the caller sends as `today` (the browser sends its own local date); it defaults to today in UTC. Completing a task is logged on the lead. There are no emails or push messages: reminders are the Tasks screen and the badge.
- **Do-not-contact** applies everywhere here: a blocked lead's history, tasks and outcome are not found, and are left out of the reports.
- **Reports** (`/insights/pipeline`, `/insights/conversion?group_by=source|segment|city`) are described under Insights.

## Insights

`GET /api/v1/insights/...` (any signed-in user) turns what runs have stored into market intelligence. Every number goes through the same do-not-contact filter as the leads list.

- `overview` — leads, how many have a phone / WhatsApp-capable number / email / website, new in 7 and 30 days, counts by status.
- `coverage?profile_id=` — a city × segment matrix (every target city appears, even with none).
- `gaps?profile_id=&threshold=` — target cities with fewer leads than the threshold, split into "never searched" and "searched, little found", with the segments still missing.
- `timeline` — new leads per day / week / month with a running total.
- `sources` — per source: leads found, leads only it found, with phone / WhatsApp / email / website, billable requests and estimated cost (per lead for paid ones), so you can judge whether a paid source earns its cost.
- `pipeline` — how far leads got: for each stage how many are there now and how many have reached it or gone beyond (a lead that closed keeps credit for the stages it passed), plus won, lost, still open, win rate (won of won + lost), revenue, average deal and the reasons leads were lost. "Reached" uses the recorded status history; a lead that was already `not_interested` before history was kept counts as lost but is not credited with any stage, and one already a `customer` counts as having passed every stage.
- `conversion?group_by=` — the same stage counts, wins, losses, win rate and revenue per `source` (a lead found by two sources counts under both), `segment` (needs `profile_id`) or `city`.
- `movers` — businesses seen recently whose review count grew most since the search before (each run records a rating / review-count snapshot per business it sees).

## Project Structure

```
app/
├── core/            # Code shared by 2+ features
│   ├── config.py       # App configuration/settings
│   ├── constants.py    # Values used by more than one feature
│   ├── database.py     # Engine/session setup (SQLite pragmas applied here)
│   ├── dependencies.py # Shared FastAPI dependencies (get_db)
│   ├── security.py, exceptions.py, limiter.py, crypto.py, utils.py
│   ├── importing/      # Reading CSV/Excel files, mapping columns, looking up contacts (pure Python)
│   ├── sheets/         # Google Sheets client + service-account sign-in (pure Python, no database)
│   └── scouting/       # The engine: sources (one module each), place_store (the local places files), website
│                       #   enrichment, phone/name normalisation, de-duplication, classification. Pure Python.
├── features/        # One folder per feature (auth, users, profiles, geographies, sources, runs, businesses,
│                    #   compliance, exports, sheets, insights, imports, pipeline), each with router/service/schemas/models
├── models.py        # Imports every ORM model (add new ones here)
└── main.py          # Application entry point

alembic/          # Database migrations
scripts/          # Utility/maintenance scripts (create_admin, seed + seed_data/, download_overture, download_foursquare, convert_aedb_pdf)
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
- **Overture Maps or Foursquare Places says "Needs a download".** Run `python -m scripts.download_overture` or `python -m scripts.download_foursquare --parquet ...` in the backend folder (see above). "Data file can't be read" or "from an older version of the app" means the same: download it again.
- **A run's OpenStreetMap searches fail or are slow.** The public Overpass server throttles and sometimes times out. The run retries with backoff and keeps what it found; repeat the run later, or set `OVERPASS_URL` to another Overpass server.
- **"The service account can't open this spreadsheet".** Share the sheet with the service account's email (shown on the Google Sheet screen) as Editor. "Sheets API isn't switched on" means enabling it in that Google Cloud project.
- **A saved key "can no longer be read".** `SECRET_KEY` or `ENCRYPTION_KEY` changed since it was saved; enter it again.

## Notes

- **Error responses.** A database conflict the service layer didn't anticipate comes back as `409` (not a 500), and even a genuine `500` carries the CORS headers for allowed origins, so the browser shows the real error instead of an opaque "Network Error".

- The first migration was generated on SQLite. When moving to PostgreSQL, point `DATABASE_URL` at a fresh database and regenerate the initial migration (or review it) before deploying.

## Status

In development. Completed: foundation, auth, user management, profiles, locations, seed data, scouting engine, sources (OpenStreetMap, Overture Maps, Foursquare Places, Google Places, HERE, TomTom), runs, leads API, do-not-contact, CSV export, Google Sheet mirror, insights. Imports (CSV/Excel lists) and the AEDB installer list added. Hardening done (lint, guard tests, concurrency, clean-install check). Lead history, follow-ups, deal outcomes and conversion reports added. Not built on purpose: two-way sheet sync, sending messages, LLM classification, a job queue (see Operating notes).
