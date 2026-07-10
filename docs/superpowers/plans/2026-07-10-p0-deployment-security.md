# SaveBasket P0 Deployment Security Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Remove SaveBasket's P0 authorization, secret-handling, scraper-authentication, and release-client configuration blockers for a web-first deployment.

**Architecture:** Django defaults to authenticated access, then explicitly opens catalog reads through a reusable staff-write permission. Basket ownership is enforced by the viewset queryset, production configuration is validated in one helper module, and scraper ingestion fails closed. Flutter uses one testable API-origin module driven by `--dart-define`.

**Tech Stack:** Django 5, Django REST Framework, SimpleJWT, django-cors-headers, Flutter/Dart, Django TestCase/APIClient, flutter_test.

## Global Constraints

- Target web deployment first; Android store signing remains deferred.
- Preserve anonymous catalog reads and authenticated basket behavior.
- Never reveal or commit real `SECRET_KEY` or `SCRAPER_API_KEY` values.
- Add concise helper comments at security-sensitive paths and keep operational detail in `docs/deployment.md`.
- Follow red-green-refactor for every behavior change.
- Do not rewrite or force-push Git history without separate explicit approval.
- Preserve unrelated working-tree files.

---

## File Map

- Create `backend/savebasket/permissions.py`: reusable catalog read/staff-write policy.
- Create `backend/supermarkets/tests_permissions.py`: supermarket and branch authorization tests.
- Create `backend/products/tests_permissions.py`: product and price authorization tests.
- Modify `backend/savebasket/settings.py`: authenticated default, production validation, and explicit CORS configuration.
- Modify `backend/supermarkets/views.py`: apply catalog permission.
- Modify `backend/products/views.py`: apply catalog permission and fail-closed scraper authentication.
- Create `backend/baskets/tests_permissions.py`: basket ownership integration tests.
- Modify `backend/baskets/views.py`: owner-scoped queryset and simplified creation.
- Create `backend/savebasket/config.py`: pure environment parsing and production validation helpers.
- Create `backend/users/tests_settings.py`: production configuration tests.
- Create `backend/products/tests_ingest_security.py`: scraper-key tests.
- Create `frontend/lib/config/api_config.dart`: single API-origin interface.
- Create `frontend/test/api_config_test.dart`: URL-resolution tests.
- Modify `frontend/lib/services/api_service.dart`: consume `ApiConfig.apiBaseUrl`.
- Modify `frontend/lib/services/auth_service.dart`: consume `ApiConfig.origin`.
- Modify `frontend/android/app/src/main/AndroidManifest.xml`: release internet permission.
- Modify `backend/.env.example`: safe documented configuration contract.
- Create `docs/deployment.md`: web build, backend variables, scraper header, and credential-remediation guide.
- Modify `walkthrough.md`: remove the exposed credential from the current revision.
- Modify `backend/users/tests.py`: replace the rejected common test password.
- Move the import-time manual HTTP check out of Django test discovery.
- Modify `frontend/test/widget_test.dart` and `frontend/lib/screens/login_screen.dart` only as needed to restore the existing smoke test and narrow-layout behavior.

---

### Task 1: Secure catalog permission interface

**Files:**
- Create: `backend/savebasket/permissions.py`
- Create: `backend/supermarkets/tests_permissions.py`
- Create: `backend/products/tests_permissions.py`
- Modify: `backend/savebasket/settings.py`
- Modify: `backend/supermarkets/views.py`
- Modify: `backend/products/views.py`

**Interfaces:**
- Produces: `IsAdminOrReadOnly.has_permission(request, view) -> bool`.
- Policy: safe HTTP methods are public; unsafe methods require `request.user.is_authenticated and request.user.is_staff`.

- [ ] **Step 1: Write failing supermarket and branch permission tests**

Create endpoint tests that build an anonymous client, a normal authenticated user, and a staff user. For both `/api/supermarkets/` and `/api/branches/`, assert anonymous GET is `200`, anonymous POST is `401` or `403`, normal-user POST is `403`, and staff POST succeeds with `201`.

```python
class CatalogPermissionTests(TestCase):
    def test_normal_user_cannot_create_supermarket(self):
        self.client.force_authenticate(self.user)
        response = self.client.post("/api/supermarkets/", {"name": "Blocked"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
```

- [ ] **Step 2: Write failing product and price permission tests**

Create the required supermarket, branch, and product fixtures. Assert public GETs remain `200`, normal-user writes return `403`, and staff writes reach serializer validation or succeed with valid payloads.

- [ ] **Step 3: Run the new tests and verify RED**

Run:

```powershell
cd backend
.\.venv\Scripts\python.exe manage.py test supermarkets.tests_permissions products.tests_permissions -v 2
```

Expected: failures showing anonymous or non-staff catalog writes are currently allowed.

