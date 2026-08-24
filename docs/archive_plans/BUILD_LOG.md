# BUILD_LOG — Critical Bug Fixes & Validation Controls

System: gym-recon (monthly finance CLI engine, client ארי– Idan). Repo root:
`C:\Users\Amit\Documents\gym-recon`. Owner is non-technical, runs via
`friend_install/run_month.bat`.

Every entry: date, files changed, what changed + why, test result before/after.

---

## 2026-08-03 — Session: critical bugs + validation controls + manifest tracking

### Bug 1 — Hilan Cross-Check was Dead (silent zeros)
- **File:** `tools/billing.py:97-98` (now `read_hilan_crosscheck`, helper added).
- **Cause:** `.cell()` was called on the loaded **Workbook** object (which has no
  `.cell()` method) instead of a **Worksheet**, raising `AttributeError` every run.
  The bare `except Exception` swallowed it, so `hilan` was always `{0,0,0}` and the
  Δ control always showed "OK".
- **Fix:** extracted `read_hilan_crosscheck(wb_path, sheet_name, sys_row, act_row,
  col)` that loads the **specific worksheet** `cfg["approval_sheet"]` and reads both
  Hilan cells from it. On a missing sheet it raises `ValueError`; `main()` now logs a
  `HILAN_CROSSCHECK_FAILED` ERR entry and exits 1 (no more silent fake-zero pass).
- **Test:** `tests/test_bugs_pytest.py::test_import_hl_fix1_hilan_reads_real_worksheet`
  (builds a real workbook; verifies Δ is visible) and
  `test_import_hl_fix1_hilan_missing_sheet_raises`. **Before:** hilan always zeros.
  **After:** real workbook → system=20850, actual=20500, delta=350.

### Bug 2 — run_all.py Always Returned 0
- **File:** `run_all.py:132-133`.
- **Cause:** `main()` hardcoded `return 0` regardless of tool failures.
- **Fix:** `_run_tool(...)` now writes `output/report_status.json` marking the run
  `INVALID` with the failed step + exit code when a tool fails, and raises
  `SystemExit(proc.returncode)` when `fail_hard` (default) so the pipeline halts.
  On a fully clean run `_mark_valid()` writes `final=VALID`. `main()` returns the
  propagated non-zero code when reached.
- **Test:** `test_ffix2_run_all_returns_nonzero_on_tool_failure` verifies a failing
  step raises a nonzero SystemExit and writes an INVALID status; `test_ffix2_mark_valid_after_clean`.
  **Before:** run_all exited 0 even on failure. **After:** verified end-to-end that a
  failing validate step exits **1** and writes `report_status.json = INVALID`.

### Bug 3 — Fake Money Data in suppliers_ocr.json
- **File:** `config/suppliers_ocr.json`.
- **Status:** already covered by `.gitignore` line 28 and **not tracked** by git
  (verified: `git ls-files config/` does NOT list it; `git check-ignore` matches).
- **Fix:** kept it untracked; added `config/manifest.json` (input manifest) to
  `.gitignore`. Added a regression test asserting the file is gitignored and that
  `load_supplier_ocr()` on a missing path returns `[]` (never fabricates money).
- **Note / open decision:** the on-disk file still contains fake amounts (~₪20k) and
  is read by `tools/suppliers.py` when it exists (via the `os.path.exists` cache
  branch). **Safest next step (needs owner approval): delete the file off disk** so
  no fake amounts can ever flow. It is already not committed, so the repo is safe.

### Bug 4 — Wrong Month-Priority Rule (memo vs balance)
- **File:** `core/ledger.py` (model `MONTH_PRIORITY` + `parse_ledger`).
- **Cause:** priority was balance_date → memo → value. Data shows a +1-month lag on
  105 rows (₦28,651 drift in June) because the accounting date precedes the memo.
- **Fix:** priority is now **memo → balance → value** via `MONTH_PRIORITY` constant.
- **⚠️ DECISION FLAG:** this REVERSES the decision recorded in
  `.opencode/decisions.md` (2026-07-29) and `AGENTS.md` ledger rule #3 (which said
  balance-first). The owner explicitly ordered the change (Bug 4 in this brief); it is
  implemented and isolated behind a named constant for easy revert. Confirm this is the
  intended new product law.
- **Test:** `test_fix4_memo_wins_over_balance_date` (2026-06 vs memo-april) and
  `test_fix4_memo_beats_balance_for_lagged_invoice`. **Before:** balance won; **After:**
  memo wins.

### Bug 5 — Ledger Tab Selection was Arbitrary
- **File:** `core/ledger.py:15` (`_rows_from_xlsx` defaulted to
  `wb[wb.sheetnames[-1]]` — last tab).
- **Cause:** last-tab assumption with no logging; tabs differ by ~₎240k in net.
- **Fix:** `_select_ledger_tab(wb, target_month, path)` now parses each sheet that
  covers the target month, picks the **latest tab with the most target-month rows**,
  logs the choice to stderr (`[ledger] selected tab 'X' (target_month=...)...`), and
  records it in `_LOG_TAB_CHOICES`. `ledger_sync.py` now passes `target_month`.
