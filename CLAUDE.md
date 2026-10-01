# Market Scout — Project Conventions

Binding conventions for every change in this repo, backend and frontend. Read the relevant section before touching code so these don't need repeating per prompt.

## Universal (backend + frontend)

### No comments
No comments anywhere in project source — no `#`, `//`, `/* */`, or docstrings, backend or frontend (tests, scripts and migrations included). Naming and structure should make intent obvious; if they can't, rename or restructure rather than annotate. Explanations of why something works the way it does belong in the READMEs.

Exception: tool-directive pragmas a linter/type-checker needs to actually function (`# type: ignore[...]`, `# noqa: E501`, `// eslint-disable-next-line ...`) aren't documentation — keep using them when genuinely needed, never to explain code.

Text a program prints for people (CLI usage text, error messages) is data, not a comment: keep it in a named constant.

### No hardcoded values — constants only
Never inline a literal that carries meaning (a status string, a URL, a limit, a permission/role code, a magic number). It belongs in a constants file, not the call site.
- Frontend: app-wide constants go in `src/constants/*.constants.ts`. A constant only one module cares about lives beside that module instead.
- Backend: a value used by a single feature stays a module-level constant in that feature's own file; a value used by 2+ features goes in `app/core/constants.py`, created the first time a real cross-feature constant shows up.

### Ask when genuinely unsure
Ask before guessing on anything actually ambiguous — a naming call with real cost either way, a structural decision, a conflict between a new instruction and something already built. Don't ask about things resolvable by just reading the code.

### Milestone workflow
Build one milestone, verify it for real (tests plus a real browser/API run), write a short plain-language summary, then stop until told to continue. Nothing is committed unless asked.

## Backend (`market-scout-backend/`)

### Folder & file structure
Feature-based / vertical-slice architecture. Each feature is a self-contained folder under `app/features/<name>/`:

```
app/
  core/
    constants.py
    config.py
  features/
    auth/
      router.py
      service.py
      schemas.py
      models.py
      dependencies.py
```

- `router.py` — route definitions only, delegates to `service.py`.
- `service.py` — business logic for the feature.
- `schemas.py` — Pydantic request/response models for the feature.
- `models.py` — ORM models for the feature.
- `dependencies.py` — FastAPI `Depends` callables local to the feature.

`app/core/` is for code shared by 2+ features (`config.py`, `constants.py`, `database.py`, `dependencies.py`, security, exceptions, crypto). Don't put single-feature code there, and don't pre-create empty core files before a real cross-feature need shows up.

Established exception: the three engines are pure-Python subsystems with no database or web framework, deliberately kept apart from the features that use them, and stay in `app/core/`: `scouting/` (sources, normalising, de-duplication, classification), `importing/` (reading CSV/Excel, mapping columns, looking up contacts) and `sheets/` (the Google Sheets client).

### Naming
snake_case in Python everywhere. Deviation from the usual camelCase-on-the-wire rule, decided for this project: the JSON API stays snake_case too (`is_available`, `rows_total`), so schemas inherit `BaseModel` directly.

