# Progress (agent)

## 2026-08-03 — Owner decisions A–G implemented (run_all rewrite) (DONE)

- **A — memo month parse fixed at the source:** `core/common.py::parse_memo_month` now
  parses `dd.mm.yy` (`05.06.26`→2026-06), rejects instalment `5/12` as a year, rejects
  2-digit years < 20. Impact vs balance-first: 165/897 rows move, June delta ₪28,651.65.
  Docs (AGENTS/README/CLAUDE/SKILL/decisions) updated to memo → מאזן → ערך.
- **B/C — per-run audit:** `run_all.py` rewritten → `RunContext`, `run_pipeline()`.
  Every run writes `output/runs/<run_id>/{manifest.json, report_status.json, run.log}`;
  `RUN_INVALID.txt` only for INVALID (mirrored to output/). Exit 0 = VALID/REVIEW_REQUIRED,
  non-zero = INVALID. Manifest carries input/output SHA-256 + client_id +
  `selected_ledger_tab` (via Ledger Sync JSON, not in-process import).
- **D — Hilan zero:** `tools/billing.py` `hilan_suspect` → `HILAN_SUSPECT_ZERO` WARN +
  branch/run status `REVIEW_REQUIRED` + `review_required` in summary.
- **E — no fabricated OCR:** `config/suppliers_ocr.json` moved to
  `tests/fixtures/suppliers_ocr_SAMPLE_ONLY.json`; `tools/suppliers.py` only uses OCR
  entries linked to real input invoices, else writes a truthful empty pack.
- **F — strict validate gate:** `_validate_gate_passed` requires exit 0 AND parsed
  JSON ok/pass==true; text matching is no proof.
- **G — `run_month.bat` created as LEGACY thin wrapper** over `run_all.py`.
- Added `tests/test_run_pipeline.py` (12 tests) + owner A/D/E tests in test_bugs_pytest.py
  (now 28). Added `pytest>=7` to requirements.txt. BUILD_LOG.md updated.

## Final verification (all green)

- `python -m pytest -q` → **44 passed**
- `python tests/test_acceptance.py` → **58 passed** · `test_idan_fixes.py` → 27 · `test_resilience.py` → 11
- Real run `run_pipeline('./input','./output',month=6)` → exit 0, status **REVIEW_REQUIRED**
  (Pilates REVIEW drift), manifest 5 inputs + 5 outputs hashed, tab `13.7`, no RUN_INVALID.txt.

## Remaining / blocked

- Working tree has many uncommitted changes across this session + the prior pass
  (`run_all.py`, `core/ledger.py`, `tools/billing.py`, `tools/suppliers.py`, `tools/ledger_sync.py`,
  `core/common.py`, `core/validation.py`, `core/manifest_tracking.py`, `jobs/billing_output.py`,
  `conftest.py`, tests, docs, `run_month.bat`, `requirements.txt`). Not committed unless asked.
- `tools/validate.py` legacy 60s-timeout acceptance harness (pre-existing, unchanged).

---

# Progress (agent)

## 2026-08-03 — Critical bugs + validation controls + manifest tracking (DONE)

- Fixed all 6 bugs from the owner brief:
  1. `tools/billing.py` Hilan cross-check was dead (`.cell()` on Workbook → AttributeError swallowed) → new `read_hilan_crosscheck` on the real worksheet; exits 1 on failure. Verified real: sys=20850, act=20500, Δ=350.
  2. `run_all.py` always returned 0 → now writes `output/report_status.json` (VALID/INVALID) and propagates non-zero exit; verified end-to-end exit 1 + INVALID.
  3. `config/suppliers_ocr.json` fake money → already gitignored+untracked (repo-safe). Open: owner to approve physical deletion off disk.
  4. Month priority reversed to memo → balance → value via `MONTH_PRIORITY` (owner-ordered; FLAGGED as reversing 2026-07-29 decision — needs owner confirm).
  5. Ledger tab selection: `_select_ledger_tab` picks latest tab covering target month, logs to stderr; `ledger_sync` passes `target_month`.
  6. `jobs/billing_output.py`: unknown formulas raise `UnknownFormulaError` instead of writing 0.
- New: `core/validation.py` (4 gates), `core/manifest_tracking.py` (SHA-256 + client_id), `tests/test_bugs_pytest.py` (20 tests), `conftest.py`, `BUILD_LOG.md`.
- Review pass applied: header scan all-rows, approval workbooks validated in gate, SUM sheet-qualifier handling, manifest keyed by abs path, cleared stale `__pycache__` (cpython-310 pyc from 7/19 masked 5 tests).

## Final verification (all green)

- `python -m pytest tests/` → **28 passed**
- `python tests/test_acceptance.py` → **58 passed**
- `python tests/test_idan_fixes.py` → 27 passed · `python tests/test_resilience.py` → 11 passed
- Input gate on real inputs → no errors.

## Remaining / blocked

- Owner decision needed: (a) Bug-4 memo-first is the new product law? (b) delete `config/suppliers_ocr.json` off disk?
- `tools/validate.py` legacy 60s-timeout harness behaviour (pre-existing).
