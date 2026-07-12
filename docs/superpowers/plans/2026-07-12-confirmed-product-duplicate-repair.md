# Confirmed Product Duplicate Repair Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the two confirmed retailer name pairs converge on canonical products and safely repair the duplicate rows already in PostgreSQL.

**Architecture:** Product matching receives narrow canonicalization rules for Daawat spelling and Farmer's Choice/Safari sausage wording. A separate targeted repair service and dry-run-by-default management command merge only the two approved database pairs, including dependent store, price, basket, alias, and review records.

**Tech Stack:** Django 5, Django ORM transactions, Django management commands, `django.test.TestCase`.

## Global Constraints

- Keep `Farmer's Choice Safari Beef Sausage 500 Gm` as the canonical sausage.
- Keep `Daawat Long Grain Rice 5Kg` as the canonical rice.
- Do not lower global matching or review thresholds.
- Do not merge unrelated Safari, Farmer's Choice, Daawat, rice, or sausage products.
- Default the repair command to dry-run; require `--apply` for writes.
- Delete a duplicate only after all dependent records are resolved.
- Preserve all unrelated uncommitted workspace changes.

---

### Task 1: Canonicalize the confirmed retailer names

**Files:**
- Modify: `backend/products/match_service.py`
- Test: `backend/products/tests_services.py`

**Interfaces:**
- Produces: `ProductMatchService.canonical_brand("daawati") == "daawat"`.
- Produces: sausage names containing Safari resolve to brand `farmers choice`.
- Produces: normalized `sausages` and `sausage` wording with canonical category `sausage`.

- [ ] **Step 1: Add failing unit tests for canonicalization**

Add tests asserting:

```python
self.assertEqual(ProductMatchService.canonical_brand("daawati"), "daawat")
self.assertEqual(
    ProductMatchService.extract_brand("Beef Sausages (Safari) 500Gm"),
    "farmers choice",
)
self.assertEqual(
    ProductMatchService.extract_brand("Farmer's Choice Safari Beef Sausage 500 Gm"),
    "farmers choice",
)
self.assertEqual(
    ProductMatchService.normalize_name("Beef Sausages (Safari) 500Gm"),
    "beef sausage safari 500g",
)
self.assertEqual(
    ProductMatchService.extract_canonical_category("beef sausage safari 500g"),
    "sausage",
)
```

- [ ] **Step 2: Run RED**

```powershell
cd backend
& 'C:\Users\user\Desktop\Peru\school\ACS 400\SaveBasket\backend\.venv\Scripts\python.exe' manage.py test products.tests_services.ProductMatchServiceTests -v 2
```

Expected: failures show `daawati` remains a separate brand, CleanShelf resolves to `safari`, and plural sausage/category normalization is missing.

- [ ] **Step 3: Implement narrow canonicalization**

In `match_service.py`:

- Add brand aliases for `daawati`, `farmer's choice`, and `farmers choice`.
- Normalize Farmer's Choice apostrophe spelling before generic punctuation cleanup.
- Normalize the whole word `sausages` to `sausage`.
- Recognize `sausage` as canonical category `sausage`.
- In `extract_brand`, return `farmers choice` when the name contains the Farmer's Choice phrase, or when it contains both whole-word `safari` and `sausage`/`sausages`. Do this before iterating `KNOWN_BRANDS` so set iteration order cannot change the result.

- [ ] **Step 4: Add failing ingestion regression tests**

Create one test importing canonical then CleanShelf names for each pair:

```python
canonical_raw = RawScrapedProduct.objects.create(
    store_name="Naivas",
    product_name="Daawat Long Grain Rice 5Kg",
    price="1000.00",
)
alias_raw = RawScrapedProduct.objects.create(
    store_name="CleanShelf",
    product_name="Daawati Long Grain Rice 5Kg",
    price="990.00",
)
canonical, _, _ = ProductMatchService.process_raw_product(canonical_raw)
matched, created, _ = ProductMatchService.process_raw_product(alias_raw)
self.assertFalse(created)
self.assertEqual(matched, canonical)
```

Repeat for the exact Farmer's Choice/Safari names and assert a single canonical product per pair.

