# Market Scout (frontend)

The web app for Market Scout: the sales team's leads workspace and the admin's tools for finding new businesses. It talks to the API in the sibling `market-scout-backend` folder.

## What's in it

- **Insights** (everyone): headline numbers, leads over time, a city × business-type coverage map, "where to look next" (cities with few or no leads; admins get a **Search here** button that opens a new run with the city chosen), which source is worth it (with estimated cost per lead for paid ones), businesses whose reviews are growing, the **sales pipeline** (how far leads got, wins, losses, win rate, revenue and why leads were lost) and **what turns into customers** by source, segment or city.
- **Leads** (everyone): a filterable, sortable table of the businesses found so far, best first. Filters live in the URL, so a view can be bookmarked or shared. Click a lead for its contacts (call, WhatsApp, email), where it came from, and to record status, notes and who owns it. Select several to assign or change status in bulk. The lead panel also holds the lead's **follow-ups** (a title and a due date), its **history** (status and owner changes are logged for you, and you log calls, WhatsApp, emails, meetings and notes), and, when you move a lead to Customer or Not interested, a short form for the **deal** (value and product) or the **reason it was lost**. **Export CSV** downloads everything the current filters match (do-not-contact people are never included). Anyone can mark a business **do not contact**.
- **Runs** (admins only): start a search (choose the profile, cities, sources), see an estimate of the searches, time and cost *before* it starts, then watch its progress live. Each finished run shows how complete each source's results were (phone / website / email), which is how you judge whether a paid source is worth it.
- **Administration** (admins only):
  - **Profiles**: define an industry without touching code: its segments, search terms (including the OpenStreetMap filter for each), and how leads are scored. Editing validates as you type, warns before you leave with unsaved changes, and updates in place so existing leads keep their segment.
  - **Locations**: the provinces and cities a run can search, with each city's centre and radius.
  - **Sources**: switch sources on and off, save the Google Places API key (stored encrypted, never shown again), test the connection, and see whether the Overture Maps data has been downloaded.
  - **Imports**: upload a CSV or Excel list (certified installers, chamber directories, customs records), confirm which column is which, and watch it being added to Leads. Rows are matched against the businesses you already have; anyone on do-not-contact is refused. Tick "Look up missing phones in Overture Maps" for a list that only names its businesses. Each list becomes a "Found by" source you can filter Leads by and compare on Insights.
  - **Google Sheet**: connect a Google Sheet that mirrors the leads live (paste a Google service-account key, share the sheet with its address, press Sync now). It refreshes by itself after runs and edits; the sheet is a read-only copy, so share it view-only. The screen walks through the Google setup.
  - **Users**: create accounts and change roles, passwords and access.
- **Tasks** (everyone): your follow-ups across all leads, in tabs for overdue, today, upcoming, all open and done, with a switch for "only mine". Tick one off to complete it; a badge on the sidebar item counts what is overdue or due today.
- **Integrations** (admins only): create API keys (read-only, or able to add and change leads) for your other software, add webhooks that are called when a lead is found, changes status, raises an alert or a message is sent, see each call and send a failed one again, and read a short guide to the public API. Keys and signing secrets are shown once, when made. On the Leads page, **Export** also offers files shaped for HubSpot, Zoho CRM or any CRM.
- **Outreach** (everyone; admins edit templates): message templates that fill in the business name, city and contact person, and a send log. On a lead, **Message** picks a phone or email, a template and lets you edit the text, then opens WhatsApp or your mail app. It never sends anything itself: after you press send there, confirm here and the message is logged on the lead's history and a new lead becomes contacted. **Copy text** copies the message without logging it. The lead panel also has a **Contact person** field used in messages.
- **Data quality** (admins only): review pairs of leads that may be the same business and merge them or say they are different; see which traits (phone, working email, website and so on) go with the deals you won, with suggested score weights to apply or undo; and switch on automatic contact checks after each run. Anyone can select leads on the Leads page, or open one, and press **Check contacts**: it looks up whether each email's domain can receive mail and whether the website answers, and flags phone numbers shared by many businesses. It never sends anything.
- **Alerts** (everyone): a list of what the latest runs found that is worth a look (new leads that score well, businesses gaining reviews, leads that gained a phone or email), with an unread count on the sidebar. Opening an alert's lead marks it read; *Mark all read* clears the list. Admins set the limits at the bottom of the page.
- **Repeating searches** (admins only): on the New run screen, switch on *Repeat this search*, choose how often and save. The Repeating searches screen lists them with when each runs next and what its last run found, and lets you pause one, run it now or delete it. It also tells you whether the background worker is running.
- **AI assistant** (admins only): save the Anthropic API key, choose the model, set the monthly budget and see what has been spent, with a test button. In the lead panel, an **AI assessment** section shows what the AI says about a lead (summary, suggested segment, fit score) and lets anyone press **Analyze with AI**; on the Leads list you can select leads and **Analyze with AI** in bulk (after a cost estimate), see an **AI fit** column, sort by it and filter by a minimum. In the profile editor, **Your ideal customer** is the text the AI scores against.
- **Do not contact** (everyone can view and add; only admins can lift a block): a business, phone number or email that asked not to be contacted.
- Sales accounts see Leads, Tasks, Insights and Do not contact (and can use Analyze with AI, but not change its settings); the admin routes are guarded too, and the API enforces the same rule.

