# SaveBasket P0 Deployment Security Design

**Date:** 2026-07-10

**Status:** Approved for implementation planning

**Target:** Web-first deployment; Android store signing is deferred

## Goal

Remove the security and configuration blockers that prevent SaveBasket from being safely deployed as a Django API with a Flutter web client.

## Scope

This tranche implements the repository's explicit P0 issues and the additional client/configuration blockers found during deployment review:

- GitHub issue #3: lock down DRF default permissions.
- GitHub issue #4: enforce basket object ownership.
- GitHub issue #5: protect supermarket and branch write operations.
- GitHub issue #6: require the scraper API key in production.
- Remove the tracked credential from `walkthrough.md` and document rotation/history remediation.
- Replace duplicated frontend localhost URLs with one build-time API configuration module.
- Make production secrets, hosts, scraper authentication, and CORS configuration fail closed.
- Add Android release internet permission while deferring release signing.

The following existing issues remain outside this tranche: image-proxy allowlisting/SSRF hardening (#7), rate limiting (#8), scraper payload validation (#9), product/price audit logging (#11), and broader operational hardening. Product and price writes are restricted to staff because that is required for a safe public deployment and is already described by issue #10.

## Architecture

### Access-control policy

The Django REST Framework global default permission becomes `IsAuthenticated`. Public interfaces are explicit rather than inherited:

- Registration and JWT token endpoints remain public.
- Products, prices, supermarkets, and branches allow anonymous reads.
- Catalog create, update, partial update, and delete operations require a staff user.
- Basket interfaces require authentication and only query baskets owned by `request.user`.
- Basket detail operations and custom actions inherit ownership enforcement from the owner-scoped queryset. A different user's UUID therefore resolves as `404`.
- Scraper ingestion requires a valid `X-SCRAPER-KEY` whenever `DEBUG=False`.

A reusable `IsAdminOrReadOnly` permission class owns the catalog policy. This keeps the policy testable through one interface and prevents permission behavior from drifting between viewsets.

### Production configuration

Development remains convenient, but production fails closed:

- `DEBUG` may default to `True` for local development.
- When `DEBUG=False`, `SECRET_KEY` must be supplied and may not use the development fallback.
- When `DEBUG=False`, `ALLOWED_HOSTS`, `SCRAPER_API_KEY`, and `CORS_ALLOWED_ORIGINS` must be non-empty.
- Production uses explicit `CORS_ALLOWED_ORIGINS`; `CORS_ALLOW_ALL_ORIGINS` is allowed only in development.
- Startup errors identify the missing variable without printing secret values.

`backend/.env.example` contains safe placeholders and clearly separates local values from production requirements. `docs/deployment.md` explains each variable, including this scraper contract:

```http
X-SCRAPER-KEY: <value matching SCRAPER_API_KEY>
```

Short helper comments are placed next to fail-closed checks in `backend/savebasket/settings.py` and `backend/products/views.py`. The comments explain why the rule exists and point to `docs/deployment.md`; they do not duplicate the full operational guide.

### Frontend API configuration

One frontend module owns the backend origin:

- It reads `API_BASE_URL` using `String.fromEnvironment`.
- A supplied value is normalized by removing trailing slashes.
- Local web and desktop development default to `http://localhost:8000`.
- Local Android emulator development defaults to `http://10.0.2.2:8000`.
- Authentication builds URLs below the configured origin, such as `/api/auth/token/`.
- Application calls build URLs below `<origin>/api`.
- Web release documentation requires `--dart-define=API_BASE_URL=https://api.example.com`.
- A release verification step scans the compiled artifact and fails if localhost remains when a production URL was supplied.

`frontend/android/app/src/main/AndroidManifest.xml` receives `android.permission.INTERNET`, making network access available to Android release builds. Keystore creation and store signing remain explicitly deferred.

### Credential remediation

The exposed credential is removed from the current version of `walkthrough.md`. Because it has already been pushed to GitHub:

1. The associated account/password must be rotated immediately outside the repository.
2. `docs/deployment.md` records the incident-remediation step without reproducing the credential.
3. Git-history rewriting is documented as an optional coordinated operation using an appropriate history-filtering tool.
4. No automatic force-push is performed as part of implementation because it would rewrite collaborators' history and requires explicit authorization.

Ignoring or untracking `walkthrough.md` is not treated as credential remediation: the file is currently tracked, and prior commits remain available on GitHub until history is rewritten.

## Error Behavior

- Production configuration errors stop Django startup and name only the missing configuration key.
- Unauthenticated access to protected interfaces returns `401` or the authentication backend's equivalent response.
- Authenticated non-staff catalog writes return `403`.
- A request for another user's basket returns `404`, including custom basket actions.
- Missing or invalid scraper keys return `403` before any ingestion, history, product, price, supermarket, or branch row is created.
- Public catalog reads preserve current response behavior.

## Helper Comments and Documentation Paths

Helper comments are required where behavior would otherwise look unnecessarily strict:

- `backend/savebasket/settings.py`: explain the production fail-closed checks and reference `docs/deployment.md`.
- `backend/products/views.py`: explain why ingestion rejects a missing key in production and reference `backend/.env.example`.
- `backend/baskets/views.py`: explain that owner scoping supplies object-level protection for all viewset actions.
- `frontend/lib/config/api_config.dart`: explain the `--dart-define` contract and include the exact production build flag.
- `frontend/android/app/src/main/AndroidManifest.xml`: note that the permission is required by release builds, not just debug/profile builds.

Long-form material belongs in:

- `docs/deployment.md`: environment variables, build command, scraper header, credential rotation note, and verification commands.
- `backend/.env.example`: safe environment-variable examples only.

Comments must explain intent, not restate the following line of code, and must never contain real credentials.

## Test Strategy

Implementation follows red-green-refactor. Each behavior is first represented by a failing test.

### Backend tests

- Assert the global permission default is authenticated.
- Assert anonymous catalog list/detail reads succeed.
- Assert anonymous catalog writes fail.
- Assert a normal authenticated user cannot write catalog data.
- Assert a staff user can write catalog data.
- Create two users and verify basket list responses contain only the current user's baskets.
- Verify the second user receives `404` for the first user's detail, update, delete, add-item, remove-item, update-quantity, and compare interfaces.
- Under production-like settings, verify missing and invalid scraper keys return `403` and create no database rows.
- Verify a valid scraper key preserves successful ingestion.
- Verify production settings reject each required variable when it is absent.
- Repair the existing registration test data so it uses a password accepted by Django's configured validators.
- Convert or exclude the import-time live HTTP script so Django test discovery never performs network calls.

### Frontend tests

- Verify an injected API origin is normalized and used by both auth and application URL builders.
- Verify local web and Android emulator development defaults.
- Keep API URL selection independent of HTTP calls so it can be tested without network mocks.
- Run Flutter analysis and existing widget tests; the known login overflow/stale smoke expectation may be fixed only as required to restore the mandated green suite.

### Release verification

- `python manage.py test` passes.
- Production-like `python manage.py check --deploy` has no unresolved warnings covered by this P0 scope.
- `python manage.py makemigrations --check --dry-run` reports no changes.
- `flutter analyze` passes.
- `flutter test` passes.
- `flutter build web --release --dart-define=API_BASE_URL=https://api.example.com` succeeds.
- The compiled web artifact contains the supplied HTTPS origin and does not contain `localhost:8000`.

## Acceptance Criteria

1. GitHub issues #3, #4, #5, and #6 meet their stated acceptance criteria.
2. Anonymous users can read intended catalog interfaces but cannot write any catalog resource.
3. Normal authenticated users cannot write catalog resources or access another user's baskets.
4. Staff users retain catalog administration through the API.
5. Production-like startup refuses missing critical configuration.
6. Scraper ingestion cannot run without the configured production key.
7. A production Flutter web build communicates only with the injected HTTPS backend origin.
8. Android release builds include internet permission; store signing remains documented as deferred.
9. The exposed credential no longer appears in the current tracked walkthrough, and rotation/history-remediation steps are documented without revealing it.
10. Helper comments and `docs/deployment.md` make each non-obvious security decision discoverable from the relevant code path.
11. Backend and frontend verification suites pass before the tranche is considered complete.

## Non-Goals

- Deploying to Render or another host in this tranche.
- Rewriting and force-pushing Git history without separate explicit approval.
- Creating or storing an Android signing keystore.
- Implementing geolocation issue #2.
- Fixing scraper data-source correctness or Carrefour availability from issue #1.
- Completing rate limiting, audit logging, comprehensive ingestion validation, or full image-proxy SSRF hardening.