- [ ] **Step 4: Implement the minimal permission class and apply it**

```python
from rest_framework.permissions import BasePermission, SAFE_METHODS


class IsAdminOrReadOnly(BasePermission):
    """Expose catalog reads publicly while reserving mutations for staff."""

    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return True
        return bool(request.user and request.user.is_authenticated and request.user.is_staff)
```

Set `DEFAULT_PERMISSION_CLASSES` to `IsAuthenticated`, then explicitly apply `IsAdminOrReadOnly` to supermarket, branch, product, and price viewsets.

- [ ] **Step 5: Run permission tests and verify GREEN**

Run the Task 1 test command. Expected: all new catalog permission tests pass.

- [ ] **Step 6: Commit Task 1**

```powershell
git add backend/savebasket/permissions.py backend/savebasket/settings.py backend/supermarkets/views.py backend/supermarkets/tests_permissions.py backend/products/views.py backend/products/tests_permissions.py
git commit -m "fix: restrict catalog writes to staff"
```

---

### Task 2: Enforce basket ownership

**Files:**
- Create: `backend/baskets/tests_permissions.py`
- Modify: `backend/baskets/views.py`

**Interfaces:**
- Consumes: DRF `IsAuthenticated` default and existing basket router actions.
- Produces: `BasketViewSet.get_queryset()` containing only `request.user.baskets`.

- [ ] **Step 1: Write failing list and detail isolation tests**

Create two users, one basket per user, and authenticated clients. Assert each list contains only its owner's basket and User B receives `404` for User A's detail endpoint.

- [ ] **Step 2: Write failing custom-action isolation tests**

For User B targeting User A's basket, assert `404` from:

```text
POST /api/baskets/<id>/add_item/
POST /api/baskets/<id>/remove_item/
POST /api/baskets/<id>/update_item_quantity/
GET  /api/baskets/<id>/compare/
PUT  /api/baskets/<id>/
DELETE /api/baskets/<id>/
```

- [ ] **Step 3: Run ownership tests and verify RED**

```powershell
cd backend
.\.venv\Scripts\python.exe manage.py test baskets.tests_permissions -v 2
```

Expected: User B can currently see or act on User A's basket.

- [ ] **Step 4: Implement owner-scoped queryset**

```python
def get_queryset(self):
    # Owner scoping protects detail and custom actions through get_object().
    return self.request.user.baskets.all().order_by("-created_at")

def perform_create(self, serializer):
    serializer.save(user=self.request.user)
```

- [ ] **Step 5: Run ownership and existing basket tests**

```powershell
.\.venv\Scripts\python.exe manage.py test baskets -v 2
```

Expected: all basket tests pass.

- [ ] **Step 6: Commit Task 2**

```powershell
git add backend/baskets/views.py backend/baskets/tests_permissions.py
git commit -m "fix: scope baskets to their owners"
```

---

### Task 3: Fail closed in production and require scraper identity

**Files:**
- Create: `backend/savebasket/config.py`
- Create: `backend/users/tests_settings.py`
- Create: `backend/products/tests_ingest_security.py`
- Modify: `backend/savebasket/settings.py`
- Modify: `backend/products/views.py`
- Modify: `backend/.env.example`

**Interfaces:**
- Produces: `split_env_list(value: str | None) -> list[str]`.
- Produces: `validate_production_settings(debug: bool, values: dict[str, object]) -> None` raising `ImproperlyConfigured` with missing key names.
- Scraper contract: `X-SCRAPER-KEY` must equal `settings.SCRAPER_API_KEY` whenever production-like settings are active.

- [ ] **Step 1: Write failing pure configuration tests**

Test that development accepts omitted production variables, production rejects each missing variable, whitespace-only list settings count as missing, and exception messages list key names but not values.

```python
with self.assertRaisesMessage(ImproperlyConfigured, "SCRAPER_API_KEY"):
    validate_production_settings(False, {"SECRET_KEY": "x", "ALLOWED_HOSTS": ["example.com"], "SCRAPER_API_KEY": "", "CORS_ALLOWED_ORIGINS": ["https://app.example.com"]})
```

- [ ] **Step 2: Write failing scraper-key endpoint tests**

Using `override_settings(DEBUG=False, SCRAPER_API_KEY=...)`, assert missing and invalid headers return `403` and create no `IngestionHistory`, `RawScrapedProduct`, `Supermarket`, or `Branch` rows. Assert a valid key accepts a minimal valid payload.

- [ ] **Step 3: Run configuration and ingestion tests and verify RED**

```powershell
cd backend
.\.venv\Scripts\python.exe manage.py test users.tests_settings products.tests_ingest_security -v 2
```

Expected: helper imports fail and missing production scraper keys do not fail closed.

- [ ] **Step 4: Implement configuration helpers and settings wiring**

