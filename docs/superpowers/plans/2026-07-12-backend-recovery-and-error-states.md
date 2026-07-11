# SaveBasket Backend Recovery and Error States Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Distinguish stale authentication, network outages, and backend response failures in Flutter, then document verified PostgreSQL 5433 admin and scraper recovery workflows.

**Architecture:** `ApiService` will preserve request failure semantics through a typed `ApiException` and injectable HTTP/auth dependencies. `BasketProvider` will expose a categorized recovery state consumed by the dashboard, while `walkthrough.md` records the verified PostgreSQL, superuser, scraper, and stale-token procedures.

**Tech Stack:** Flutter/Dart, package:http, Provider, flutter_test, Django 5, Django ORM, PostgreSQL.

## Global Constraints

- Follow red-green-refactor for every frontend behavior change.
- Never print or commit `SECRET_KEY`, `SCRAPER_API_KEY`, database passwords, superuser passwords, or JWTs.
- Do not automatically create a superuser during application startup.
- Do not seed data implicitly during migrations.
- Do not alter or delete the local PostgreSQL database.
- Leave the existing deletion of `backend/.env.example` untouched.
- Keep the walkthrough aligned with PostgreSQL at `127.0.0.1:5433`.

---

## File Map

- Create `frontend/lib/services/api_exception.dart`: typed request failure and category.
- Create `frontend/test/api_service_error_test.dart`: HTTP and connection classification tests.
- Modify `frontend/lib/services/api_service.dart`: dependency injection and typed basket-creation failures.
- Create `frontend/test/basket_provider_error_test.dart`: provider state mapping tests.
- Modify `frontend/lib/providers/basket_provider.dart`: categorized error state and injectable service.
- Modify `frontend/lib/screens/home_screen.dart`: category-specific title, icon, copy, and recovery action.
- Modify `frontend/test/widget_test.dart` only if required to cover the new recovery presentation without brittle full-app setup.
- Modify `walkthrough.md`: dated current-state and recovery guide.

---

### Task 1: Preserve API failure semantics

**Files:**
- Create: `frontend/lib/services/api_exception.dart`
- Create: `frontend/test/api_service_error_test.dart`
- Modify: `frontend/lib/services/api_service.dart`

**Interfaces:**
- Produces: `enum ApiErrorKind { authentication, connection, server }`.
- Produces: `ApiException(kind, message, {int? statusCode, Object? cause})`.
- Produces: `ApiService({http.Client? client, AuthService? authService})`.

- [ ] **Step 1: Write failing exception-classification tests**

Use `MockClient` from `package:http/testing.dart` and a test `AuthService`
subclass that returns no token and does not refresh. Assert:

```dart
expect(
  () => service.createBasket('Test'),
  throwsA(isA<ApiException>()
    .having((e) => e.kind, 'kind', ApiErrorKind.authentication)
    .having((e) => e.statusCode, 'statusCode', 401)),
);
```

Cover final `401`, final `403`, HTTP `500`, and `http.ClientException` before a
response. The `201` test returns a minimal valid basket JSON object.

- [ ] **Step 2: Run tests and verify RED**

```powershell
cd frontend
flutter test test/api_service_error_test.dart
```

Expected: import/symbol failures because `ApiException`, dependency injection,
and typed classification do not exist.

- [ ] **Step 3: Implement the typed exception**

```dart
enum ApiErrorKind { authentication, connection, server }

class ApiException implements Exception {
  final ApiErrorKind kind;
  final String message;
  final int? statusCode;
  final Object? cause;

  const ApiException(this.kind, this.message, {this.statusCode, this.cause});

  @override
  String toString() => message;
}
```

- [ ] **Step 4: Add injectable dependencies and classify create-basket outcomes**

Change the eager final fields to constructor-injected fields:

```dart
ApiService({http.Client? client, AuthService? authService})
    : _client = client ?? http.Client(),
      _auth = authService ?? AuthService();
```

Wrap `createBasket()` so `401/403` throws authentication, other non-`201`
responses throw server, and `http.ClientException`/`SocketException` throw
connection. Do not include response bodies or authorization values in messages.

- [ ] **Step 5: Run focused tests and verify GREEN**

```powershell
flutter test test/api_service_error_test.dart
flutter analyze
```

Expected: focused tests pass and analysis reports no issues.

- [ ] **Step 6: Commit Task 1**

```powershell
git add frontend/lib/services/api_exception.dart frontend/lib/services/api_service.dart frontend/test/api_service_error_test.dart
git commit -m "fix: classify backend request failures"
```

---

### Task 2: Map failures to recovery states

**Files:**
- Create: `frontend/test/basket_provider_error_test.dart`
- Modify: `frontend/lib/providers/basket_provider.dart`
- Modify: `frontend/lib/screens/home_screen.dart`

**Interfaces:**
- Consumes: `ApiErrorKind` and `ApiException` from Task 1.
- Produces: `BasketProvider({ApiService? apiService})`.
- Produces: `BackendErrorState? backendError` with `kind`, `title`, and `message`.

