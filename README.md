# Market Scout

A reusable business-discovery and market-intelligence system. It finds small businesses (dealers, importers, installers, retailers, wholesalers, contractors) in the places you sell, so a sales team can reach them outside its existing channels. The first industry it is set up for is solar, inverters and batteries in Pakistan; new industries are added from the screens, with no code changes.

| Folder | What it is |
|---|---|
| [market-scout-backend](market-scout-backend) | The API: FastAPI, SQLAlchemy/Alembic on SQLite (PostgreSQL later), the scouting engine |
| [market-scout](market-scout) | The web app sales and admins use: React, TypeScript, Tailwind, shadcn/ui |

## What it does

- **Finds businesses** in chosen cities from free sources (OpenStreetMap, plus reading each business's own website for email and WhatsApp) and, when a key is saved on the Sources screen, the Google Places API. No code change to switch; every run shows an estimate first and can carry a spending cap.
- **Merges and scores** what different sources report into one lead per business, sorted best first.
- **Sales work the leads in the app**: filter, call or WhatsApp, record status and notes, assign, bulk-update, export to CSV.
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