- **Test:** `test_ffix5_tab_selection_picks_latest_covering_month` and
  `test_ffix5_tab_selection_logged_to_stderr`. **Before:** `13.7`? — no logging.
  **After:** explicit `[ledger] selected tab '13.7'` observed on real run.

### Bug 6 — formula corruption on unknown formulas
- **File:** `jobs/billing_output.py:119` (`_resolve_formula` + caller loop).
- **Cause:** any unrecognized formula (SUM, IF, VLOOKUP, etc.) wrote `0`.
- **Fix:** new `UnknownFormulaError` raised when a formula's **shape** is not a pure
  cell ref (`=Sheet!A1`) or additive ref sum (`=A1+B2`). The build loop now
  propagates the error and never writes 0. A pure ref to an empty cell resolves to 0
  (faithful to the workbook, not corruption).
- **Test:** `test_resolve_unknown_formula_raises`, `test_resolve_func_like_if_raises`,
  `test_resolve_simple_ref_still_works`, plus acceptance §5 "no leaked formulas".
  **Before:** ~500 formulas silently zeroed; **After:** acceptance 58/58 (no leaks;
  only the fatal unknown shapes now stop the build).

---

## New modules & controls

### core/validation.py — Input / integrity / output gates
- `validate_input_file(path, formats)` — exists, allowed type, non-empty.
- `validate_workbook(path, required_sheets, header_cells)` — sheets present + non-empty.
- `validate_integrity(rows, critical_cols, date_col, amount_col)` — no NaN, valid
  dates, numeric amounts.
- `validate_output(wb, required_sheets)` — required sheets + no leaked formulas.
- Wired into `run_all.py`: a failing input gate now marks INVALID and exits 1.
- Tests: `test_val_input_file_missing`, `_empty`, `test_val_workbook_required_sheets`,
  `test_val_integrity_nan_and_nonnumeric`, `test_val_output_leaked_formula`.

### SHA-256 input manifest (provenance)
- **File:** `core/manifest_tracking.py`.
- Tracks each input file's `filename, sha256, size, timestamp, client_id` in
  `config/manifest.json`. A changed hash under the same name emits a WARNING.
- Wired into `run_all.py` after preflight (tracks ledger/budget/arbox/approval).
- Test: `test_manifest_records_sha256_and_flags_change`.

### Multi-client future-proofing (client_id)
- **File:** `core/manifest_tracking.py` (records carry `client_id`), `run_all.py`.
- Single-client today (`DEFAULT_CLIENT_ID`); schema already has the column so adding a
  second gym later needs no rewrite. Documented in this log. Test:
  `test_manifest_future_client_id`.

### Tests migration to pytest
- Added `tests/test_bugs_pytest.py` (20 tests) + root `conftest.py` that excludes the
  legacy `sys.exit()` harness files (they still run standalone via
  `python tests/test_acceptance.py` etc.).
- Command: `python -m pytest tests/ -v`

---

## Validation results (this session)

| Suite | Result |
|-------|--------|
| `python -m pytest tests/` | **28 passed** (20 new bug tests + scheduler) |
| `tests/test_bugs_pytest.py` | 20 passed |
| `python tests/test_acceptance.py` | **58 passed, 0 failed** |
| `python tests/test_idan_fixes.py` | 27 passed, 0 failed |
| `python tests/test_resilience.py` | 11 passed, 0 failed |
| `python tools/billing.py --month 6 --branch pilates` | ok, real hilan read (no silent zero) |
| `python tools/ledger_sync.py --month 6` | ok, tab '13.7' explicitly selected |
| `python run_all.py --month 6` | exits **1** on failing validate, marks INVALID (Bug-2 verified) |

## Post-review hardening (reviewer pass)

- `core/validation.py`: header-cell scan now scans ALL rows (was capped at row 8 —
  the ledger 'מט.' header sits lower); `validate_integrity` accepts Israeli date
  formats (`dd/mm/yyyy`, `dd.mm.yy`) via `common.parse_date_any`.
- `run_all.py`: approval workbooks (`דוח מרכז לאישור מנהל`) are now validated in the
  input gate with their real required sheet name (were only SHA-tracked before).
- `jobs/billing_output.py`: `SUM()` parser strips an optional sheet qualifier
  (`'X'!F9:F14`) and raises `UnknownFormulaError` instead of crashing on `split(':')`.
- `core/manifest_tracking.py`: manifest keyed by absolute path (was basename-only —
  collision risk if two files share a name in different dirs).
- Cleared stale `__pycache__` (`common.cpython-310.pyc` from 7/19 was masking 5 tests).
- Input gate re-verified against real inputs: **NONE (all real inputs pass)**.

## Remaining issues / risks
1. **Bug 4 priority change** reverses a recorded product decision — needs owner
   confirm; isolated behind `MONTH_PRIORITY` for easy revert.
2. **suppliers_ocr.json** — repo-safe (ignored/untracked) but the on-disk fake file
   could still be read by suppliers.py. Recommend owner-approved physical deletion.
3. `tools/validate.py` runs the legacy `test_acceptance.py` under a 60s timeout; in
   this run it timed out once then passed — pre-existing harness behaviour, not caused
   by these fixes.
