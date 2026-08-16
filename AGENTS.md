# Agent rules — gym-recon (ledger & billing engine)

You are in the **monthly finance CLI engine** for אריאל פיט & ספא (A+ Street Mall).  
Client contact for budget-vs-actual: **Idan**.

## Operating model (read this first)

This product is **not** “100% deterministic agent.”  
It is **agent judgment + deterministic money tools.**

| Agent decides | Engine / tools own |
|---------------|--------------------|
| What’s wrong this month (flags, gaps, drift) | Final shekel amounts in official Excel |
| **What** to change (code, config, map, alias, test) | Ledger net (debit − credit), coded month rules |
| **How** to change it (approach, order, scope) | Two-layer write contract |
| Which tools to run (full month vs ledger only vs re-OCR) | Never invent amounts in chat as deliverables |
| How to explain results to Idan | Footer / audit trail of tool output |
| Product/process next steps when asked | |

**One-liner:** *Judgment is the agent’s job. Money math is the engine’s job. Prefer improving the engine over bypassing it.*

### Correct freedom
1. Diagnose (read outputs, דגלים, inputs, code)  
2. Decide what should change and how  
3. Implement in `core/` / `jobs/` / `tools/` / `config/` / `tests/` when needed  
4. Re-run the relevant tool(s)  
5. Validate and report  

### Wrong freedom
- Hand-paint תקציב / invent cells outside the product  
- Freestyle openpyxl “גרסה 2” as the official deliverable  
- Guess amounts in chat as the answer instead of fixing + re-running tools  

## What this product does for Idan

1. **תקציב מול ביצוע** — official workbooks from **כרטסת** + budget template  
   (`python tools/ledger_sync.py` → `output/תקציב_מול_ביצוע_*.xlsx`)
2. **Trainer billing** — invoice OCR + validation → `output/חיוב_*.xlsx` + `דגלים`
3. **Supplier pack** — `output/ספקים_לאישור_מנהל.xlsx` (+30/+60)

**Core Operator Contract:**  
*The operator does NOT need to create, duplicate, or calculate summary workbooks by hand. That is the exact job of this automation engine. We work on a single persistent master template that is automatically populated and updated from raw external inputs (Arbox, Hilan, Invoices, Sales).*

Idan reviews `output/` and `דגלים`; he should not need a freestyle Excel rebuild for official BvA.

## Sibling product (do not mix pipelines)

[`club-finance-recon`](https://github.com/amitswsisa-cyber/club-finance-recon) = trainer HTML recon, dashboard, GUI, **DRAFT** Excel packs.  
Different deliverable. Do not treat its drafts as `ledger_sync` output. See `SCOPE.md`.

## Session start

1. Read this file, `SCOPE.md`, `CLAUDE.md`, `.opencode/decisions.md` if present.  
2. Work under **this** repo root (`tools/`, `core/`, `jobs/`).  
3. Prefer relative paths: `./input`, `./output`, `python tools/...`.

## 🔒 Protected knowledge files — read before changing money logic

| File | Contains | Read it before |
|------|----------|----------------|
| `docs/CLIENT_IDAN.md` | Client transcript, real workflow, cadence, open questions | Touching cadence, sheet layout, or scope |
| `docs/DATA_INVENTORY.md` | Real input-file structure, verified risks | Writing/changing any parser |
| `docs/PRODUCT_STRATEGY.md` | Phase plan, what's in/out of scope | Proposing features or refactors |

**Rules for these three files:**
- They are **source of truth**. If code contradicts them, the **code** is wrong until the owner says otherwise.
- You may **append** to their Change log / Decision log sections.
- You may **not** rewrite, condense, summarize, translate, or delete anything above those sections.
- If your task is not in the current phase (`PRODUCT_STRATEGY.md` §5), **say so and stop** instead of doing it.

### Known-critical facts (do not "fix" without asking)
1. `התאמה ידנית` was **not found** in the client's real workbook — his manual column looks like `ביאורים`.
2. `כרטסת.xlsx` has **4 snapshot tabs**; June net differs by ~₪240k between them. Tab choice must be explicit.
3. תקציב מול ביצוע is a **weekly** dashboard for the client, not only a monthly close.

## Money write rules (non-negotiable)

| Do | Do not |
|----|--------|
| Prefer official numbers from tools under `output/` | Deliver freestyle xlsx as official BvA |
| When rules change: **edit engine code/config**, then re-run tools | Bypass engine by hand-totalling a new workbook |
| Never write `התאמה ידנית` | Invent amounts, accounts, or months in the deliverable |
| Keep Hebrew sheet/column keys as-is | Translate keys “for clarity” |
| Footer on official BvA: `written by gym-recon ledger_sync` | Treat Antigravity/גרסה 2 freestyle as engine truth |

## Default tools (extend code when rules need to change)

```text
python tools/preflight.py --input ./input
python tools/ocr_gemini.py --invoices ./input/invoices --output ./config/invoices_ocr.json
python tools/billing.py --input ./input --output ./output --month N
python tools/ledger_sync.py --input ./input --output ./output --month N
python tools/suppliers.py --input ./input --output ./output --month N
python tools/validate.py --output ./output
```

**Full month (primary path):** call `run_pipeline(input_dir, output_dir, month)` —
an agent runs this in-process, or `python run_all.py --input ./input --output ./output --month N`
from a terminal. `run_month.bat` is a **LEGACY** thin wrapper over `run_all.py`.

**Per-run audit (every full-month run):** `output/runs/<run_id>/` holds
`manifest.json` (input/output SHA-256 hashes + `selected_ledger_tab` + `client_id`),
`report_status.json` (`VALID` / `REVIEW_REQUIRED` / `INVALID`), and `run.log`.
`output/RUN_INVALID.txt` exists **only** for INVALID runs — never trust `output/`
while that marker is present.

- Choose subset by judgment (e.g. only `ledger_sync` if only budget from ledger).  
- If a rule is wrong for Idan: change `core/` / `jobs/` / `config/`, add/adjust tests, re-run — do not patch only the xlsx.

## Ledger business rules (current product law)

1. Two-layer: `ביצוע (כרטסת)` overwrite each run · `התאמה ידנית` never touch · `ביצוע` = sum (value).  
2. Income ≤ 0, expenses ≥ 0 (enforced on write).  
3. Month: memo `פרטים` (regex) → `תאריך למאזן` → `תאריך ערך`. Month attribution is coded, not ad-hoc LLM per row.  
4. Strip uncoded pricing-note rows; keep coded lines.  
5. YTD + income/expense rollups live in the engine — improve code if wrong, don’t reimplement once in chat.

## Tests before claiming a code change is done

```text
python tests/test_idan_fixes.py
python tests/test_resilience.py
python tests/test_acceptance.py
```

## Never commit

`input/**` (except README), `output/**` (except `.gitkeep`), `config/*_ocr.json`, API keys, `.env`.

## Self-documentation rules (Mandatory for all agent sessions)

1. After EVERY change you make, before claiming the task is done:
   a. Append an entry to `docs/BUILDER_LOG.md`
   b. Update `docs/SYSTEM_MAP.md` if the change affects any workflow, sheet, tab, column, trigger, integration, or data flow
   c. Commit the code AND the docs together (or as a separate docs commit)
2. Never commit secrets, API keys, or tokens into any file.
3. Write documentation in plain English a non-technical founder can read. Technical terms are allowed only with a one-line explanation.
4. Do not push to GitHub without explicit approval. Commit locally only, and tell the user the commit is ready to push.

