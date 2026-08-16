# CLAUDE.md — gym-recon engine

**Client:** אריאל פיט & ספא בע"מ (A+ Street Mall) — חדר כושר + פילאטיס.  
**For Idan:** official monthly **תקציב מול ביצוע** from ledger, trainer billing Excel, supplier pack.  
**Shape:** re-runnable CLI. Files in `input/` → tools → `output/`.

Read **`AGENTS.md`** for lockdown. Read **`SCOPE.md`** for product boundary.

## Run

```
python tools/preflight.py --input ./input
python tools/billing.py --input ./input --output ./output --month 6
python tools/ledger_sync.py --input ./input --output ./output --month 6
python tools/validate.py --output ./output
python run_all.py --input ./input --output ./output --month 6
python tests/test_idan_fixes.py
python tests/test_resilience.py
python tests/test_acceptance.py
```

## Tools (`tools/`)

| Tool | Purpose |
|------|---------|
| preflight | Input readiness |
| ocr_gemini | Gemini OCR (Hebrew invoices) |
| billing | Invoices → `חיוב_*.xlsx` + דגלים |
| ledger_sync | כרטסת → `תקציב_מול_ביצוע_*.xlsx` |
| suppliers | Supplier approval workbook |
| validate | Acceptance / output check |

## Core rules

- **Two-layer:** `ביצוע (כרטסת)` overwritten · `התאמה ידנית` NEVER · `ביצוע` = sum VALUE  
- **Service month (invoices):** month with most `session_dates`  
- **Income ≤ 0 / expenses ≥ 0** (enforced on write)  
- **Ledger month:** `פרטים` memo regex → מאזן → ערך · no AI  
- **Accounts:** 180+code Club, 181+code Pilates; income 101+80xxx / 101+81xxx  
- **Trainers:** exact → normalized → fuzzy ≥88 → UNMAPPED; unknown = HOLD+PROPOSE  
- **Missing receipt:** flag only, never fabricate  
- **Agent model:** judge and decide what/how to change; money deliverables from tools. Prefer improve engine → re-run over freestyle Excel

## Layout

- `tools/` — CLI entrypoints  
- `core/` — ledger, arbox, ocr, inputs, common  
- `jobs/` — billing_output, ledger_output, audit, suppliers  
- `config/` — maps, aliases, rates (no secrets)  
- `input/` — monthly drop (gitignored)  
- `output/` — deliverables (gitignored)  
- `tests/` — idan_fixes, resilience, acceptance  
- `friend_install/` — `run_month.bat`

## OCR

- `GEMINI_API_KEY` env only · cache `config/invoices_ocr.json` · `--force` to redo  

## Sibling repo

`club-finance-recon` = recon reports/dashboard/drafts. **Not** this ledger engine. Do not substitute.

## Self-documentation rules (Mandatory for all agent sessions)

1. After EVERY change you make, before claiming the task is done:
   a. Append an entry to `docs/BUILDER_LOG.md`
   b. Update `docs/SYSTEM_MAP.md` if the change affects any workflow, sheet, tab, column, trigger, integration, or data flow
   c. Commit the code AND the docs together (or as a separate docs commit)
2. Never commit secrets, API keys, or tokens into any file.
3. Write documentation in plain English a non-technical founder can read. Technical terms are allowed only with a one-line explanation.
4. Do not push to GitHub without explicit approval. Commit locally only, and tell the user the commit is ready to push.

