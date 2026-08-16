# PLAN_RECON_FINAL.md

# Gym Recon — Tool-Orchestrated Agent (complete v1 plan)

**Do not skip any section.** This is the single source of truth for implementation.

---

## 0. Product vision (what we are building)

An AI agent a non-technical friend runs monthly for  
**אריאל פיט & ספא / A+ Street Mall** (gym = חדר כושר + Pilates = פילאטיס).

### Roles

| Role | Responsibility |
|------|----------------|
| **Agent** | Intent, tool choice, order of tools, explain flags to the manager in plain language (Hebrew OK) |
| **Python tools** | Exact shekel math, openpyxl Excel writes, matching, preflight, validate |
| **Gemini Vision** | Primary/only engine for reading Hebrew invoice PDFs/images → structured JSON |
| **Persistent JSON + Excel** | Memory across runs + manager deliverables |

### Explicit non-goals (v1)

- **No OfficeCLI** (openpyxl is the only Excel writer/reader for money files)
- **No n8n / Supabase** unless multi-branch always-on is later approved
- **No multi-model brainstorming** as part of monthly money runtime
- **No silent invent** of unknown trainers or missing receipts
- **Never write** budget columns labeled `התאמה ידנית`

---

## 1. Hard business rules (must not break)

1. **Two-layer actuals (budget):**  
   `ביצוע (כרטסת)` = system, overwritten each run  
   `התאמה ידנית` = manager, **never** overwritten  
   `ביצוע` (display) = sum (value or formula; keep consistent with existing engine)

2. **Service month, not document date** for invoices (session_dates majority).

3. **Income is negative** in ledger movement (Σ debit − Σ credit).

4. **Account map:** 180+code = Club, 181+code = Pilates; income 101+80xxx Club, 101+81xxx Pilates.

5. **Trainer aliases:** exact → normalized → fuzzy ≥88 → UNMAPPED (never guess below threshold).

6. **Unknown trainer = HOLD + PROPOSE** (name, tax id, branch, category, rate, closest match) in `דגלים` + audit JSON. Not written into money rows.

7. **Three-way match (freelancers):** invoice × Arbox held sessions (`מתקיים`) × rate matrix.  
   Salaried: Hilan/חילנט vs system hours (tolerance ~2h warn).

8. **Verdicts:** OK = auto-write, REVIEW = write+flag, BLOCK = hold.

9. **Mark gaps:** amount written to `דוח מרכז` but not rolled into `חיוב יזם` → flag in `דגלים`.

10. **Missing receipt:** expected trainer/activity this month, no invoice → flag `חסרות קבלות`, do not fabricate.

11. **Hebrew strings are keys** — do not “improve” or translate sheet/file/column names used as keys.

12. **Targets (reference):** Club ~124,467.90, Pilates ~33,203 (drift from partial samples must flag, not crash).

---

## 2. Architecture (canonical — 5 tools)

```
Agent (orchestrator + manager communication)
  │
  ├─ Tool 1: preflight       → readiness JSON (what files found / missing)
  ├─ Tool 2: gemini_ocr      → config/invoices_ocr.json (persistent cache)
  ├─ Tool 3: billing         → billing xlsx + דגלים + trainer_amounts_*.json + audit entries
  ├─ Tool 4: ledger_sync     → תקציב_מול_ביצוע_*.xlsx (two-layer) + audit entries
  └─ Tool 5: validate        → acceptance tests / non-empty checks / print PASS-FAIL

Excel: openpyxl only
Vision: Gemini (primary) for Hebrew invoices
```

### Agent does

- Choose tools (full pipeline vs “only ledger” vs “only check inputs”)
- Pass month / branch / paths
- Read compact JSON summaries from tools
- Point the human at issues (דגלים, unknown trainer, Hilan delta, missing files, missing receipts)

### Agent does NOT

- Hand-calculate shekels cell-by-cell in chat
- Rewrite Excel without the Python tools
- Auto-approve unknown trainers

### Token model

- Heavy work = Python (zero tokens)
- Tools return **small JSON summaries** (flags, totals, paths)
- Agent reads summaries only → low token cost

---

## 3. Persistent state (required — never “optional”)