### Testing
Every new feature or service function gets tests in `tests/test_<feature>.py` (engine code under `tests/<engine>/`). After implementing or modifying anything, run the full backend check before calling it done:
```
pytest -q
ruff check .
```
mypy is not used in this project (decided deliberately; the models use SQLAlchemy's `Column` style).

## Frontend (`market-scout/`)

### Folder & file structure per page/module
Each page or module gets its own folder under `src/pages/`, containing:
- `<Name>.tsx` — presentation only: JSX and prop destructuring, nothing else.
- `<Name>.Container.ts` — all state, hooks, handlers, derived values, and logic for that page. The `.tsx` file calls this and renders what it returns.
- `<Name>.types.ts` — types local to that page.
- `index.ts` — barrel re-export.
- `Components/` — components used only within this page/module, not reusable elsewhere.

```
pages/Dashboard/
  Dashboard.tsx
  Dashboard.Container.ts
  Dashboard.types.ts
  index.ts
  Components/
    SummaryCard.tsx
```

A module with sibling sub-pages nests one level deeper — each sub-page repeats this same structure inside the parent folder.

### Reusable vs. page-local
- Used by exactly one page/module → stays in that page's own `Components/` folder.
- Used by 2+ pages/modules → move to `src/components/` (e.g. `src/components/custom/`).
- Same rule for logic: a function or hook used by only one page can live in that page's `.Container.ts`; once a second page needs it, extract it to `src/utils/` (plain functions) or `src/hooks/` (stateful/React logic).

### The Container pattern
No logic in a page's top-level `.tsx` file — no `useState`, no data transforms, no event-handler bodies. All of that lives in `<Name>.Container.ts`, which the `.tsx` file calls (typically one function returning everything the view needs), keeping the `.tsx` file a pure render function.

This restriction is specifically for page-level files. Ordinary components — page-local (`Components/`) or shared (`src/components/`) — are normal React components and can hold their own logic inline; they don't need a paired Container file.

A Container's final `return` is a plain object of already-computed identifiers — no assignment, condition, or expression evaluated inline as a value. Compute each value into its own `const` above the `return`, then return bare names only, one per line:

```ts
const isReady =
    !isLoadingFamilies &&
    (mode === "add" || (!isLoadingExisting && !!existing));
const isSubmitting = isCreating || isUpdating;

return {
    isReady,
    defaultValues,
    formConfig,
    isSubmitting,
    existing,
    onSubmit,
    goBack,
};
```

Not this — no inline boolean logic or expressions as return-object values:

```ts
return {
    isReady: !isLoadingFamilies && (mode === "add" || (!isLoadingExisting && !!existing)),
    isSubmitting: isCreating || isUpdating,
};
```

### Form submit payloads go through a dedicated builder function
A Container's `onSubmit` never assembles the request body inline. Define a `build<Name>Payload` function above `onSubmit` that takes the form values and returns the request body, then have `onSubmit` call it:

```ts
const buildLoginPayload = (values: ILoginFormValues): TLoginPayload => ({
    ...values,
    rememberMe: !!values.rememberMe,
});

const onSubmit = async (values: ILoginFormValues) => {
    const body = buildLoginPayload(values);
};
```

### No inline JSX inside `.map()`
A `.map()` call never returns JSX inline. Define a function that returns the JSX for one item above the component's `return`, then call that function from `.map()`:

```tsx
const renderRow = (row: RowType) => (
    <div key={row.id} className="grid grid-cols-12 gap-2 items-end">
        ...
    </div>
);

return <div>{rows.map(renderRow)}</div>;
```

### Types
Type every function signature and every piece of state. No `any`, no `unknown`. Use `type`, never `interface`. For the rare case where a value's real type genuinely isn't known up front (e.g. a `catch` block), narrow it with a type guard before use rather than leaving it loosely typed.

### Functions: arrow only
Arrow function syntax everywhere — components, handlers, helpers. Never `function` declarations or expressions.

### Hooks: default to not using them
Avoid `useMemo` and `useCallback`. Avoid `useEffect` too, except when there's a real need — syncing with something outside React (a subscription, a non-React widget, a manual DOM measurement). Not a real need: deriving a value from props/state (compute it inline during render), fetching data (use TanStack Query), or resetting state on a prop change (use a `key` instead).

### Colors: theme-only
No hardcoded colors in any component or style file — no inline hex/rgb/named colors. Every color is a token declared in `src/theme.css` (the theme file) and referenced from there, so light/dark mode both stay correct automatically.

Files under `src/components/ui/` are shadcn/ui output; they follow the same comment, arrow-function and colour rules, but their structure stays as the library generates it. `src/vite-env.d.ts` keeps `interface` because augmenting `ImportMeta` needs declaration merging.