Parse comma-separated hosts/origins with trimming and empty-item removal. Keep a development-only secret fallback. Call `validate_production_settings()` after reading `SECRET_KEY`, `ALLOWED_HOSTS`, `SCRAPER_API_KEY`, and `CORS_ALLOWED_ORIGINS`.

```python
if DEBUG:
    CORS_ALLOW_ALL_ORIGINS = True
else:
    CORS_ALLOW_ALL_ORIGINS = False
    CORS_ALLOWED_ORIGINS = split_env_list(os.getenv("CORS_ALLOWED_ORIGINS"))
```

Add helper comments pointing to `docs/deployment.md` and never include secret values in exceptions.

- [ ] **Step 5: Implement fail-closed scraper authentication**

Reject missing keys when `DEBUG=False`; validate configured keys in both environments; preserve keyless local development only when `DEBUG=True`.

- [ ] **Step 6: Update the safe environment example**

Document `DEBUG`, `SECRET_KEY`, `ALLOWED_HOSTS`, `CORS_ALLOWED_ORIGINS`, `SCRAPER_API_KEY`, and database variables with placeholders rather than usable credentials.

- [ ] **Step 7: Run Task 3 tests and Django deployment checks**

```powershell
.\.venv\Scripts\python.exe manage.py test users.tests_settings products.tests_ingest_security -v 2
$env:DEBUG='False'
$env:SECRET_KEY='test-only-long-random-placeholder-value-for-checks'
$env:ALLOWED_HOSTS='api.example.com'
$env:CORS_ALLOWED_ORIGINS='https://app.example.com'
$env:SCRAPER_API_KEY='test-only-scraper-key'
.\.venv\Scripts\python.exe manage.py check --deploy
```

Expected: tests pass; only deployment warnings explicitly outside this tranche may remain.

- [ ] **Step 8: Commit Task 3**

```powershell
git add backend/savebasket/config.py backend/savebasket/settings.py backend/users/tests_settings.py backend/products/views.py backend/products/tests_ingest_security.py backend/.env.example
git commit -m "fix: fail closed for production secrets"
```

---

### Task 4: Centralize the Flutter API origin

**Files:**
- Create: `frontend/lib/config/api_config.dart`
- Create: `frontend/test/api_config_test.dart`
- Modify: `frontend/lib/services/api_service.dart`
- Modify: `frontend/lib/services/auth_service.dart`
- Modify: `frontend/android/app/src/main/AndroidManifest.xml`

**Interfaces:**
- Produces: `ApiConfig.resolveOrigin({String configured, bool isWeb, bool isAndroid}) -> String`.
- Produces: `ApiConfig.origin` and `ApiConfig.apiBaseUrl` getters.

- [ ] **Step 1: Write failing API configuration tests**

```dart
test('normalizes an injected production origin', () {
  expect(
    ApiConfig.resolveOrigin(
      configured: 'https://api.example.com/',
      isWeb: true,
      isAndroid: false,
    ),
    'https://api.example.com',
  );
});
```

Also test empty configured values for web (`localhost`) and Android emulator (`10.0.2.2`).

- [ ] **Step 2: Run the focused Flutter test and verify RED**

```powershell
cd frontend
flutter test test/api_config_test.dart
```

Expected: import or symbol failure because `ApiConfig` does not exist.

- [ ] **Step 3: Implement `ApiConfig` minimally**

Use `const String.fromEnvironment('API_BASE_URL')`, remove trailing slashes, and include a helper comment with the exact production flag:

```text
--dart-define=API_BASE_URL=https://api.example.com
```

- [ ] **Step 4: Replace duplicated URL getters**

`AuthService` uses `ApiConfig.origin`; `ApiService` uses `ApiConfig.apiBaseUrl`. Remove direct `dart:io` and `kIsWeb` imports from both service files.

- [ ] **Step 5: Add Android release internet permission**

Add `<uses-permission android:name="android.permission.INTERNET"/>` to the main manifest with a concise release-build helper comment.

- [ ] **Step 6: Run focused tests, analysis, and a production web build**

```powershell
flutter test test/api_config_test.dart
flutter analyze
flutter build web --release --dart-define=API_BASE_URL=https://api.example.com
rg -n "localhost:8000|10\.0\.2\.2:8000" build/web
```

Expected: tests and analysis pass; build succeeds; `rg` returns no matches.

- [ ] **Step 7: Commit Task 4**

```powershell
git add frontend/lib/config/api_config.dart frontend/test/api_config_test.dart frontend/lib/services/api_service.dart frontend/lib/services/auth_service.dart frontend/android/app/src/main/AndroidManifest.xml
git commit -m "fix: inject the frontend API origin"
```

---

### Task 5: Remove credential exposure and document deployment

**Files:**
- Modify: `walkthrough.md`
- Create: `docs/deployment.md`