| Path | Purpose |
|------|---------|
| `config/invoices_ocr.json` | OCR cache from Gemini/agent vision |
| `config/trainer_aliases.json` | Canonical trainers + aliases |
| `config/pay_matrix.json` | Rates / tiers |
| `config/account_map.json` | Ledger → budget |
| `config/branches.json` | Branch layout, row maps, targets |
| `output/audit_log.json` | Full chase history (mismatches, holds, unmapped) |
| `output/trainer_amounts_<branch>.json` | Validated amounts before/after Excel gate |
| `output/*.xlsx` | Manager deliverables including sheet `דגלים` |
| `input/` | Drop zone for monthly sources |

Agent and friend batch must always write/read these under project root:

`C:\Users\Amit\Documents\gym-recon`

---

## 4. Paths

```
SOURCE (legacy session copy — already promoted; only re-copy if TARGET incomplete) =
C:\Users\Amit\AppData\Local\Packages\Claude_pzs8sxrjxfjjc\LocalCache\Roaming\Claude\local-agent-mode-sessions\817ec14a-78a0-422d-8484-88324e7dd4eb\4fc43137-b9e4-4dd9-b4e9-fd00188475f4\local_29084a3a-c2f9-4368-8b45-3c9551fdd2ed\outputs\gym_recon_v2

TARGET =
C:\Users\Amit\Documents\gym-recon

Skills =
%USERPROFILE%\.claude\skills\gym-recon\SKILL.md
%USERPROFILE%\.agents\skills\gym-recon\SKILL.md
```

### STATUS snapshot (as of plan write)

| Item | Status |
|------|--------|
| Project at TARGET | DONE (engine present) |
| Skill installed | DONE (re-sync SKILL.md after edits) |
| 5 CLI tools under `tools/` | NOT DONE — implement |
| Gemini primary OCR | PARTIAL — strengthen `core/ocr.py` + `tools/ocr_gemini.py` |
| friend_install | NOT DONE |
| OfficeCLI | OUT OF SCOPE — do not install as dependency |
| Resilience chaos tests | NOT DONE — add |

---

## 5. Implementation phases (execute in order)

### Phase A — Project hygiene (if needed)

1. Ensure TARGET has: `run_all.py`, `core/`, `jobs/`, `config/`, `tests/`, `input/`, `output/`, `SKILL.md`, `CLAUDE.md`.
2. Do not delete `output/` sample artifacts unless asked.
3. Create `tools/` directory.

**VERIFY A**

```powershell
Test-Path C:\Users\Amit\Documents\gym-recon\run_all.py
Test-Path C:\Users\Amit\Documents\gym-recon\jobs\billing_output.py
Test-Path C:\Users\Amit\Documents\gym-recon\config\branches.json
```

---

### Phase B — Gemini Vision OCR (Hebrew primary)

**Files:** `core/ocr.py`, new `tools/ocr_gemini.py`

Requirements:

1. Primary path: Gemini Vision when `GEMINI_API_KEY` is set (env only — never hardcode key).
2. Secondary path: if agent already wrote `config/invoices_ocr.json`, load cache first (don’t re-OCR unless forced).
3. Schema (strict keys):

```json
{
  "file": "str",
  "trainer": "str",
  "doc_number": "str",
  "doc_date": "YYYY-MM-DD",
  "issuer_tax_id": "str",
  "billed_to": "str",
  "stated_total": 0.0,
  "vat_included": false,
  "unit_kind": "session|hour|monthly",
  "category": "personal|studio|group|class|other",
  "branch": "פילאטיס|חדר כושר",
  "line_items": [{"desc":"","qty":0,"rate":0,"total":0}],
  "session_dates": ["d.m.yy or DD/MM/YYYY"],
  "notes": "str"
}
```

4. **Per-invoice isolation:** one bad image must not stop the batch. Failed files → list in return JSON + later `דגלים`.
5. Persist to `config/invoices_ocr.json` (merge by file name when possible).
6. CLI:

```bash
python tools/ocr_gemini.py --invoices ./input/invoices --output ./config/invoices_ocr.json
python tools/ocr_gemini.py --force   # re-OCR even if cache exists
```

Return compact summary JSON to stdout:

```json
{"ok": true, "n_ok": 5, "n_fail": 1, "failed": ["x.pdf"], "path": "config/invoices_ocr.json"}
```

**VERIFY B**

```powershell
cd C:\Users\Amit\Documents\gym-recon
python -c "import core.ocr as o; print('ok', hasattr(o,'load_or_ocr') or hasattr(o,'gemini_available'))"
```

If no API key: tool must exit gracefully with clear message, not crash stack.

---

### Phase C — Modular tools (5 CLIs)

Create under `tools/`. Prefer thin wrappers that import existing `jobs/` + `core/` — **do not rewrite business logic from scratch**.

