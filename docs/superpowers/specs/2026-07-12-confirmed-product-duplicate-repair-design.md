# Confirmed Product Duplicate Repair Design

## Goal

Prevent two confirmed naming variations from creating duplicate canonical
products, and safely repair the corresponding rows already stored in local
PostgreSQL.

The confirmed pairs are:

- `Beef Sausages (Safari) 500Gm` and
  `Farmer's Choice Safari Beef Sausage 500 Gm`.
- `Daawati Long Grain Rice 5Kg` and `Daawat Long Grain Rice 5Kg`.

## Canonical Products

- Keep `Farmer's Choice Safari Beef Sausage 500 Gm` as the canonical sausage.
- Keep `Daawat Long Grain Rice 5Kg` as the canonical rice product.
- Treat Farmer's Choice as the sausage manufacturer/brand and Safari as its
  product-line wording for these confirmed sausage names.
- Treat `daawati` as a spelling alias of the canonical `daawat` brand.

## Matching Changes

The matcher will canonicalize `daawati` to `daawat`. It will also normalize the
singular/plural sausage wording used by the confirmed names so that `sausage`
and `sausages` contribute the same product identity. Farmer's Choice/Safari
sausage names will resolve to a compatible canonical brand instead of being
split solely because one retailer omits `Farmer's Choice`.

These rules will be narrowly scoped. The global automatic-match and review
thresholds will not be lowered.

Future imports of the two exact CleanShelf spellings must reuse their canonical
products rather than create new canonical rows or unnecessary review entries.

## Existing-Data Repair

A Django management command will implement the repair instead of relying on an
unrecorded shell edit. It will support a dry run and an explicit apply mode.

For each confirmed pair, the command will:

1. Locate the canonical and duplicate products by their normalized identities.
2. Move every `StoreProduct` and `ProductPrice` reference from the duplicate to
   the canonical product, resolving uniqueness conflicts without losing the
   canonical row.
3. Repoint relevant raw scraped rows and import-review references when those
   relationships exist.
4. Create or update a reviewed `ProductAlias` for the retailer spelling.
5. Delete the duplicate product only when no dependent store, price, or review
   data remains.
6. Be safe to run again without creating duplicate aliases or corrupting data.

Dry-run mode will report planned actions without writing. Apply mode will run
inside a database transaction and report counts without exposing credentials.

## Testing

Tests will first reproduce both matching failures using the exact retailer
names. They will assert that each second import reuses the first canonical
product. Command tests will construct both duplicate pairs, verify dry-run does
not mutate data, verify apply mode moves store rows and creates reviewed
aliases, and verify a second apply is harmless.

The complete Django test suite and system check must pass before the command is
run against local PostgreSQL. After applying the repair, a read-only audit must
confirm one canonical product per pair and all four supermarket store rows are
linked to the intended products.

## Safety and Scope

- Do not change global matching thresholds.
- Do not merge unrelated Safari, Farmer's Choice, Daawat, rice, or sausage
  products.
- Do not delete a product while dependent records remain.
- Do not print or commit database credentials or API keys.
- Preserve the user's uncommitted `.gitignore`, `Scrapper/ci_jobs.txt`, and
  `backend/.env.example` changes.