- [ ] **Step 5: Run GREEN and the product service suite**

```powershell
& 'C:\Users\user\Desktop\Peru\school\ACS 400\SaveBasket\backend\.venv\Scripts\python.exe' manage.py test products.tests_services -v 2
```

- [ ] **Step 6: Commit**

```powershell
git add backend/products/match_service.py backend/products/tests_services.py
git commit -m "fix: canonicalize confirmed retailer product names"
```

---

### Task 2: Build the targeted duplicate repair service

**Files:**
- Create: `backend/products/confirmed_duplicate_repair.py`
- Create: `backend/products/tests_confirmed_duplicate_repair.py`

**Interfaces:**
- Produces: immutable `ConfirmedDuplicatePair` definitions for the two approved canonical/duplicate normalized names.
- Produces: `plan_confirmed_duplicate_repairs() -> list[RepairPlan]` with no writes.
- Produces: `apply_confirmed_duplicate_repairs() -> RepairResult` inside one atomic transaction.

- [ ] **Step 1: Write failing dry-run planning tests**

Create both canonical and duplicate products with exact current database names. Assert the planner identifies exactly those two pairs, reports missing pairs without error, and does not mutate products, store rows, aliases, prices, baskets, or reviews.

- [ ] **Step 2: Run RED**

```powershell
& 'C:\Users\user\Desktop\Peru\school\ACS 400\SaveBasket\backend\.venv\Scripts\python.exe' manage.py test products.tests_confirmed_duplicate_repair -v 2
```

Expected: import failure because the targeted repair module does not exist.

- [ ] **Step 3: Implement exact pair discovery**

Use constants containing the current stored normalized names:

```python
CONFIRMED_DUPLICATE_PAIRS = (
    ConfirmedDuplicatePair(
        canonical="farmer s choice safari beef sausage 500g",
        duplicate="beef sausages safari 500g",
        alias_store="CleanShelf",
        alias_raw_name="Beef Sausages (Safari) 500Gm",
    ),
    ConfirmedDuplicatePair(
        canonical="daawat long grain rice 5kg",
        duplicate="daawati long grain rice 5kg",
        alias_store="CleanShelf",
        alias_raw_name="Daawati Long Grain Rice 5Kg",
    ),
)
```

Discovery must require exactly one canonical and one duplicate for a pair. Ambiguous lookup results must be reported and skipped rather than guessed.

- [ ] **Step 4: Write failing apply and idempotency tests**

For each pair create:

- a CleanShelf `StoreProduct` on the duplicate;
- a `ProductPrice` on the duplicate;
- a `BasketItem` referencing the duplicate;
- imported aliases and import-review foreign keys referencing the duplicate.

Assert apply moves or reconciles each relationship, creates a reviewed CleanShelf alias, deletes the empty duplicate, and preserves the canonical product. Run apply a second time and assert it performs no additional merge and leaves the same final state.

- [ ] **Step 5: Implement transactional relationship reconciliation**

For each exact pair:

- lock canonical and duplicate rows with `select_for_update()`;
- move `StoreProduct` rows, resolving `(product, store_name)` conflicts by keeping the newest retailer data;
- move `ProductPrice` rows, resolving `(product, branch)` conflicts by keeping the newest price data;
- merge duplicate `BasketItem` quantities into existing canonical basket items;
- repoint `ProductAlias.product`, `ProductImportReview.matched_product`, and `candidate_product`, resolving uniqueness conflicts before updating;
- create/update the confirmed CleanShelf alias with `source=reviewed` and `confidence=1.0`;
- verify no dependent store, price, basket, alias, or review relationship remains before deleting the duplicate.

`RawScrapedProduct` has no product foreign key, so retain its audit rows unchanged.

- [ ] **Step 6: Run GREEN**

```powershell
& 'C:\Users\user\Desktop\Peru\school\ACS 400\SaveBasket\backend\.venv\Scripts\python.exe' manage.py test products.tests_confirmed_duplicate_repair -v 2
```

- [ ] **Step 7: Commit**

```powershell
git add backend/products/confirmed_duplicate_repair.py backend/products/tests_confirmed_duplicate_repair.py
git commit -m "fix: add targeted confirmed duplicate repair"
```