## Tech stack

Same as `pulse-store-admin`:

- **React 19** + **TypeScript** + **Vite** (with the React Compiler)
- **Tailwind CSS 4** + **shadcn/ui** (Radix)
- **TanStack Query** (server state) and **TanStack Table v8**
- **React Router 7**, **Zustand** (auth), **nuqs** (filters in the URL)
- **react-hook-form** + **zod**, **axios**, **react-toastify**

## Getting started

1. Start the backend (see `market-scout-backend/README.md`) on http://localhost:8000.
2. Install and configure:

   ```bash
   npm install
   cp .env.example .env   # VITE_API_URL should point at the backend, including /api/v1
   ```

3. Run it:

   ```bash
   npm run dev      # http://localhost:5173
   npm run build    # type-check + production build
   npm run lint
   npm test         # unit tests (Vitest) for the pure logic: OSM filter parsing, profile form mapping
   ```

The backend allows the origin `http://localhost:5173` by default (`CORS_ORIGINS`).

If another project already uses port 8000, run the backend on a different port (`uvicorn app.main:app --port 8010`) and start the dev server with `VITE_API_URL=http://localhost:8010/api/v1` (or change `.env`).

## Project structure

```
src/
├── api/
│   ├── client/        # axios instance, interceptors (auth header, token refresh), request()
│   ├── models/        # shared types (user)
│   ├── services/      # one folder per backend feature: index.ts, *.request.types.ts,
│   │                  #   *.response.types.ts, queryKeys.ts
│   └── types/
├── components/
│   ├── ui/            # shadcn primitives
│   └── custom/        # DataTable, Pagination, ConfirmationModal, StatusBadge, ...
├── constants/         # statuses, roles, messages
├── hooks/api/         # TanStack Query hooks per feature
├── layouts/           # MainLayout (sidebar + topbar), AuthLayout, menu config
├── pages/             # Leads/, Runs/ (list, NewRun/, RunDetails/), Authentication/, NotFound/
├── providers/         # query client, toasts
├── routes/            # APP_ROUTES, router, role guard
├── store/             # Zustand auth store (persisted)
└── utils/
```

Each page is a folder: `Page.tsx` only renders, `Page.Container.ts` holds the state, queries and handlers, `Page.constants.ts` and `Page.types.ts` its constants and types, `index.ts` re-exports it and `Components/` holds what only that page uses. The rules (no comments, constants not literals, arrow functions, no inline JSX in `.map()`) are in the repo's `CLAUDE.md`.

## How sign-in works

Access tokens last 30 minutes, so the API client swaps the refresh token for a new pair the first time a request comes back 401 and replays the request; several requests failing together share one refresh. If that fails the user is signed out. "Sign out" ends this browser's session only.

## Notes for whoever touches this next

- **TanStack Table is pinned to v8.** `npm install @tanstack/react-table` currently gives v9, which is a different API.
- **Forms opt out of the React Compiler.** Every component or hook that uses React Hook Form (`register`, `reset`, `useFieldArray`) starts with `"use no memo"`. Without it the compiler caches the `register()` results, so after a `reset()` (e.g. "Discard changes") the inputs stop being tracked: they don't revert and never mark the form dirty. Do the same in any new form.
- **`DataTable` opts out of the React Compiler** (`"use no memo"`): `useReactTable` returns unstable functions and the compiler would otherwise freeze the table.
- **Base UI state names are mapped to Radix.** The shadcn "radix-vega" components use Base UI's `data-checked` / `data-open` attributes, but Radix reports `data-state="checked"` etc. `src/theme.css` maps one onto the other (`@custom-variant`); without it switches and checkboxes have no fill when on. Header actions use the card's `CardAction` slot.
- **Adding shadcn components:** the CLI resolves the `@/` alias from the root `tsconfig.json` (that's why it has a `paths` entry). Check that generated files import `cn` from `@/lib/utils`; the CLI wrote `"cn"` once, which had to be corrected. `checkbox.tsx` has a local edit (a dash for the partly-selected state).
- Run-estimate requests are `silent`: their errors show inline instead of as toasts, because the estimate refreshes as options change.
