# Local CORS, Scraper Key, and Password Visibility Design

**Date:** 2026-07-12

**Status:** Approved for implementation planning

## Goal

Fix Flutter web registration from random local development ports, make local
scraper ingestion use the configured API key reliably, add password-visibility
controls to authentication forms, and document the workflows in
`walkthrough.md`.

## Verified Root Causes

### Registration fetch failure

Flutter currently runs at a random development origin such as
`http://localhost:52498`. Django is configured with
`CORS_ALLOWED_ORIGINS=['http://localhost:3000']`, so the browser's preflight
response omits `Access-Control-Allow-Origin`. The browser reports
`ClientException: Failed to fetch` even though Django is listening on port
`8000`.

### Scraper 403

The running backend accepts the current `SCRAPER_API_KEY` in `backend/.env`: a
safe empty-product probe passed authentication and returned `400 No products
provided`. Therefore `ci_runner.py` supplied a different value. The runner
currently reads only `--key`; it does not resolve `SCRAPER_API_KEY` from the
process environment or the local backend environment file.

## CORS Design

Development CORS remains restricted, not globally open:

- When `DEBUG=True`, allow HTTP origins matching localhost or `127.0.0.1` on
  any numeric port through `CORS_ALLOWED_ORIGIN_REGEXES`.
- When `DEBUG=False`, allow only `CORS_ALLOWED_ORIGINS` from the environment.
- Keep `CORS_ALLOW_ALL_ORIGINS=False` in every environment.
- Add tests proving a random Flutter localhost port receives the CORS header and
  an unrelated origin does not.

This supports Flutter's random development ports without allowing arbitrary
internet origins.

## Scraper Key Resolution

`ci_runner.py` resolves its key with explicit precedence:

1. `--key` command-line argument.
2. `SCRAPER_API_KEY` from the current process environment.
3. `SCRAPER_API_KEY` from the repository-local ignored `backend/.env` file.

The backend environment file is loaded only for local convenience and never
overrides an explicit command-line or process value. Add `python-dotenv` to
`Scrapper/requirements.txt` so the behavior is reproducible in the scraper
environment.

When pushing to a backend and no key can be resolved, `ci_runner.py` exits with
a parser error before scraping or sending requests. `--dry-run` and
`--list-jobs` continue to work without a key. No log or exception includes the
resolved key.

Tests cover precedence, local file fallback, missing-key rejection, and the
existing dry-run/list behavior.

## Password Visibility Controls

Add local widget state and accessible suffix icon buttons to:

- Login password field.
- Registration password field.
- Registration confirmation field.

Each field starts obscured. Tapping its control toggles only that field, changes
the icon between visibility and visibility-off, and updates the tooltip and
semantic label. Registration password and confirmation visibility are
independent.

Widget tests verify the default obscured state and tap-to-reveal behavior for
login and both registration fields.

## Walkthrough Update

Update `walkthrough.md` with:

- Explanation of Flutter's random local web port and the restricted localhost
  CORS regex.
- Restart requirement after changing Django environment or settings.
- Scraper key precedence.
- Recommended local batch command without exposing the key:

  ```powershell
  cd Scrapper
  python ci_runner.py --backend http://127.0.0.1:8000
  ```

- Explicit `--key` override guidance using placeholders only.
- `403 Invalid API key` troubleshooting: verify the same configured source,
  restart Django after `.env` changes, and never pass the literal placeholder.
- Registration `Failed to fetch` troubleshooting: confirm frontend origin,
  backend port, CORS preflight header, and Django restart.
- Password-visibility behavior.

## Testing and Verification

- Django CORS tests pass.
- Scraper unit tests pass.
- Flutter password-toggle widget tests pass.
- Full Django and Flutter suites pass.
- Flutter analysis and release build pass.
- `manage.py check` passes against PostgreSQL 5433.
- No secret values appear in diffs or output.

## Safety Rules

- Never print, commit, or echo the scraper key.
- Never make production CORS permissive.
- Never automatically copy secrets into tracked files.
- Do not restore or modify the currently deleted `backend/.env.example`.
- Do not change the local PostgreSQL data.

## Acceptance Criteria

1. Flutter web registration from a random localhost port passes CORS preflight.
2. Non-local development origins remain rejected.
3. `ci_runner.py` uses CLI, process environment, then `backend/.env` precedence.
4. Missing keys fail before scraping when a backend push is requested.
5. Login and both registration password fields have independent visibility
   controls.
6. Tests and builds pass.
7. `walkthrough.md` contains safe, exact troubleshooting steps.
8. `backend/.env.example` remains untouched.

## Non-Goals

- Allowing arbitrary development origins.
- Changing production deployment domains.
- Running the scraper or inserting products automatically.
- Displaying, rotating, or rewriting secret values.
- Redesigning authentication screens beyond password visibility controls.