#### C1 `tools/preflight.py`

```bash
python tools/preflight.py --input ./input
```

- Use `core/inputs.py` preflight if exists.
- Print human lines + JSON readiness: ledger, budget, arbox, approval per branch, invoices_dir / invoices_ocr.
- Exit code 0 if minimum for *something* exists; non-zero only if input dir missing.

#### C2 `tools/ocr_gemini.py`

(See Phase B.)

#### C3 `tools/billing.py`

```bash
python tools/billing.py --input ./input --output ./output --month 6 [--branch club|pilates|all]
```

- Call existing `job_billing` + `billing_output` pipeline.
- Write `output/trainer_amounts_*.json` first (gate), then Excel.
- Produce per-branch workbooks with sheets:  
  `חיוב יזם`, `דוח מרכז לאישור מנהל`, `חילנט`, `ריכוז שעות`, `דגלים`
- Append audit events to `output/audit_log.json` (merge/append, don’t wipe whole history blindly — prefer append or replace with full run snapshot documented in file).
- Stdout summary JSON: totals, n_held, n_new_trainers, n_missing_receipts, paths, flags_top.

#### C4 `tools/ledger_sync.py`

```bash
python tools/ledger_sync.py --input ./input --output ./output --month 6 [--branch club|pilates|all]
```

- Use existing `ledger` + `ledger_output`.
- Two-layer write; never touch manual adjustment column.
- Fix blank month total rollups if still broken (compute values in Python).
- Stdout summary JSON: n_cells_written, paths, unmapped_accounts count.

#### C5 `tools/validate.py`

```bash
python tools/validate.py
# or
python tools/validate.py --output ./output
```

- Run `tests/test_acceptance.py` if runnable.
- Extra: ensure key output xlsx exist; print PASS/FAIL.
- Do not require OfficeCLI.

#### C6 Keep `run_all.py` as full pipeline

`run_all.py` should call the same underlying functions as tools (or shell out to tools) so friend batch and agent share one path:

order: preflight → ocr (if invoices) → billing → ledger_sync → validate (optional warn)

**VERIFY C**

```powershell
cd C:\Users\Amit\Documents\gym-recon
python tools/preflight.py --input ./input
python tools/billing.py --help
python tools/ledger_sync.py --help
python tools/validate.py --help
python tools/ocr_gemini.py --help
```

All must run without import errors.

---

### Phase D — Resilience (do not skip)

Implement or confirm in code:

1. **Per-invoice / per-trainer try-except** in billing validation loop — continue on failure, flag failure.
2. **Prefer label-based row find** when writing external trainer lines (search Hebrew label in approval sheet) when config row maps fail or as safety check; fall back to `branches.json` row map.
3. **Unmapped ledger accounts** → count + list in summary/audit, not silent total drop without notice.
4. **Preflight** blocks full run with clear Hebrew/English message if critical files missing.

### Chaos tests (add to `tests/test_acceptance.py` or `tests/test_resilience.py`)

| Test | Assert |
|------|--------|
| Bad/corrupt invoice entry in OCR JSON | Run continues; failure flagged; other invoices process |
| Unknown trainer | Not in money totals; in pending/דגלים proposal |
| Missing receipt list | Flagged when expected trainer has no invoice (if logic already present, keep; else implement gate) |
| Manual adjustment survival | Re-run ledger does not wipe `התאמה ידנית` |
| Unmapped account | Logged, not crash |

**VERIFY D**

```powershell
cd C:\Users\Amit\Documents\gym-recon
python tests/test_acceptance.py
```

If resilience file added: run it too. No regressions on existing 16 checks if still present.

---

### Phase E — Friend pack (`friend_install/`)

#### `install.ps1`

- `$Root = parent of friend_install`
- `pip install openpyxl pandas` (+ `google-generativeai` if used for Gemini)
- Copy `SKILL.md` to `~\.claude\skills\gym-recon` and `~\.agents\skills\gym-recon`
- Remind: set user env `GEMINI_API_KEY` for OCR on friend PC
- **No OfficeCLI install**

#### `run_month.bat` (double-click)

- cd to project root
- If no `%1`: prompt for month 1–12; if empty Enter → **previous calendar month** via PowerShell
- Run pipeline:

```bat
python tools\preflight.py --input .\input
python tools\ocr_gemini.py --invoices .\input\invoices --output .\config\invoices_ocr.json
python tools\billing.py --input .\input --output .\output --month %MONTH%
python tools\ledger_sync.py --input .\input --output .\output --month %MONTH%
python tools\validate.py --output .\output
```

