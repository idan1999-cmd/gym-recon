# gym-recon

Monthly **finance CLI engine** for **אריאל פיט & ספא** (A+ Street Mall) — gym + Pilates.

Built so **Idan** (and ops) can close the month with **deterministic** tools: drop files in `input/`, run Python, get validated workbooks in `output/`.

## What Idan gets from this project

| Deliverable | Tool | Output |
|-------------|------|--------|
| **תקציב מול ביצוע** (official, two-layer) | `tools/ledger_sync.py` | `output/תקציב_מול_ביצוע_חדר_כושר.xlsx`, `…_פילאטיס.xlsx` |
| Trainer billing + **דגלים** | `tools/billing.py` | `output/חיוב_*.xlsx` |
| Supplier approval (+30/+60) | `tools/suppliers.py` | `output/ספקים_לאישור_מנהל.xlsx` |

Budget-vs-actual is driven by **כרטסת** (ledger) into the yearly budget layout:

- System column `ביצוע (כרטסת)` — rewritten each run  
- Manager column `התאמה ידנית` — **never** overwritten  
- Display `ביצוע` — sum as a value  
- Income **negative**, expenses **positive**  
- YTD columns, section rollups, strip uncoded pricing notes  
- Month: memo `פרטים` → `תאריך למאזן` → `תאריך ערך` (no AI)

See `SCOPE.md` for product boundaries vs the dashboard/drafts app.

## Quick start

```powershell
cd path\to\gym-recon
python -m pip install -r requirements.txt
$env:GEMINI_API_KEY = "..."   # only for OCR of new invoices

python tools/preflight.py --input ./input
python tools/ledger_sync.py --input ./input --output ./output --month 6
# full month:
python run_all.py --input ./input --output ./output --month 6
```

Inputs: see `input/README.md` (כרטסת, תקציב תזרים, Arbox/מרכז, `invoices/`, …).

## Tools

| Tool | Purpose |
|------|---------|
| `tools/preflight.py` | Input readiness |
| `tools/ocr_gemini.py` | Hebrew invoice OCR (Gemini) |
| `tools/billing.py` | Invoice validation + Excel |
| `tools/ledger_sync.py` | Ledger → תקציב מול ביצוע |
| `tools/validate.py` | Output / acceptance checks |
| `tools/suppliers.py` | Supplier payments pack |

## Agent model

**Judgment is the agent’s job. Money math is the engine’s job.**  
Agents diagnose, decide what/how to change, improve code/config, and re-run tools.  
They do not freestyle official money Excel outside the engine.

## Money rules (humans + agents)

1. **Two-layer actuals** — never write `התאמה ידנית`.
2. **Income ≤ 0, expenses ≥ 0**.
3. **Ledger month** — memo → מאזן → ערך (coded; change code if the rule is wrong).
4. **Official BvA via `ledger_sync`** — footer `gym-recon ledger_sync`. Prefer engine fixes over one-off workbooks.
5. **Unknown trainers** — HOLD + PROPOSE, never auto-post to money.

Agents: **`AGENTS.md`** first. Product boundary: `SCOPE.md`. Architecture: `CLAUDE.md`. Skill: `SKILL.md`.

## Knowledge base (protected)

| File | What it answers |
|------|-----------------|
| [`docs/CLIENT_IDAN.md`](docs/CLIENT_IDAN.md) | Who the client is, how he actually works, what he asked for, what's still unanswered |
| [`docs/DATA_INVENTORY.md`](docs/DATA_INVENTORY.md) | What each input file really contains, and which parts are reusable at another gym |
| [`docs/PRODUCT_STRATEGY.md`](docs/PRODUCT_STRATEGY.md) | Service-first plan, phase gates, pricing anchor, what's out of scope |

These are the persistent context for this project. Read them before changing money logic.

## Tests

```powershell
python tests/test_idan_fixes.py
python tests/test_resilience.py
python tests/test_acceptance.py
```

## Related product

Trainer HTML recon, GUI, and manager **draft** Excel packs live in  
[`club-finance-recon`](https://github.com/amitswsisa-cyber/club-finance-recon) — separate pipeline, not a substitute for `ledger_sync`.

## Privacy

Do **not** commit `input/`, `output/`, or OCR caches (`config/*_ocr.json`). Client PII and amounts stay local.

## Future (not now)

Read-only Q&A over past recon files (RAG-style) may be added later — never writes money. See `.opencode/decisions.md`.
