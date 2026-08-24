---
name: gym-recon
description: >
  Monthly finance CLI engine for A+ Street Mall (אריאל פיט & ספא): official
  תקציב מול ביצוע from ledger (ledger_sync), trainer billing, supplier pack.
  Agent judges and decides changes; money math stays in tools/code.
  Use when: run monthly recon, update budget from ledger, ledger sync,
  תקציב מול ביצוע, תריץ התאמה, תעדכן תקציב, תבדוק חשבוניות, billing, suppliers.
  Project root has tools/, core/, jobs/ — NOT recon/+files/ (that is club-finance-recon).
---

# Gym recon engine (CLI)

**Judgment is the agent’s job. Money math is the engine’s job. Prefer improving the engine over bypassing it.**

**Repo root:** directory containing `tools/`, `core/`, `jobs/`, `AGENTS.md`.  
Read `AGENTS.md` + `SCOPE.md` first. Prefer relative paths.

**Protected knowledge — read before changing money logic:**
`docs/CLIENT_IDAN.md` (client + cadence + open questions) ·
`docs/DATA_INVENTORY.md` (real file structures + risks) ·
`docs/PRODUCT_STRATEGY.md` (phases + scope).
Append to their logs only; never rewrite them. If code contradicts them, the code is wrong.

## Agent autonomy

You **should** decide:

- What is broken or incomplete this month  
- What to change (code, config maps, aliases, tests) and how  
- Which tools to run (full pipeline vs subset)  
- How to explain results to Idan  

You **should not**:

- Invent deliverable amounts in chat  
- Freestyle-rebuild official תקציב Excel outside `ledger_sync`  
- Treat Antigravity / “גרסה 2” freestyle xlsx as engine truth  

When product rules are wrong: **edit engine → tests → re-run tools → ship `output/`.**

## What this does for Idan

| Ask | Default run | Give him |
|-----|-------------|----------|
| תקציב מול ביצוע / budget from ledger | `python tools/ledger_sync.py --input ./input --output ./output --month N` | `output/תקציב_מול_ביצוע_*.xlsx` |
| Check invoices / billing | OCR if needed → `tools/billing.py` | `output/חיוב_*.xlsx` + `דגלים` |
| Suppliers | `tools/suppliers.py` | `output/ספקים_לאישור_מנהל.xlsx` |
| Full month | `run_pipeline('./input', './output', month=N)` (agent, preferred) or `python run_all.py --input ./input --output ./output --month N` | all of the above |

Official BvA footer: **`written by gym-recon ledger_sync`**.

**Per-run audit:** every full-month run writes `output/runs/<run_id>/` with
`manifest.json` (input/output SHA-256 + `selected_ledger_tab` + `client_id`),
`report_status.json` (`VALID` / `REVIEW_REQUIRED` / `INVALID`), and `run.log`.
`output/RUN_INVALID.txt` exists **only** for INVALID runs — never deliver `output/`
while it is present. Exit code 0 = VALID or REVIEW_REQUIRED; non-zero = INVALID.
`run_month.bat` is a **LEGACY** wrapper over `run_all.py`.

## Default pipeline (choose steps by judgment)

```text
1. python tools/preflight.py --input ./input
2. python tools/ocr_gemini.py --invoices ./input/invoices --output ./config/invoices_ocr.json
3. python tools/billing.py --input ./input --output ./output --month N
4. python tools/ledger_sync.py --input ./input --output ./output --month N
5. python tools/suppliers.py --input ./input --output ./output --month N   # if supplier PDFs
6. python tools/validate.py --output ./output
```

OCR needs `GEMINI_API_KEY`. Cache skips re-OCR unless `--force`.  
Suppliers OCR: `ocr_gemini.py --suppliers --invoices ./input/invoices_suppliers --output ./config/suppliers_ocr.json`.

## Money write rules

1. Two-layer: כרטסת system · התאמה ידנית never · ביצוע = sum  
2. Income ≤ 0, expenses ≥ 0  
3. Month: memo פרטים → מאזן → ערך (coded rules; improve code if wrong)  
4. Unknown trainer = HOLD + PROPOSE (דגלים + audit)  
5. Missing receipt = flag only  
6. Hebrew strings are keys — do not translate  
7. Prefer openpyxl **inside** engine paths, not one-off money workbooks in chat  

## Ledger output features (engine)

- Strip uncoded pricing-note rows  
- YTD columns `סה"כ תקציב/ביצוע/הפרש YTD 1-N/YY`  
- Income/expense rollups on סה"כ labels  

## Present results

1. Point to `output/`  
2. Billing: open **דגלים** first  
3. BvA: confirm footer + two-layer target-month columns  
4. Chase history: `output/audit_log.json`  
5. If something is wrong: propose code/config fix, implement if in scope, re-run  

## Tests before claiming a code change is done

```text
python -m pytest -q
python tests/test_idan_fixes.py
python tests/test_resilience.py
python tests/test_acceptance.py
```

## Friend install

`friend_install/run_month.bat` — prompts for month. **LEGACY:** kept only for
non-technical muscle memory; the agent path is `run_pipeline()` / `run_all.py`.

## Sibling product

`club-finance-recon` = recon reports / dashboard / drafts — not a substitute for `ledger_sync`.