- On failure pause with message; on success tell user to open `output\` and sheet `דגלים`

#### `FRIEND_README.txt`

- One-time Python + install.ps1 + GEMINI_API_KEY
- Monthly: files in `input\`, double-click bat, read `דגלים`
- Do not edit `התאמה ידנית`

**VERIFY E**

```powershell
Test-Path C:\Users\Amit\Documents\gym-recon\friend_install\install.ps1
Test-Path C:\Users\Amit\Documents\gym-recon\friend_install\run_month.bat
Test-Path C:\Users\Amit\Documents\gym-recon\friend_install\FRIEND_README.txt
```

---

### Phase F — Agent skill (`SKILL.md` + install)

Update `SKILL.md` to describe:

1. Project root path
2. Each tool command (preflight, ocr, billing, ledger, validate, run_all)
3. When to run full pipeline vs single tool
4. How to present flags to manager (point to `דגלים` + audit_log)
5. Gemini / `GEMINI_API_KEY` for invoices
6. openpyxl only; no OfficeCLI
7. Persistent JSON locations
8. Hard rules (HOLD, two-layer, service month)

Copy to:

- `~\.claude\skills\gym-recon\SKILL.md`
- `~\.agents\skills\gym-recon\SKILL.md`

Update `CLAUDE.md` with install paths + tool list + Gemini + openpyxl-only.

**VERIFY F**

```powershell
Select-String -Path C:\Users\Amit\Documents\gym-recon\SKILL.md -Pattern "tools/preflight|Gemini|openpyxl|audit_log"
Test-Path C:\Users\Amit\.claude\skills\gym-recon\SKILL.md
```

---

### Phase G — Optional polish (only after A–F)

1. `run_all.py` prints the same compact summary JSON as tools for the agent.
2. Dashboard HTML update if already exists — optional.
3. Do **not** add OfficeCLI bridge.

---

## 6. Forbidden actions for executor models

| Forbidden | Why |
|-----------|-----|
| Install/require OfficeCLI | Explicitly rejected for this product |
| Replace openpyxl writers with OfficeCLI | Complexity / dependency |
| Auto-write unknown trainers | Hard rule |
| Touch `התאמה ידנית` | Hard rule |
| Hardcode GEMINI_API_KEY | Security |
| Rewrite pay matrix numbers | Business sign-off |
| Drop tools to “only 3” without preflight/validate | User required full set |
| Drop persistent JSON | Chase/history required |
| Rebuild entire engine from scratch | Use existing jobs/core |

---

## 7. Done criteria (all must be true)

1. TARGET project stable at `Documents\gym-recon`
2. Five tools exist and `--help` / basic run works
3. Gemini OCR path documented + env-based; cache JSON persistent
4. Billing + ledger still openpyxl; two-layer + HOLD intact
5. `audit_log.json` + `trainer_amounts_*.json` + `דגלים` remain part of flow
6. `friend_install` double-click month prompt works
7. Skill installed and teaches tool orchestration
8. Acceptance tests pass (or document which need sample input paths fixed)
9. Resilience tests added or existing gates confirmed
10. No OfficeCLI dependency

---

## 8. Suggested agent chat UX (after tools exist)

User: “תריץ התאמה ליוני”  
Agent:

1. `preflight` → report missing files if any  
2. `ocr_gemini` if new invoices  
3. `billing` + `ledger_sync`  
4. `validate`  
5. Read summaries → tell manager: totals, Hilan delta, held invoices, new trainers, missing receipts, paths to `output\`

User: “רק תקציב” → only `ledger_sync`  
User: “רק חשבוניות” → ocr + billing  

---

## 9. Relation to older plans

| Old plan | Status |
|----------|--------|
| `PLAN_OFFICECLI_LOW_MODEL.md` | Superseded for Excel tool; packaging ideas kept |
| OfficeCLI hybrid Option C | **Rejected for v1** — openpyxl only |
| ADHD | Design-time only, not monthly runtime |
| Multi-tool + Gemini + agent orchestration | **This plan** |

If conflict: **this file wins**.

---

## 10. Executor order checklist

```
[ ] A hygiene + tools/ folder
[ ] B Gemini OCR
[ ] C1–C5 tools + wire run_all
[ ] D resilience + tests
[ ] E friend_install
[ ] F SKILL.md + CLAUDE.md + copy skills
[ ] G optional polish
[ ] Full VERIFY done criteria
```
