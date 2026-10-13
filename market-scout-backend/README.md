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

A **run** searches a profile's terms in chosen cities using chosen sources, then reads each found business's own website for more contact details. Runs are background jobs (see *Background jobs and repeating searches*; switched off by `RUN_WORKER_ENABLED=false`); progress is polled from `GET /api/v1/runs/{id}`.

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
- A search that finished within `RUN_TASK_CACHE_DAYS` is skipped by later runs unless `refresh` is set. A run interrupted by a restart or crash carries on by itself; one that keeps failing can be resumed by hand.

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
- **Government installer lists (AEDB, now PPIB):** the Private Power and Infrastructure Board publishes three PDF tables of certified installers on [ppib.gov.pk](https://www.ppib.gov.pk/): **C-1** (large projects, 500 kW and above), **C-2** (up to 500 kW) and **C-3** (up to 250 kW). `python -m scripts.convert_aedb_pdf "List of Certified Installer C-1 (25-10-2024).pdf" c1.csv` (needs `pip install -r requirements-dev.txt`) turns one into a clean CSV with the city and phones/emails split out, ready for the Imports screen. `sample_data/sample-installers.csv` holds 24 fictional companies in the same format, so you can try the Imports screen without any real contact details. The real lists are public on the PPIB site: download them yourself and check each certificate's "Valid until" date, since many have lapsed. Import each under its own list name (e.g. "PPIB certified installers C-1"); a newer version under the same name updates that list.
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

## AI assistant

`/api/v1/ai` adds a Claude-powered second opinion on a lead. It is **advice only**: results sit beside a lead and never change its segment or score unless someone applies the suggestion.

- **What it produces** (per lead and profile): a one-line summary of what the business does, a suggested segment (or none), and a 0-100 *fit* score with a reason, measured against the profile's **ideal customer** text (`ideal_customer` on the profile; edit it in the profile editor). The score is `null` when the website has too little text to judge. Each result also records a confidence (`low`/`medium`/`high`), the model used, how many pages were read and whether the text was cut.
- **How a lead is read.** The website's home page and an "About" page (when linked) are fetched with the same safeguards as contact enrichment (public addresses only, robots.txt honoured) and reduced to visible text, at most `PAGE_TEXT_MAX_CHARS` (8,000) in `app/features/ai/service.py`. A lead with no website, a site that blocks automated readers, or a page with under 200 characters of text is skipped **without calling the API** and the reason is stored.
- **What is sent to Anthropic.** The business name, address, city, listing categories and website address, plus the website text, plus the profile's segment list and ideal-customer text. Phone numbers and emails from the lead record are not sent, though they can appear in a website's own text. The website text is wrapped in a data block, the prompt tells the model to treat it as data and never as instructions, and a closing tag inside the text is escaped so a page can't end the block early.
- **Calling Claude.** Through the official `anthropic` SDK (`app/core/ai/analyzer.py`): one `messages.create` per lead with a JSON-schema `output_config.format`, `max_tokens` 2,000 and, on models that support it, `effort: low` (a rating needs little deliberation). A refusal (`stop_reason: refusal`) is recorded as "declined"; the tokens it used are still counted. **Server-side fallbacks for refusals are not enabled**: a declined lead is just marked declined. `ANTHROPIC_API_KEY` may be set on the server as a fallback to a key saved from the AI assistant screen (stored encrypted, like the other keys).
- **Models and prices.** `claude-opus-5-5` (default), `claude-sonnet-5-5` and `claude-haiku-4-5`, chosen on the AI assistant screen; prices per million tokens live in `app/core/ai/models.py` and were copied from Anthropic's published list on 2026-09-25. **Check them against your Anthropic bill**: cost is computed from the token counts the API reports. The default is the most capable and the most expensive; Sonnet or Haiku is usually enough for a rating.
- **Spending is capped.** `AI_MONTHLY_BUDGET_USD` (default 5, editable on the screen) is the calendar-month ceiling. Every call is logged to `ai_usage` with its tokens and cost. Before each lead the batch checks that this month's spend plus that lead's *worst-case* cost (full-size prompt and the whole `max_tokens`) still fits, and stops with a message if not. `POST /ai/estimate` shows the same worst case up front; real costs are usually a fraction of it.
- **Batches.** `POST /ai/analyze` (any signed-in user) queues up to 100 leads and returns a batch; a background job processes it one lead at a time. `GET /ai/batches/{id}` reports progress, counts and the first few problems. If the server stops mid-batch it carries on from the next lead when it is back (see *Background jobs and repeating searches*). Leads already analysed for that profile are skipped unless `refresh` is set, and a failed re-analysis never overwrites an earlier good result. A key that is rejected, or an account out of credit, stops the whole batch.
- **Using results.** `GET /businesses` returns `ai_fit` per lead and accepts `min_ai_fit` and `sort=ai_fit`; a lead's detail returns an `ai` object. `POST /ai/leads/{id}/apply-segment` moves the lead to the suggested segment and logs it on the lead's timeline.
- **Admin.** `GET`/`PUT /ai/settings` and `POST /ai/settings/test` are admin-only (the test uses Anthropic's token-counting call, which makes no model request). `GET /ai/status` tells every user whether the assistant is ready and, if not, why.

## Background jobs and repeating searches

Runs, imports and AI batches are **jobs** saved in the database (the `jobs` table), not tasks held in memory. Nothing queued is lost when the server stops.

- **Starting work.** Saving a run (or import, or AI batch) and its job happen in one transaction, so there is never a run with no job to carry it out. Three lanes inside the server (runs, imports, AI) each take the oldest waiting job of their kind, one at a time. A lane takes a job by an atomic update that gives it a 30-second **lease**, which a heartbeat renews every 10 seconds while it works.
- **After a crash or restart.** If a job's lease lapses (the process was killed, the machine lost power), a maintenance thread puts it back in the queue and the work carries on where it stopped: a run continues with the searches not yet done (and keeps its counts so far), an import with the rows not yet stored, an AI batch with the next lead. Expect it to start again roughly 30-45 seconds after the server is back. Each job gets up to 3 attempts; after that it is marked failed with a message, and a failed run can still be resumed by hand. A job that stops with an unexpected error is marked failed and is **not** retried.
- **Stopping the server on purpose** hands running jobs back at once, so the next start picks them up without waiting for the lease.
- **Self-healing.** On start and every 10 seconds the server gives a job to anything that is waiting without one (for example work queued before this feature existed) and recovers work stuck in "running" with no job. A lane that has died is started again, and a database error while looking for work is logged and retried after 5 seconds instead of killing the lane.
- **Seeing it.** `GET /api/v1/jobs/status` (admin) lists how many jobs are waiting and running per kind, how long the oldest has waited and the latest failures. `GET /health` now also reports `workers` (`running`, `disabled` when `RUN_WORKER_ENABLED=false`, or `stopped`, which makes the health check answer 503). Finished job records are deleted after 30 days.
- **More than one process.** Jobs and schedules are claimed with guarded updates, so two processes should not run the same job, but this is not tested, and the Sheets sync lock and refresh timer are still per process. Keep to one server process.

`/api/v1/schedules` (admin only) holds **repeating searches**: a profile, cities, sources and options like a run, plus how often (`daily`, `weekly` or `monthly`).

- **When it runs.** The first run comes one cycle after the schedule is saved (use `POST /schedules/{id}/run-now` to start one sooner without moving the cadence). A ticker checks every 15 seconds. Each run is created exactly like a manual run, with `refresh` on so the searches really repeat, and carries the schedule's id and name. Leads that are already known are merged, so a run adds only what is new.
- **Checked when saved.** The same checks as a run (profile on, cities and sources exist and are switched on, search count under `RUN_MAX_TASKS`), and a schedule that uses a paid source **must** set a cap on billable requests, since the cost repeats.
- **Careful by default.** A schedule that was overdue (the server was off) runs once, not once per missed cycle. If its last run is still going, that cycle is skipped. If the last run failed, or a run cannot be started, it counts as a failure; three in a row switch the schedule off with the reason in `last_error`. A completed run clears the count. Switching a schedule back on clears the failures and waits one cycle.
- **Editing.** `PUT /schedules/{id}` can change the name, frequency, on/off and the search itself (re-checked). The Repeating searches screen switches schedules on and off, runs them now and deletes them; to change what one searches, use the API or save a new one. Deleting a schedule keeps the runs it made.
- **Not built.** Choosing a time of day or weekday (a cycle counts from when the schedule was saved), and re-reading the websites of leads that already exist.

## Alerts

`/api/v1/alerts` tells people about things worth a look that turned up when a run finished. They are in-app only: a list and an unread count, nothing is emailed or messaged.

- **When they are worked out.** At the end of every run (manual or repeating), whatever its outcome, once the run's results are stored. A failure while working them out is logged and never affects the run. Only leads the run touched are considered, and leads on the do-not-contact list never produce or show an alert.
- **Three kinds.**
  - `new_lead`: the lead was first seen during this run and scores at least `new_lead_min_score` (default 70) for the run's profile. The AI fit is not used, because it only exists after someone asks for it.
  - `growing`: the lead's review count rose by at least `growing_min_new_reviews` (default 10) **and** by at least `growing_min_percent` (default 20%) since its previous snapshot. It needs a source that reports reviews (Google, HERE, TomTom, Foursquare, Overture); OpenStreetMap has none, so it never triggers this.
  - `reachable`: a lead that was known before the run gained a phone, email or WhatsApp contact during it (including from reading its website) and had none of those before. A website or social page alone does not count.
- **No repeats.** An alert is unique per kind, lead and key: `new_lead` and `reachable` once per lead ever, `growing` once per review count reached. Running the same evaluation again adds nothing.
- **Not a flood.** `max_per_run` (default 50) keeps only the best of a run (highest score or biggest review jump). Alerts older than 90 days are deleted.
- **Who sees them.** An alert about a lead that is assigned goes to that person; an unassigned lead's alert goes to everyone who signs in. Alerts are not moved if the lead is assigned later. Read state is per person, so one person reading an alert does not clear it for anyone else.
- **Endpoints.** `GET /alerts` (filters `unread_only`, `kind`; returns the person's unread count too), `GET /alerts/summary` (just the unread count, used by the sidebar badge), `POST /alerts/mark-read` (`ids` or `all`). `GET`/`PUT /alerts/settings` are admin-only and apply to every profile from the next run.

## Integrations

Three ways to connect other software, all admin-managed.

**API keys** (`/api/v1/api-keys`, admin; `DELETE` revokes). A key is `ms_` plus 43 random characters. It is shown once when created; only its SHA-256 hash is stored, so a lost key cannot be recovered, only replaced. A key is read-only unless an admin ticks `can_write`.

**Public API** (`/api/v1/public`, any valid key). Send `Authorization: Bearer <key>` or `X-API-Key: <key>`. A key works only here: a login token is refused on these routes and a key is refused everywhere else, so a leaked key can never manage users, settings or other keys. Each key is limited to 120 requests a minute for reads and 60 for writes (`429` after that).
- `GET /me`, `GET /leads` (same filters, sorting and paging as the Leads page), `GET /leads/{id}`, `GET /leads/{id}/activities`.
- Write keys only: `POST /leads` adds a business (needs a phone, email or website; an optional `city_id`, `profile_id` and `segment_slug`; it is stored with source `api`, merged into an existing lead if it matches, and refused with `409` if it or a contact is on the do-not-contact list), `PATCH /leads/{id}` (status, notes, contact person, deal outcome; never assignment) and `POST /leads/{id}/activities` (a note, call, meeting, WhatsApp or email). Changes made with a key show on the lead's history with no person's name.
- Do-not-contact leads are invisible here, as everywhere.
- Using a key records `last_used_at`, refreshed at most once a minute to avoid a database write on every request.

**Webhooks** (`/api/v1/webhooks`, admin). The app calls an address you give it when something happens.
- **Events**: `lead.created` (a run, import or API call stored a new business), `lead.status_changed` (with `from_status`, `to_status` and, when the lead became a customer or not interested, the deal `outcome` with value, product and loss reason), `alert.raised` (the alert and the lead) and `message.sent` (a confirmed outreach message). The payload carries a small snapshot of the lead (id, name, city, status, score, website, phones, emails); fetch the lead through the public API for more. A lead is announced when it is created, so contacts a later website read finds are not in that snapshot.
- **Delivery**: a JSON `POST` with `X-MarketScout-Event`, `X-MarketScout-Delivery` (the delivery id, unchanged across tries) and `X-MarketScout-Signature: t=<unix seconds>,v1=<hex>`, where `v1` is HMAC-SHA256 of `"<t>." + raw body` with the webhook's signing secret. The secret is shown once when the webhook is made (or replaced with `rotate-secret`) and stored encrypted. Redirects are not followed and the answer must arrive within 10 seconds.
- **Retries**: any answer other than 2xx, or no answer, is tried again after 30 s, 2 min, 10 min and 1 h, five tries in all. Delivery is at least once (a server restart can send a call twice), so receivers should ignore a delivery id they have seen. Events are not guaranteed to arrive in order. After 15 failed tries in a row the webhook switches itself off and says so; switching it back on clears the count. A failed delivery can be sent again by hand. Deliveries are kept 30 days.
- **Jobs**: each delivery is a `webhook` job in the same job table as runs, so retries survive restarts and show in `GET /jobs/status`.
- **Address rules**: `https://` only, no username or password in the address, and the host must resolve to a public address, checked when the webhook is saved and again before every call. `WEBHOOKS_ALLOW_PRIVATE_URLS=true` lifts the https and public-address rules for testing against a program on your own machine or network; leave it off on a server reachable from the internet.
- **Test**: `POST /{id}/test` queues a `ping` event even for a switched-off webhook; it gets one try and does not count towards the failure limit.

**CRM files** (`GET /api/v1/exports/crm.csv?layout=hubspot|zoho|generic`, any user, same filters as `leads.csv`). One row per lead, company-first because the leads are businesses: `hubspot` uses HubSpot's company property names (the importer maps columns by header, and the Market Scout extras can be skipped or created as custom properties), `zoho` uses Zoho CRM's Leads fields with the required Last Name always filled (the contact person's last word, or the business name when there is none) and `generic` has plain columns plus the deal outcome, value, product, loss reason and close date. Country is always Pakistan, as the app searches there. Statuses map to each CRM's stage names as a guess: HubSpot's Lifecycle Stage (Lead, Sales Qualified Lead, Opportunity, Customer, Other) and Zoho's Lead Status; the real status is always in a `Market Scout status` column. Review the mapping in the CRM's import screen.

## Outreach

`/api/v1/outreach` helps a person message a lead without the app ever sending anything itself.

- **Templates** (`GET/POST /templates`, `PATCH/DELETE /templates/{id}`): shared by the whole team. Everyone can list them (optionally narrowed with `channel`, which also returns `any` templates); only admins create, change or delete. A template is for `whatsapp`, `email` or `any`; only email-capable templates keep a subject. Names are unique ignoring case.
- **Placeholders**: `{business_name}`, `{city}` and `{contact_name}`, listed by `GET /config`. A lead with no city says "your city" and one with no saved contact person says "there". Any other `{word}` is refused when saving a template or preparing a message, so a typo never goes out. The contact person is a plain field on the lead (`contact_name`, edited with `PATCH /businesses/{id}`); nothing fills it in automatically.
- **Preview** (`POST /preview`): fills a template, or text written by hand, for one lead without saving anything. The Copy button uses it too, so copying leaves no trace.
- **Prepare** (`POST /messages`): the person picks the lead's contact, the channel and the final text. The server checks that the contact belongs to the lead and suits the channel (a phone or WhatsApp number for WhatsApp; an email address for email, never one a contact check found cannot receive mail), fills the placeholders, and returns a `wa.me` chat link or a `mailto:` link with the text encoded in it. It records the message as `opened`. **Nothing is logged on the lead and no status changes at this point**, and the reply says if someone already messaged this lead in the last 14 days.
- **Confirm** (`POST /messages/{id}/decision {sent}`): the person says whether they really sent it, once. `sent` adds a WhatsApp or Email entry (with the template name, subject and text) to the lead's history and moves a lead still marked *new* to *contacted* (a lead further along is never moved back). `not_sent` keeps the row in the log and changes nothing else. Only the person who wrote the message, or an admin, can confirm it. A message nobody confirms stays `opened`.
- **Send log** (`GET /messages`): newest first, filterable by lead, by status and to your own messages. A lead on the do-not-contact list cannot be messaged and drops out of the log.
- **Merging and deleting**: merging two leads moves the send log and the contact person onto the lead you keep. Deleting a template keeps every message already logged, with the template's name.
- **Not built, on purpose**: bulk sending, sending through WhatsApp or an email service, and email sequences with unsubscribe. WhatsApp's rules do not allow unsolicited bulk messages, and those pieces need an email service to be chosen first.

## Data quality

`/api/v1/quality` keeps the lead list honest. It has three parts.

**Contact checks** (`POST /quality/checks`, any signed-in user; follow it with `GET /quality/tasks/{id}`). A background job looks at up to 500 leads you choose:
- **Email:** the address's domain is looked up in DNS (`dnspython`, 5-second limit). A domain with mail servers is `ok`; one that does not exist, has no mail server, or publishes a null MX is `bad`; a lookup that cannot finish leaves the result unknown and is tried again next time. **No email is ever sent**, and no mail server is contacted, so this says a domain can receive mail, not that the mailbox exists.
- **Website:** one plain request to the home page (public addresses only, like website reading, but without robots.txt since it is a single page load). It is `ok` if it answers (including 401/403/429, which mean it is there but turns bots away) and `dead` if the domain is missing, the connection fails, it loops, or it returns an error status. A timeout leaves it unknown.
- **Phones:** a number listed for 3 or more businesses is flagged `warning` (likely a switchboard or directory). No telephone number is called.
- **Effect:** a `bad` email and a `dead` website stop counting towards the lead's score (the lead is rescored at once); results are kept 30 days and not repeated unless `refresh` is set. The lead detail shows each contact's `check_status`, `check_note` and `checked_at`, and `website_status`.
- **Automatic checks:** `PUT /quality/settings` (admin) can switch on `check_after_runs`, which queues a check for the leads each run touched (at most `max_checks_per_run`, default 200). It is off by default.

**Duplicate review** (admin). The automatic merge only joins businesses that clearly match (same website, same phone with a similar name, or very close with a very similar name). Pairs it was unsure about are saved for you:
- Recorded as new leads arrive: the same phone under a very different name, or a similar name within 300 m. `POST /quality/duplicates/scan` also looks through leads already stored (grid and phone blocking, so it stays fast) and flags pairs that should have merged as `likely`. Pairs you have decided are never offered again.
- `GET /quality/duplicates` lists pending pairs with both sides side by side. `POST /duplicates/{id}/merge {keep_id}` moves the other lead's contacts, source records, snapshots, classifications, AI results, history, tasks, outcome, do-not-contact marks, notes and any missing details onto the lead you keep, logs "Merged with a duplicate" on its timeline, rescores it and deletes the other. If the other lead had a closed deal and the kept one had none, the deal and status come across. **Merging cannot be undone.** `POST /duplicates/{id}/dismiss` records "not the same".

**Scoring from outcomes** (admin). `GET /quality/scoring?profile_id=` takes the leads you closed as won or lost and, for each of the six scoring traits (phone, mobile, working website, working email, 3+ reviews, name matches its segment), compares how often leads with and without it were won.
- **Honest about data:** nothing is suggested below 30 closed deals; a trait needs at least 5 leads on each side, and its difference must pass a two-proportion z-test (|z| of at least 1.64, about 90% confidence) before it is called clear. A clear trait gets half its win-rate difference (in points) added to or taken off its weight, by at most 25 and within 0-100. Everything else keeps its weight.
- **It shows what you worked, not why.** Only leads someone contacted get closed, so a pattern is a hint rather than proof.
- **Apply and undo.** `POST /scoring/apply` recomputes the suggestion on the server (the screen's numbers are not trusted), saves the old weights, updates the profile and rescores every lead for it; `POST /scoring/revert` restores them. Changing a profile's scoring weights by hand now rescores its leads too (before, scores only changed when a lead was next seen).

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
│   ├── ai/             # The Claude call: prompt, structured answer, model prices (pure Python)
│   └── scouting/       # The engine: sources (one module each), place_store (the local places files), website
│                       #   enrichment, phone/name normalisation, de-duplication, classification. Pure Python.
├── features/        # One folder per feature (auth, users, profiles, geographies, sources, runs, businesses,
│                    #   compliance, exports, sheets, insights, imports, pipeline, ai, jobs, schedules, alerts, quality, outreach, api_keys, public_api, webhooks), each with router/service/schemas/models
├── models.py        # Imports every ORM model (add new ones here)
└── main.py          # Application entry point

alembic/          # Database migrations
scripts/          # Utility/maintenance scripts (create_admin, seed + seed_data/, download_overture, download_foursquare, convert_aedb_pdf)
tests/            # Test suite
```

## Operating notes

Read these before putting it on a server.

- **Secrets.** `SECRET_KEY` must be at least 32 characters (the app refuses to start otherwise). Saved API keys and the Google service-account key are encrypted with `ENCRYPTION_KEY` (or a key derived from `SECRET_KEY`: rotating either means re-entering saved keys, and the screens say so). Never commit `.env`.
- **One process.** Runs, imports and AI batches are jobs kept in the database and carried out by threads inside the server, and the Sheets sync lock and the automatic-refresh timer are per process. Run **one** server process (one uvicorn worker). Jobs survive a restart (see *Background jobs and repeating searches*); a separate queue service (Celery/RQ) is the step to take before running on several machines.
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

In development. Completed: foundation, auth, user management, profiles, locations, seed data, scouting engine, sources (OpenStreetMap, Overture Maps, Foursquare Places, Google Places, HERE, TomTom), runs, leads API, do-not-contact, CSV export, Google Sheet mirror, insights. Imports (CSV/Excel lists) and the AEDB installer list added. Hardening done (lint, guard tests, concurrency, clean-install check). Lead history, follow-ups, deal outcomes and conversion reports added. AI assistant added. Background jobs survive restarts, searches can repeat on a schedule, and runs raise in-app alerts, and a data-quality screen checks contacts, reviews duplicates and learns from closed deals, and message templates open WhatsApp or the mail app with a send log. API keys, a public API, signed webhooks and CRM import files connect other software. Not built on purpose: two-way sheet sync, the app sending messages itself, a separate queue service (see Operating notes).