**Interfaces:**
- Documentation consumes the environment and build contracts created in Tasks 3 and 4.

- [ ] **Step 1: Remove credential-bearing lines from the current walkthrough**

Replace the credential block with a short statement that test credentials must never be documented or committed. Do not reproduce any previous values.

- [ ] **Step 2: Write the deployment guide**

Document:

- Generating separate Django and scraper keys.
- Backend environment-variable names and example placeholders.
- GitHub Actions `SCRAPER_BACKEND_URL` and `SCRAPER_API_KEY` configuration paths.
- `X-SCRAPER-KEY` request behavior.
- Flutter web build command with `API_BASE_URL`.
- Android signing explicitly deferred.
- Credential rotation as mandatory because the repository was pushed.
- Optional history rewriting as a separately authorized, coordinated force-push operation.
- Verification commands from the design.

- [ ] **Step 3: Verify no current tracked credential markers remain**

```powershell
git grep -n -I -E "Password:|DJANGO_SUPERUSER_PASSWORD|django-insecure-" -- ':!docs/superpowers/**'
```

Expected: no real credential values in tracked operational documentation or production settings; safe explanatory references may remain.

- [ ] **Step 4: Commit Task 5**

```powershell
git add walkthrough.md docs/deployment.md
git commit -m "docs: add secure deployment configuration guide"
```

---

### Task 6: Restore deterministic test discovery and smoke tests

**Files:**
- Modify: `backend/users/tests.py`
- Remove from discovery: `backend/test_register.py`
- Create: `backend/scripts/register_manual_check.py`
- Modify: `frontend/test/widget_test.dart`
- Modify: `frontend/lib/screens/login_screen.dart` only if the narrow layout still overflows.

**Interfaces:**
- Backend test discovery performs no live network calls.
- The frontend smoke test asserts current visible application behavior at a realistic viewport.

- [ ] **Step 1: Update the registration test password**

Use a strong, non-common test password such as `S4veBasket-Test-Only!2026` so the test exercises successful registration under the configured validators.

- [ ] **Step 2: Move the manual HTTP script out of test discovery**

Preserve it as `backend/scripts/register_manual_check.py`, add a `main()` guard, and use an environment-configurable base URL. Delete `backend/test_register.py` from the test-discovery path.

- [ ] **Step 3: Write or adjust the frontend regression expectation**

Set an explicit narrow surface size and assert the actual login title or distinctive login control. Run the test to reproduce the current overflow before changing layout production code.

- [ ] **Step 4: Fix the narrow login row only if RED confirms overflow**

Replace the overflowing horizontal content with a `Wrap`, `Flexible`, or responsive arrangement that preserves the current copy and controls.

- [ ] **Step 5: Run backend and frontend suites**

```powershell
cd backend
.\.venv\Scripts\python.exe manage.py test
cd ..\frontend
flutter test
```

Expected: both suites pass with no import-time network calls or render overflow.

- [ ] **Step 6: Commit Task 6**

```powershell
git add backend/users/tests.py backend/test_register.py backend/scripts/register_manual_check.py frontend/test/widget_test.dart frontend/lib/screens/login_screen.dart
git commit -m "test: restore deterministic release checks"
```

---

### Task 7: Full verification and issue mapping

**Files:**
- Modify only if verification exposes an implementation defect covered by the approved design.

**Interfaces:**
- Produces evidence that GitHub issues #3, #4, #5, and #6 meet their acceptance criteria.

- [ ] **Step 1: Run complete backend verification**

```powershell
cd backend
.\.venv\Scripts\python.exe manage.py test
.\.venv\Scripts\python.exe manage.py makemigrations --check --dry-run
$env:DEBUG='False'
$env:SECRET_KEY='test-only-long-random-placeholder-value-for-checks'
$env:ALLOWED_HOSTS='api.example.com'
$env:CORS_ALLOWED_ORIGINS='https://app.example.com'
$env:SCRAPER_API_KEY='test-only-scraper-key'
.\.venv\Scripts\python.exe manage.py check --deploy
.\.venv\Scripts\python.exe -m pip check
```

- [ ] **Step 2: Run complete frontend verification**

```powershell
cd frontend
flutter analyze
flutter test
flutter build web --release --dart-define=API_BASE_URL=https://api.example.com
rg -n "localhost:8000|10\.0\.2\.2:8000" build/web
```

- [ ] **Step 3: Verify repository safety and scope**

```powershell
git diff --check
git status --short
git diff main...HEAD --stat
```

Expected: no whitespace errors, only approved files changed, and no generated build artifacts staged.

- [ ] **Step 4: Review acceptance criteria issue by issue**

Record evidence for #3, #4, #5, and #6 in the final handoff. Do not close GitHub issues unless the user separately asks for that write action.
