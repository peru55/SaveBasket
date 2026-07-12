# Local CORS, Scraper Key, and Password Visibility Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make random-port Flutter web registration pass restricted local CORS, make `ci_runner.py` resolve the correct scraper key safely, and add accessible password visibility controls.

**Architecture:** Django will allow only localhost/127.0.0.1 development origins through regexes while retaining explicit production origins. The scraper runner will use deterministic CLI → process environment → ignored backend `.env` key precedence. Login and registration forms will own independent visibility state with tested accessible controls.

**Tech Stack:** Django 5, django-cors-headers, unittest/DRF test client, Python dotenv, Flutter/Dart, flutter_test.

## Global Constraints

- Never print, commit, or echo scraper, Django, database, or user secrets.
- Never allow arbitrary production CORS origins.
- Do not insert scraper data during tests.
- Preserve concurrent `.gitignore`, `Scrapper/ci_jobs.txt`, and `backend/.env.example` changes.
- Follow red-green-refactor for behavior changes.

---

### Task 1: Restrict local CORS by regex

**Files:**
- Create: `backend/users/tests_cors.py`
- Modify: `backend/savebasket/settings.py`

**Interfaces:**
- Produces development `CORS_ALLOWED_ORIGIN_REGEXES` for localhost and `127.0.0.1` numeric ports.
- Preserves production `CORS_ALLOWED_ORIGINS` environment configuration.

- [ ] **Step 1: Write failing CORS preflight tests**

Use Django's client to send `OPTIONS /api/auth/register/` with an origin and
`Access-Control-Request-Method: POST`. Assert a random localhost origin receives
the matching `Access-Control-Allow-Origin` header and `https://evil.example`
does not.

```python
response = self.client.options(
    "/api/auth/register/",
    HTTP_ORIGIN="http://localhost:52498",
    HTTP_ACCESS_CONTROL_REQUEST_METHOD="POST",
)
self.assertEqual(response["Access-Control-Allow-Origin"], "http://localhost:52498")
```

- [ ] **Step 2: Run RED**

```powershell
cd backend
& 'C:\Users\user\Desktop\Peru\school\ACS 400\SaveBasket\backend\.venv\Scripts\python.exe' manage.py test users.tests_cors -v 2
```

Expected: the unrelated origin is currently allowed under keyless DEBUG
settings, proving the policy is too broad.

- [ ] **Step 3: Implement environment-specific CORS settings**

Set `CORS_ALLOW_ALL_ORIGINS=False`. Under DEBUG set allowed origins to an empty
list and use regexes matching `http://localhost:<port>` and
`http://127.0.0.1:<port>`. Outside DEBUG parse explicit
`CORS_ALLOWED_ORIGINS` and leave regexes empty.

- [ ] **Step 4: Run GREEN and Django checks**

```powershell
& 'C:\Users\user\Desktop\Peru\school\ACS 400\SaveBasket\backend\.venv\Scripts\python.exe' manage.py test users.tests_cors -v 2
& 'C:\Users\user\Desktop\Peru\school\ACS 400\SaveBasket\backend\.venv\Scripts\python.exe' manage.py check
```

- [ ] **Step 5: Commit**

```powershell
git add backend/users/tests_cors.py backend/savebasket/settings.py
git commit -m "fix: allow restricted local Flutter origins"
```

---

### Task 2: Resolve scraper keys deterministically

**Files:**
- Create: `Scrapper/test_ci_runner_key.py`
- Modify: `Scrapper/ci_runner.py`
- Modify: `Scrapper/requirements.txt`

**Interfaces:**
- Produces `resolve_api_key(cli_key, environ=None, env_path=None) -> str | None`.
- Precedence: CLI, process `SCRAPER_API_KEY`, ignored `backend/.env`.

- [ ] **Step 1: Write failing key-resolution tests**

Test CLI precedence, process-environment fallback, temporary dotenv-file
fallback, and `None` when all sources are absent. Patch `build_payload_from_url`
and assert `main()` exits with parser error before scraping when backend push is
requested without a key.

