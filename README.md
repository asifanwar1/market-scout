# Market Scout

A reusable business-discovery and market-intelligence system. It finds small businesses (dealers, importers, installers, retailers, wholesalers, contractors) in the places you sell, so a sales team can reach them outside its existing channels. The first industry it is set up for is solar, inverters and batteries in Pakistan; new industries are added from the screens, with no code changes.

| Folder | What it is |
|---|---|
| [market-scout-backend](market-scout-backend) | The API: FastAPI, SQLAlchemy/Alembic on SQLite (PostgreSQL later), the scouting engine |
| [market-scout](market-scout) | The web app sales and admins use: React, TypeScript, Tailwind, shadcn/ui |

## What it does

- **Finds businesses** in chosen cities from free sources (OpenStreetMap; Overture Maps and Foursquare Places, open datasets kept on your computer; plus reading each business's own website for email and WhatsApp) and, when a key is saved on the Sources screen, the paid Google Places, HERE and TomTom searches (check their storage terms first). No code change to switch; every run shows an estimate first and can carry a spending cap.
- **Imports lists you already have** (CSV or Excel, such as the government's certified-installer lists) through the same matching, scoring and do-not-contact checks, and can look up the missing phones of a name-only list in Overture Maps.
- **Merges and scores** what different sources report into one lead per business, sorted best first.
- **Sales work the leads in the app**: filter, call or WhatsApp, record status and notes, assign, bulk-update, export to CSV.
- **Helps you message leads**: shared message templates that fill in the business name, city and contact person, a button that opens WhatsApp or your mail app with the text ready, and a log of what was sent. You press send yourself, then confirm it was sent.
- **Connects to your other software**: API keys let your own programs and tools like Zapier read leads, add them and update them; signed webhooks tell them when a lead is found, changes status or a deal is won or lost; and leads export as files ready to import into HubSpot, Zoho CRM or any CRM.
- **Checks and cleans its own data**: marks emails that cannot receive mail and websites that are down (they stop counting towards a score), asks you about businesses that may be listed twice, and shows which traits go with the deals you win, with suggested score weights you approve.
- **Alerts you in the app** when a run finds a new lead that scores well, a business whose reviews are climbing, or a lead that can finally be contacted. The limits are set by an admin.
- **Repeats searches by itself** (daily, weekly or monthly) and adds only what is new. Runs, imports and AI batches are kept in the database, so a restart or crash does not lose them: they carry on where they stopped.
- **Reads a lead's website with Claude** (on demand, with a cost estimate and a monthly spending cap) to say what the business does, suggest a segment and rate how well it fits your ideal customer. It is advice and changes nothing by itself.
- **Tracks leads through to deals**: a history of what happened on each lead, follow-up tasks with due dates, the deal value or the reason a lead was lost, and reports of what turns into customers by source, segment and city.
- **Respects do-not-contact**: anyone asking to be left alone is excluded everywhere (lists, exports, the sheet, insights) and is refused if a later search finds them again.
- **Mirrors the leads to a Google Sheet** (one way, app to sheet) for people who prefer a spreadsheet.
- **Shows where the market is thin**: coverage by city and type, cities nobody has searched, which source is worth its cost, which businesses are growing.
- **Roles**: admins manage profiles, locations, sources, runs, users and the sheet; sales see leads, insights and do-not-contact.

## Run it

You need Python 3.11+ and Node 20+. Two terminals:

```bash
# 1. Backend (see market-scout-backend/README.md for details)
cd market-scout-backend
python -m venv venv && venv\Scripts\activate        # source venv/bin/activate on macOS/Linux
pip install -r requirements.txt
copy .env.example .env                              # then set SECRET_KEY (instructions inside)
alembic upgrade head
python -m scripts.create_admin --email you@example.com --password "Str0ng!Pass" --name "Your Name"
python -m scripts.seed                              # Pakistan's cities and the solar profile
uvicorn app.main:app --reload

# 2. Frontend (see market-scout/README.md)
cd market-scout
npm install
npm run dev
```

Open the address Vite prints, sign in, go to **Runs → New run**, pick a city, and start. If something else is already using port 8000, run the backend on another port and set `VITE_API_URL` in `market-scout/.env` (and `CORS_ORIGINS` in the backend's `.env`).

## Checks

```bash
cd market-scout-backend && pytest && ruff check .
cd market-scout && npm run lint && npm test && npm run build
```

## Where to read next

- [market-scout-backend/README.md](market-scout-backend/README.md): setup, configuration, roles, how runs/exports/the sheet/insights work, operating notes, troubleshooting.
- [market-scout/README.md](market-scout/README.md): the screens, project layout and frontend conventions.
