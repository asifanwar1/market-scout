# Contributing to Market Scout

Thanks for helping. Bug reports, fixes, new sources and new screens are all welcome. For anything larger than a small fix, open an issue first so we can agree on the approach before you spend time on it.

By contributing you agree that your work is released under the project's [AGPL-3.0 license](LICENSE).

## Set up

Follow "Run it" in the [README](README.md). The backend needs Python 3.11+, the frontend Node 20+.

## Before you open a pull request

Run every check and make sure all pass:

```bash
cd market-scout-backend && pytest -q && ruff check .
cd market-scout && npm run lint && npm test && npm run build
```

Every new feature or service function needs tests (`tests/test_<feature>.py` in the backend, a `.test.ts` beside the code in the frontend). Tests must not touch the network: use the existing fakes for Google and OpenStreetMap.

## Conventions

The full rules are in [CLAUDE.md](CLAUDE.md). The ones people trip over most:

- **No comments** in source code (`#`, `//`, `/* */`, docstrings). Rename or restructure so the intent is clear. Explanations belong in the READMEs. Linter pragmas such as `# noqa` and `// eslint-disable-next-line` are the only exception.
- **No hardcoded values.** Statuses, URLs, limits, roles and magic numbers go in constants (`app/core/constants.py` or the feature's own module on the backend, `src/constants/*.constants.ts` on the frontend).
- **Backend:** one folder per feature under `app/features/<name>/` with `router.py`, `service.py`, `schemas.py`, `models.py` and `dependencies.py`. Routers only route; logic lives in the service. snake_case everywhere, including the JSON API.
- **Frontend:** each page has a `.tsx` that only renders and a `.Container.ts` that holds all state and logic. Arrow functions only, `type` not `interface`, no `any`, no inline JSX in `.map()`, and avoid `useMemo`, `useCallback` and `useEffect` unless there is a real need.
- **Colours** come only from tokens in `src/theme.css`.

## Data and privacy

Do not commit real people's or businesses' contact details, API keys, `.env` files or database files. Use fictional data in samples and tests. If you add a data source, document its terms of use and storage limits on the Sources screen and in the backend README.

## Reporting security problems

Do not open a public issue. See [SECURITY.md](SECURITY.md).
