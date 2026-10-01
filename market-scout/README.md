# Market Scout (frontend)

The web app for Market Scout: the sales team's leads workspace and the admin's tools for finding new businesses. It talks to the API in the sibling `market-scout-backend` folder.

## What's in it

- **Insights** (everyone): headline numbers, leads over time, a city × business-type coverage map, "where to look next" (cities with few or no leads; admins get a **Search here** button that opens a new run with the city chosen), which source is worth it (with estimated cost per lead for paid ones), and businesses whose reviews are growing.
- **Leads** (everyone): a filterable, sortable table of the businesses found so far, best first. Filters live in the URL, so a view can be bookmarked or shared. Click a lead for its contacts (call, WhatsApp, email), where it came from, and to record status, notes and who owns it. Select several to assign or change status in bulk. **Export CSV** downloads everything the current filters match (do-not-contact people are never included). Anyone can mark a business **do not contact**.
- **Runs** (admins only): start a search (choose the profile, cities, sources), see an estimate of the searches, time and cost *before* it starts, then watch its progress live. Each finished run shows how complete each source's results were (phone / website / email), which is how you judge whether a paid source is worth it.
- **Administration** (admins only):
  - **Profiles**: define an industry without touching code: its segments, search terms (including the OpenStreetMap filter for each), and how leads are scored. Editing validates as you type, warns before you leave with unsaved changes, and updates in place so existing leads keep their segment.
  - **Locations**: the provinces and cities a run can search, with each city's centre and radius.
  - **Sources**: switch sources on and off, save the Google Places API key (stored encrypted, never shown again), and test the connection.
  - **Google Sheet**: connect a Google Sheet that mirrors the leads live (paste a Google service-account key, share the sheet with its address, press Sync now). It refreshes by itself after runs and edits; the sheet is a read-only copy, so share it view-only. The screen walks through the Google setup.
  - **Users**: create accounts and change roles, passwords and access.
- **Do not contact** (everyone can view and add; only admins can lift a block): a business, phone number or email that asked not to be contacted.
- Sales accounts see only Leads and Do not contact; the admin routes are guarded too, and the API enforces the same rule.

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

Pages follow the pulse-store pattern: `Page.tsx` renders, `Page.Container.ts` holds the state, queries and handlers.

## How sign-in works

Access tokens last 30 minutes, so the API client swaps the refresh token for a new pair the first time a request comes back 401 and replays the request; several requests failing together share one refresh. If that fails the user is signed out. "Sign out" ends this browser's session only.

## Notes for whoever touches this next

- **TanStack Table is pinned to v8.** `npm install @tanstack/react-table` currently gives v9, which is a different API.
- **Forms opt out of the React Compiler.** Every component or hook that uses React Hook Form (`register`, `reset`, `useFieldArray`) starts with `"use no memo"`. Without it the compiler caches the `register()` results, so after a `reset()` (e.g. "Discard changes") the inputs stop being tracked: they don't revert and never mark the form dirty. Do the same in any new form.
- **`DataTable` opts out of the React Compiler** (`"use no memo"`): `useReactTable` returns unstable functions and the compiler would otherwise freeze the table.
- **Base UI state names are mapped to Radix.** The shadcn "radix-vega" components use Base UI's `data-checked` / `data-open` attributes, but Radix reports `data-state="checked"` etc. `src/theme.css` maps one onto the other (`@custom-variant`); without it switches and checkboxes have no fill when on. Header actions use the card's `CardAction` slot.
- **Adding shadcn components:** the CLI resolves the `@/` alias from the root `tsconfig.json` (that's why it has a `paths` entry). Check that generated files import `cn` from `@/lib/utils`; the CLI wrote `"cn"` once, which had to be corrected. `checkbox.tsx` has a local edit (a dash for the partly-selected state).
- Run-estimate requests are `silent`: their errors show inline instead of as toasts, because the estimate refreshes as options change.
