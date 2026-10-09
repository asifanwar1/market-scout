# Market Scout: System Overview

## What it is

Market Scout is a web application that finds businesses to sell to. You tell it which industry and which cities you care about, and it searches open data sources, merges what it finds into one clean list of leads, scores them, and gives a sales team a workspace to call, message and track them.

It was built first for the solar, inverter and battery market in Pakistan, where it finds dealers, importers, installers, retailers, wholesalers and contractors that a sales team would not reach through its existing channels. The industry is not fixed in the code: it is a configuration (a "profile") that can be replaced from the screens.

## The problem it solves

Finding the right businesses in a market is slow manual work: searching maps, copying phone numbers into spreadsheets, checking whether a business is already on the list, and keeping the sales team from contacting people who asked to be left alone. Market Scout does the finding, cleaning and de-duplication automatically and keeps everything in one place.

## What it can do

### 1. Find businesses automatically
- Searches **OpenStreetMap** and **Overture Maps** for free. Overture is an open dataset of about 217,000 places in Pakistan, stored on your own computer, so it needs no network and no key when searching.
- Also searches **Foursquare Places**, a second open dataset kept on your computer. It needs a one-time download of Foursquare's files (a free portal account is required).
- Optionally uses the paid **Google Places**, **HERE** and **TomTom** searches when a key is saved. Each run shows an estimate of searches and cost first and can carry a spending cap. These providers limit how long their results may be stored, and the Sources screen shows each one's storage terms.
- Reads each business's own **website** for email, WhatsApp and social pages. It respects robots.txt and only visits public addresses.
- Switching sources on and off, or adding an API key, is done from the screens.

### 2. Import lists you already have
- Upload a **CSV or Excel** file, such as a government certified-installer list, a chamber directory or customs records.
- The app guesses which column is which, cleans phone numbers (including mobiles that Excel stripped the leading zero from), and runs every row through the same matching, scoring and do-not-contact checks as a search.
- For lists that only have business names, it can look up missing phone numbers from Overture Maps, but only when exactly one business has the same name in that city. Wrong numbers are treated as worse than no number.
- Includes a converter for the official Pakistani certified-installer PDF lists, with sample data for 600+ installers.

### 3. Merge and score leads
- Results from different sources are merged into **one lead per business** (same website, same phone with a similar name, or the same spot with a near-identical name).
- Every phone and email records which source reported it, and each source's raw answer is kept.
- Each lead gets a **score** from the profile's weights for what it has: phone, WhatsApp-capable mobile, website, email, reviews, and a name that matches its segment. Leads are shown best first.

### 4. Let the sales team work the leads
- Filter, sort and search leads by segment, city, province, contact details, status, owner, source and minimum score.
- Open a lead to call, WhatsApp or email, then record status, notes and who owns it. Change status or owner for up to 500 leads at once.
- Filters live in the URL, so a view can be bookmarked or shared.
- Export the current view to **CSV or Excel**.
- Every status and owner change is logged on the lead, and you can log calls, WhatsApp messages, emails, meetings and notes. Set **follow-ups** with a due date and work them from a Tasks screen with an overdue badge.
- Moving a lead to Customer records the **deal** (value and product); moving it to Not interested records **why it was lost**.

### 5. Respect do-not-contact
- Anyone can record that a business, phone number or email asked not to be contacted. Only an admin can lift it.
- Blocked people disappear from every list, export, sheet and insight, and are refused if a later search finds them again under a new record.

### 6. Mirror leads to a Google Sheet
- A one-way copy from the app to a Google Sheet for people who prefer spreadsheets. It refreshes by itself after runs and edits and never writes anyone on the do-not-contact list.

### 7. Show where the market is thin
The Insights screen turns the stored data into market intelligence:
- headline numbers and new leads over time;
- a **coverage matrix** of cities by business type;
- **gaps**: cities nobody has searched yet, and cities searched with little found;
- **source comparison**: which source finds the most, which finds leads only it can find, and the estimated cost per lead for paid ones;
- **movers**: businesses whose review counts are growing fastest;
- the **sales pipeline**: how far leads got, wins, losses, win rate, revenue and loss reasons;
- **conversion** by source, segment or city, so you can see which source produces customers and not just leads.

### 8. Manage industries, places and people
- **Profiles**: define an industry without code, with its segments, search terms and scoring weights.
- **Locations**: a country, province and city hierarchy, each city with a centre point and search radius.
- **Users and roles**: admins manage everything; sales see leads, insights and do-not-contact.

## How it works at a glance

1. An admin picks a profile, cities and sources and starts a **run**. The app shows the estimated searches, time and cost first.
2. A background worker searches each source, reads websites for contact details, and stores what it finds.
3. Results are normalised, de-duplicated against existing leads, scored, and filtered against do-not-contact.
4. Sales opens the Leads page, works the list, and the Google Sheet refreshes in the background.
5. Insights shows what is covered and where to search next.

## Technology

| Part | Stack |
|---|---|
| Backend | Python, FastAPI, SQLAlchemy and Alembic, SQLite (written to move to PostgreSQL), Pydantic, JWT auth with refresh tokens, rate limiting |
| Frontend | React 19, TypeScript, Vite, Tailwind CSS 4, shadcn/ui, TanStack Query and Table, React Router, react-hook-form with zod |
| Engines | Three pure-Python subsystems with no database or web framework: scouting (sources, normalising, de-duplication, classification), importing (CSV/Excel, column mapping, lookups) and Google Sheets |
| Quality | Backend tests with pytest, linting with ruff, frontend tests with Vitest. The tests use fakes for Google and OpenStreetMap, so none touch the network. Guard tests fail if a route's access level is unlisted, if `.env.example` misses a setting, or if models and migrations disagree |

The backend follows a feature-based structure (one folder per feature with router, service, schemas and models). The frontend follows a page/container structure where each page's component only renders and its container holds all logic.

## What it deliberately does not do (yet)

- It does not send messages. It finds and organises leads; how your team contacts them is up to you.
- The Google Sheet sync is one-way, from app to sheet. Edits in the sheet are overwritten.
- There is no LLM-based classification.
- There is no job queue. Runs execute on a background thread inside one server process, so it should run as a single process until it moves to a real queue.
- It runs on SQLite today. That is fine for one machine and would need PostgreSQL to scale.

## Using it for another industry or country

- **Another industry in Pakistan:** create a new profile with its segments, search terms (including the OpenStreetMap filter for each) and scoring weights. No code changes.
- **Another country:** add the country's locations. The bundled Overture copy and seed data are for Pakistan, so check the Overture download script before relying on it for another country.
- **Industries with public registries or lists:** import them as CSV or Excel, or add a new source to the scouting engine.

## More detail

- [README.md](README.md): short project summary and how to run it.
- [market-scout-backend/README.md](market-scout-backend/README.md): setup, configuration, how runs, imports, exports, the sheet and insights work, operating notes and troubleshooting.
- [market-scout/README.md](market-scout/README.md): the screens, project layout and frontend conventions.