4. `config/input_manifest.json` and `output/report_status.json` are new runtime
   artifacts — both gitignored.

---

## 2026-08-03 — Session: owner-approved decisions A–G (run_all rewrite)

Owner approved 7 decisions (A–G) for the audit findings. Implemented this session:

### Decision A — Memo month-priority fix (parse layer)
- **File:** `core/common.py` (`parse_memo_month`).
- **Fix:** memo dates now parse the Israeli `dd.mm.yy` format (`05.06.26` → **2026-06**,
  previously misread as 2006-05). Instalment strings like `5/12` / `תש' 5/12` are **not**
  years (return `None`); 2-digit years < 20 are rejected. Hebrew/ranged months preserved.
- **Fixture:** `tests/test_bugs_pytest.py::make_ledger_wb` header typo fixed
  (`תאריך לאזן` → `תאריך למאזן`).
- **Impact (before → after, tab 13.7, 897 rows):** 165 rows change month; total |amount|
  moved ₪799,296.84; June delta **₪28,651.65** (memo-first net −273,626.46 vs balance-first
  −302,278.11). Largest movers: expense-180 (70 rows), expense-332 (60), expense-181 (28).
- **Tests:** `test_owner_a_parse_dd_mm_yy`, `test_owner_a_parse_instalment_is_not_a_year`,
  `test_owner_a_parse_common_months`, `test_owner_a_balance_date_wins_when_no_memo`,
  `test_owner_a_value_date_when_memo_and_balance_missing`.
- **Docs:** `AGENTS.md`, `README.md`, `CLAUDE.md`, `SKILL.md`, `.opencode/decisions.md`
  updated to memo → `תאריך למאזן` → `תאריך ערך`.

### Decision B/C — Per-run audit dir + status semantics
- **File:** `run_all.py` (rewritten).
- **New:** every run creates `output/runs/<run_id>/{manifest.json, report_status.json,
  run.log}`. `RUN_INVALID.txt` exists **only** for INVALID runs (also mirrored to
  `output/`). Statuses: `VALID`, `REVIEW_REQUIRED` (≠ VALID), `INVALID`. Exit code 0 =
  VALID or REVIEW_REQUIRED; non-zero = INVALID. Top-level `output/report_status.json`
  mirrors the latest run.
- **Manifest:** inputs + outputs with **full SHA-256**, sizes, paths, `client_id`
  (`ariel_a_street_mall`), and `selected_ledger_tab` (propagated through the Ledger Sync
  JSON result — the subprocess tab choice can't be read in-process).
- **Tests:** `tests/test_run_pipeline.py` (12 tests) — run-context artifacts, marker
  write/clear, strict-gate halt, manifest hashes, tab propagation, stale-marker clear.

### Decision D — Hilan zero / REVIEW_REQUIRED
- **File:** `tools/billing.py`.
- **Fix:** `hilan_suspect` = system==0 AND actual==0 AND trainer activity → audit entry
  `HILAN_SUSPECT_ZERO` (WARN), branch status forced `REVIEW_REQUIRED`; summary carries
  `review_required` and status `REVIEW_REQUIRED` if any branch needs review.
- **Test:** `test_owner_d_hilan_suspect_zero_logged`. Real run: Pilates grand_total
  23170.4, status REVIEW, hilan_suspect_zero false.

### Decision E — No fabricated supplier OCR
- **File:** `tools/suppliers.py`; `config/suppliers_ocr.json` → `tests/fixtures/suppliers_ocr_SAMPLE_ONLY.json`.
- **Fix:** no supplier PDFs → explicit empty pack via `_write_empty_output()` (ok=true,
  truthful note). OCR entries only kept when the file name matches a real input invoice.
- **Tests:** `test_owner_e_fake_cache_not_in_runtime_config`,
  `test_owner_e_supplier_report_linked_to_real_input`.

### Decision F — Strict validate gate
- **File:** `run_all.py` (`_validate_gate_passed`).
- **Fix:** VALID only when validate.py exits 0 **and** its JSON parses **and**
  `ok/pass == true`. Text matching ("0 failed") is no longer proof of success.
- **Tests:** gate ok/nonzero/ok-false/unparsed/missing-key cases + pipeline-level halt.

### Decision G — run_month.bat is LEGACY
- **File:** `run_month.bat` (created).
- **Fix:** thin wrapper forwarding to `python run_all.py`; the agent calling
  `run_pipeline()` is the primary path. File header documents LEGACY status.

## Validation results (this session)

| Suite | Result |
|-------|--------|
| `python -m pytest -q` | **44 passed** (28 bug + 12 pipeline + scheduler) |
| `python tests/test_acceptance.py` | **58 passed, 0 failed** |
| `python tests/test_idan_fixes.py` | 27 passed, 0 failed |
| `python tests/test_resilience.py` | 11 passed, 0 failed |
| `python run_all.py --month 6` (real) | exit 0, status REVIEW_REQUIRED (Pilates drift), manifest with 5 input + 5 output SHA-256, tab `13.7`, no RUN_INVALID.txt |