- [ ] **Step 1: Write failing provider mapping tests**

Create a test `ApiService` subclass whose `createBasket` throws a supplied
exception. Verify three independent cases:

```dart
await provider.initializeBasket();
expect(provider.backendError?.title, 'Session expired');
expect(provider.backendError?.kind, ApiErrorKind.authentication);
```

Connection maps to `Backend offline`; server maps to `Backend error`.

- [ ] **Step 2: Run tests and verify RED**

```powershell
flutter test test/basket_provider_error_test.dart
```

Expected: constructor/state symbol failures because categorized provider state
does not exist.

- [ ] **Step 3: Implement the minimal provider state**

Add an immutable `BackendErrorState`, injectable `ApiService`, and a mapping
helper. Clear the state at the beginning of initialization and successful
completion. Preserve `errorMessage` as a compatibility getter if other screens
still consume it.

- [ ] **Step 4: Update the dashboard recovery card**

Use `provider.backendError` for the card. Render:

- authentication: `Session expired`, sign-in icon, `Sign in again` button that
  calls `context.read<AuthProvider>().logout()`;
- connection: `Backend offline`, cloud-off icon, `Reconnect` button;
- server: `Backend error`, warning icon, `Try again` button.

No raw exception, token, or response body appears in the UI.

- [ ] **Step 5: Run provider tests, full Flutter tests, and analysis**

```powershell
flutter test test/basket_provider_error_test.dart
flutter test
flutter analyze
```

Expected: all tests pass and analysis is clean.

- [ ] **Step 6: Commit Task 2**

```powershell
git add frontend/lib/providers/basket_provider.dart frontend/lib/screens/home_screen.dart frontend/test/basket_provider_error_test.dart frontend/test/widget_test.dart
git commit -m "fix: distinguish session and backend failures"
```

---

### Task 3: Document PostgreSQL, admin, scraper, and offline recovery

**Files:**
- Modify: `walkthrough.md`

**Interfaces:**
- Consumes: existing `docs/deployment.md`, `Scrapper/run_scraper.py`,
  `Scrapper/ci_runner.py`, and `Scrapper/sync_json_to_backend.py` contracts.

- [ ] **Step 1: Add a dated verified-current-state section**

Record PostgreSQL host `127.0.0.1`, port `5433`, applied migrations, running
Django port `8000`, and the observation that the database began empty. Use
placeholder values for database and secret fields.

- [ ] **Step 2: Add admin creation and reset commands**

Document the preferred interactive command:

```powershell
cd backend
.\.venv\Scripts\python.exe manage.py createsuperuser
```

Document `createsuperuser --noinput` as environment-driven creation only, and
document reset for an existing account:

```powershell
.\.venv\Scripts\python.exe manage.py changepassword <username>
```

Explain that changing databases requires recreating users and that environment
variables do not create accounts unless the command is run.

- [ ] **Step 3: Add scraper ingestion commands**

Document server startup, one-product push, batch job push, and saved-JSON push:

```powershell
cd backend
.\.venv\Scripts\python.exe manage.py runserver

cd ..\Scrapper
python run_scraper.py "PRODUCT_URL" --backend http://127.0.0.1:8000 --key YOUR_SCRAPER_API_KEY
python ci_runner.py --backend http://127.0.0.1:8000 --key YOUR_SCRAPER_API_KEY
python sync_json_to_backend.py --backend http://127.0.0.1:8000 --key YOUR_SCRAPER_API_KEY
```

Explain that the command-line key must match the backend's `SCRAPER_API_KEY`.

- [ ] **Step 4: Add safe verification and troubleshooting**

Include migration checks, port-listener checks, ORM record counts, and a table
covering nonexistent superuser, wrong password, stale JWT, connection failure,
server error, and empty catalog. Reference `docs/deployment.md` for secrets.

- [ ] **Step 5: Verify documentation safety**

```powershell
git diff --check
git grep -n -I -E "Password:|DJANGO_SUPERUSER_PASSWORD=|SECRET_KEY=" -- walkthrough.md
```

Expected: no usable credential values; only placeholder or command references.

- [ ] **Step 6: Commit Task 3**

```powershell
git add walkthrough.md
git commit -m "docs: update backend recovery walkthrough"
```

---

### Task 4: Full verification

**Files:**
- Modify only approved files if verification identifies a defect within scope.

- [ ] **Step 1: Run complete Flutter verification**

```powershell
cd frontend
flutter analyze
flutter test
flutter build web --release --dart-define=API_BASE_URL=https://api.example.com
```

- [ ] **Step 2: Run backend checks against local PostgreSQL**

```powershell
cd backend
.\.venv\Scripts\python.exe manage.py check
.\.venv\Scripts\python.exe manage.py showmigrations --plan
```

- [ ] **Step 3: Audit scope and repository state**

```powershell
git diff --check
git status --short
git diff main...HEAD --stat
git log --oneline main..HEAD
```

Expected: only approved frontend files and `walkthrough.md` differ from main;
`backend/.env.example` is not modified by the feature branch.
