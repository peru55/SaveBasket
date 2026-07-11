# SaveBasket Backend Recovery and Error States Design

**Date:** 2026-07-12

**Status:** Approved for implementation planning

## Goal

Make the frontend distinguish authentication failures from a genuinely offline
backend, and update `walkthrough.md` with verified PostgreSQL 5433, Django admin,
and scraper-ingestion recovery steps.

## Verified Current State

- Django connects to PostgreSQL at `127.0.0.1:5433`.
- All Django migrations are applied and `manage.py check` passes.
- Django `runserver` is listening on port `8000`.
- The PostgreSQL database currently contains zero users, superusers,
  supermarkets, branches, products, prices, baskets, and ingestion runs.
- The username configured in `backend/.env` does not exist in PostgreSQL.
- The frontend displays `Backend offline` whenever basket initialization fails,
  including HTTP authentication failures.
- `backend/.env.example` is currently deleted in the working tree and is outside
  this change unless the user separately requests restoration.

## Root Causes

### Admin login

Switching from SQLite to PostgreSQL changes the database containing Django's
authentication tables. Superusers from the old database do not automatically
exist in PostgreSQL. `DJANGO_SUPERUSER_*` environment variables provide inputs
to `createsuperuser --noinput`; they do not create or continuously synchronize
an account by themselves.

### Empty catalog

The new PostgreSQL database has the schema but no application rows. Migrations
create tables, not supermarket or product data. Data must be seeded explicitly
or pushed through `/api/scraper/ingest/` with the configured scraper key.

### Misleading offline message

`BasketProvider.initializeBasket()` catches every exception and stores the same
connection-error message. `ApiService.createBasket()` currently discards the
HTTP status and throws a generic exception. A stale JWT after the database
switch therefore appears identical to a refused network connection.

## Frontend Error Architecture

### Typed error interface

Create a small `ApiException` interface that preserves:

- a user-safe message;
- optional HTTP status code;
- whether the request failed before receiving an HTTP response;
- optional underlying cause for diagnostic output.

`ApiService.createBasket()` must translate outcomes as follows:

- `201`: return the created basket.
- `401` or `403`: throw an authentication `ApiException`.
- Other HTTP status: throw a backend-response `ApiException` with the status.
- Socket/client failure before a response: throw a connection `ApiException`.

No secret, token, password, or raw response body is included in user-facing
messages.

### Provider state

Replace the single ambiguous error string with an error category and message:

- `authentication`: title `Session expired`; guide the user to log out and sign
  in against the new database.
- `connection`: title `Backend offline`; guide the user to start Django and
  verify the configured API origin.
- `server`: title `Backend error`; report that Django responded but could not
  initialize the basket.

The dashboard error card consumes this category for its title/icon/copy. The
existing reconnect action remains for connection and server errors. The
authentication state offers a sign-in/logout recovery action rather than
repeatedly retrying a stale token.

## Testing

Implementation follows red-green-refactor.

- Unit-test `ApiException` classification.
- Test basket creation with `201`, `401`, `403`, and another server status.
- Test a client/network failure without a response.
- Test `BasketProvider` maps authentication, connection, and server errors to
  distinct states.
- Widget-test each dashboard error title and recovery action where practical.
- Run the complete Flutter suite and analysis.
- Re-run Django checks because the walkthrough commands describe the current
  backend behavior.

## Walkthrough Update

Update `walkthrough.md` with a dated current-state section containing:

1. PostgreSQL settings for local port `5433`, with password values represented
   only as placeholders.
2. Connection and migration verification commands.
3. Explanation that a database switch requires recreating users.
4. Interactive superuser creation:

   ```powershell
   cd backend
   .\.venv\Scripts\python.exe manage.py createsuperuser
   ```

5. Environment-driven, idempotent setup guidance: run
   `createsuperuser --noinput` only when the account does not exist, then use
   `changepassword <username>` to reset an existing account.
6. Staff/superuser flag verification without printing passwords.
7. Start-server and port-listener checks.
8. Stale-token recovery after a database switch: log out or clear local app
   storage, register/sign in again, then reconnect.
9. Single-product scraper push with `run_scraper.py --backend ... --key ...`.
10. Batch ingestion with `ci_runner.py` and existing JSON ingestion with
    `sync_json_to_backend.py`.
11. ORM count checks confirming supermarkets, products, prices, raw rows, and
    ingestion history were created.
12. A troubleshooting table distinguishing admin login, authorization,
    connection, server-response, and empty-catalog failures.

The walkthrough must reference `docs/deployment.md` for production secret
storage and must never contain usable credentials.

## Error and Safety Rules

- Do not print or commit `SECRET_KEY`, `SCRAPER_API_KEY`, database passwords, or
  superuser passwords.
- Do not automatically create a superuser during normal application startup.
- Do not seed production data implicitly during migrations.
- Do not delete or overwrite the user's local PostgreSQL database.
- Do not restore the currently deleted `backend/.env.example` in this change.
- Do not rewrite Git history.

## Acceptance Criteria

1. A `401/403` during basket initialization displays `Session expired`, not
   `Backend offline`.
2. A connection failure displays `Backend offline`.
3. A non-authentication HTTP failure displays `Backend error`.
4. Recovery actions match the error category.
5. Tests cover all error categories and the full Flutter suite passes.
6. `walkthrough.md` accurately documents PostgreSQL port `5433`, migrations,
   superuser creation/reset, scraper ingestion, count verification, and stale
   token recovery.
7. No credentials are added to tracked files.
8. The existing `backend/.env.example` deletion remains untouched.

## Non-Goals

- Deploying PostgreSQL or Django to a remote host.
- Automatically running the scraper or creating a superuser.
- Restoring the old SQLite users or copying data between databases.
- Changing scraper matching algorithms.
- Implementing background health monitoring.