---

### Task 3: Add and validate the safe management command

**Files:**
- Create: `backend/products/management/commands/repair_confirmed_duplicates.py`
- Modify: `backend/products/tests_confirmed_duplicate_repair.py`
- Modify: `walkthrough.md`

**Interfaces:**
- Produces: `python manage.py repair_confirmed_duplicates` as read-only dry run.
- Produces: `python manage.py repair_confirmed_duplicates --apply` as explicit transactional repair.

- [ ] **Step 1: Write failing command tests**

Use `call_command` and captured output. Assert the default command says `DRY RUN`, leaves duplicates intact, and lists both detected pairs. Assert `--apply` says `APPLIED`, performs both merges, and a second invocation reports zero remaining duplicate merges.

- [ ] **Step 2: Run RED**

```powershell
& 'C:\Users\user\Desktop\Peru\school\ACS 400\SaveBasket\backend\.venv\Scripts\python.exe' manage.py test products.tests_confirmed_duplicate_repair -v 2
```

Expected: `Unknown command: repair_confirmed_duplicates`.

- [ ] **Step 3: Implement the command**

Add only an `--apply` flag. Without it, call the planning interface and print intended pair actions. With it, call the apply interface and print merged, skipped, and ambiguous counts. Never accept arbitrary product identifiers through this targeted command.

- [ ] **Step 4: Document operator steps**

Add to `walkthrough.md`:

```powershell
cd backend
.\.venv\Scripts\python.exe manage.py repair_confirmed_duplicates
.\.venv\Scripts\python.exe manage.py repair_confirmed_duplicates --apply
```

Explain that the first command is read-only, the second changes the configured database, and a database backup is recommended before apply.

- [ ] **Step 5: Run the complete pre-apply verification**

```powershell
& 'C:\Users\user\Desktop\Peru\school\ACS 400\SaveBasket\backend\.venv\Scripts\python.exe' manage.py test
& 'C:\Users\user\Desktop\Peru\school\ACS 400\SaveBasket\backend\.venv\Scripts\python.exe' manage.py check
git diff --check
```

- [ ] **Step 6: Commit**

```powershell
git add backend/products/management/commands/repair_confirmed_duplicates.py backend/products/tests_confirmed_duplicate_repair.py walkthrough.md
git commit -m "docs: add confirmed duplicate repair workflow"
```

---

### Task 4: Repair and audit local PostgreSQL

**Files:**
- No repository file changes.

**Interfaces:**
- Consumes: `repair_confirmed_duplicates` command from Task 3.
- Produces: one canonical product and correctly linked retailer rows for each approved pair in the configured local database.

- [ ] **Step 1: Run dry-run against configured PostgreSQL**

```powershell
cd backend
.\.venv\Scripts\python.exe manage.py repair_confirmed_duplicates
```

Expected: exactly two planned merges and no ambiguity.

- [ ] **Step 2: Apply the targeted repair**

```powershell
.\.venv\Scripts\python.exe manage.py repair_confirmed_duplicates --apply
```

Expected: two merges applied inside a transaction.

- [ ] **Step 3: Prove idempotency against PostgreSQL**

```powershell
.\.venv\Scripts\python.exe manage.py repair_confirmed_duplicates
```

Expected: zero remaining duplicate pairs.

- [ ] **Step 4: Audit final catalog links**

Run a read-only Django shell query and confirm:

- one Farmer's Choice/Safari 500 g canonical product has Naivas, Quickmart, Eastmatt, and CleanShelf store rows;
- one Daawat 5 kg canonical product has Naivas, Quickmart, Eastmatt, and CleanShelf store rows;
- reviewed CleanShelf aliases exist for both retailer spellings;
- the duplicate product UUIDs no longer exist.

- [ ] **Step 5: Final repository scope audit**

```powershell
git status --short
git diff main...HEAD --stat
git diff main...HEAD -- .gitignore Scrapper/ci_jobs.txt Scrapper/requirements.txt backend/.env.example frontend/linux frontend/macos frontend/windows
```

Confirm the implementation branch does not include any of the user's unrelated working-tree changes.
