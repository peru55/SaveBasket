# SaveBasket Deployment Configuration

This guide describes the security configuration required before deploying the
Django API and Flutter web client. Never commit populated `.env` files, working
passwords, or secret values.

## 1. Generate separate secrets

Generate a Django secret key from the backend virtual environment:

```powershell
cd backend
.\.venv\Scripts\python.exe -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

Generate a separate scraper API key:

```powershell
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

Do not reuse either value. Use different Django keys for development, staging,
and production. Generate each value once per environment; do not generate a new
key every time the application starts.

## 2. Configure the Django backend

Local development values may be placed in the ignored `backend/.env` file.
Production values belong in the hosting provider's environment-variable or
secret settings.

| Variable | Production requirement |
| --- | --- |
| `DEBUG` | Must be `False`. |
| `SECRET_KEY` | Required random Django key. |
| `ALLOWED_HOSTS` | Comma-separated API hostnames, without schemes. |
| `CORS_ALLOWED_ORIGINS` | Comma-separated HTTPS Flutter web origins. |
| `SCRAPER_API_KEY` | Required random key dedicated to scraper ingestion. |
| `DB_NAME` | PostgreSQL database name. |
| `DB_USER` | PostgreSQL user. |
| `DB_PASSWORD` | PostgreSQL password. |
| `DB_HOST` | PostgreSQL hostname; setting this selects PostgreSQL. |
| `DB_PORT` | PostgreSQL port, normally `5432`. |

Example structure with placeholders only:

```env
DEBUG=False
SECRET_KEY=<generated-django-secret>
ALLOWED_HOSTS=api.example.com
CORS_ALLOWED_ORIGINS=https://app.example.com
SCRAPER_API_KEY=<generated-scraper-key>
DB_NAME=savebasket
DB_USER=savebasket
DB_PASSWORD=<database-password>
DB_HOST=<database-host>
DB_PORT=5432
```

With `DEBUG=False`, Django refuses to start if `SECRET_KEY`, `ALLOWED_HOSTS`,
`CORS_ALLOWED_ORIGINS`, or `SCRAPER_API_KEY` is missing.

## 3. Configure scraper ingestion

The scraper sends the dedicated key in this header:

```http
X-SCRAPER-KEY: <value matching SCRAPER_API_KEY>
```

The backend rejects missing or invalid production keys before creating
ingestion, supermarket, branch, product, or price records.

In GitHub, open:

`Repository → Settings → Secrets and variables → Actions`

Create these repository secrets:

- `SCRAPER_BACKEND_URL`: the deployed backend origin, such as
  `https://api.example.com`.
- `SCRAPER_API_KEY`: the same scraper key stored by the backend host.

The Django `SECRET_KEY` is not needed by `ci_runner` and must not be copied into
GitHub Actions for the scraper workflow.

## 4. Build the Flutter web client

Release builds require an injected HTTPS backend origin:

```powershell
cd frontend
flutter build web --release --dart-define=API_BASE_URL=https://api.example.com
```

Authentication requests use `<API_BASE_URL>/api/auth/...`; catalog and basket
requests use `<API_BASE_URL>/api/...`. Local development defaults remain
available only in non-release builds.

Android release builds now include internet permission. Android keystore
creation and store signing are intentionally deferred until the mobile-release
phase.

## 5. Verify before deployment

Backend:

```powershell
cd backend
.\.venv\Scripts\python.exe manage.py test
.\.venv\Scripts\python.exe manage.py makemigrations --check --dry-run
.\.venv\Scripts\python.exe manage.py check --deploy
.\.venv\Scripts\python.exe -m pip check
```

Run `check --deploy` with the production-like variables from section 2 set in
the current shell.

Frontend:

```powershell
cd frontend
flutter analyze
flutter test
flutter build web --release --dart-define=API_BASE_URL=https://api.example.com
rg -n "localhost:8000|10\.0\.2\.2:8000" build/web
```

The final `rg` command must return no matches.

## 6. Previously exposed credential

A working credential was previously committed to `walkthrough.md` and pushed to
GitHub. Removing it from the current file does not remove it from existing Git
history.

Required action:

1. Rotate or delete the affected account credential immediately.
2. Confirm the replacement credential exists only in an approved password or
   secret manager.
3. Review access logs where available.

Optional history remediation requires a coordinated history rewrite using a
tool such as `git filter-repo`, followed by a force-push. This disrupts existing
clones and branches. Do not perform it until every collaborator is notified and
the repository owner explicitly authorizes the force-push.