- [ ] **Step 2: Run RED**

```powershell
cd Scrapper
python -m unittest test_ci_runner_key.py -v
```

Expected: `resolve_api_key` is missing and missing-key execution does not fail
early.

- [ ] **Step 3: Implement key resolution**

Add `python-dotenv` to requirements. Load only the key from the repository-local
`backend/.env` after checking CLI and process environment. Resolve the key once
before the job loop and pass it to `push_payload`. Call `parser.error` before
scraping when backend push has no key. Never print the value.

- [ ] **Step 4: Run GREEN and scraper suite**

```powershell
python -m unittest test_ci_runner_key.py -v
python -m unittest discover -s . -p "test_*.py"
```

- [ ] **Step 5: Commit**

```powershell
git add Scrapper/ci_runner.py Scrapper/requirements.txt Scrapper/test_ci_runner_key.py
git commit -m "fix: resolve scraper API key safely"
```

---

### Task 3: Add password visibility controls

**Files:**
- Create: `frontend/test/password_visibility_test.dart`
- Modify: `frontend/lib/screens/login_screen.dart`
- Modify: `frontend/lib/screens/register_screen.dart`

**Interfaces:**
- Login tooltips: `Show password` / `Hide password`.
- Registration confirmation tooltips: `Show password confirmation` /
  `Hide password confirmation`.

- [ ] **Step 1: Write failing widget tests**

Pump login and registration screens. Inspect `TextFormField.obscureText`, tap
the tooltip finder, pump, and assert the targeted field becomes visible while
the other registration password field remains obscured.

- [ ] **Step 2: Run RED**

```powershell
cd frontend
flutter test test/password_visibility_test.dart
```

Expected: tooltip finders return no widgets.

- [ ] **Step 3: Implement login toggle**

Add `_obscurePassword=true` state and an `IconButton` suffix with visibility
icon, tooltip, semantic label, and `setState` toggle.

- [ ] **Step 4: Implement independent registration toggles**

Add separate password and confirmation booleans and suffix buttons. Toggling
one must not change the other.

- [ ] **Step 5: Run GREEN, full Flutter tests, and analysis**

```powershell
flutter test test/password_visibility_test.dart
flutter test
flutter analyze
```

- [ ] **Step 6: Commit**

```powershell
git add frontend/lib/screens/login_screen.dart frontend/lib/screens/register_screen.dart frontend/test/password_visibility_test.dart
git commit -m "feat: add password visibility controls"
```

---

### Task 4: Update walkthrough and verify

**Files:**
- Modify: `walkthrough.md`

- [ ] **Step 1: Document local CORS behavior**

Explain random Flutter ports, allowed localhost regexes, Django restart, and a
safe preflight diagnostic.

- [ ] **Step 2: Document scraper key precedence and 403 recovery**

Show `python ci_runner.py --backend http://127.0.0.1:8000` as the preferred
local command and explain CLI overrides. Warn against literal placeholders and
document restarting Django after `.env` changes.

- [ ] **Step 3: Document password controls and registration validation**

Explain show/hide icons and Django's 8+ character/non-common/non-numeric rules.

- [ ] **Step 4: Run full verification**

```powershell
flutter analyze
flutter test
flutter build web --release --dart-define=API_BASE_URL=https://api.example.com
& 'C:\Users\user\Desktop\Peru\school\ACS 400\SaveBasket\backend\.venv\Scripts\python.exe' manage.py test
python -m unittest discover -s Scrapper -p "test_*.py"
git diff --check
git diff main...HEAD --stat
```

Confirm no feature diff for `.gitignore`, `Scrapper/ci_jobs.txt`, or
`backend/.env.example`.

- [ ] **Step 5: Commit walkthrough**

```powershell
git add walkthrough.md
git commit -m "docs: add local auth and scraper troubleshooting"
```
