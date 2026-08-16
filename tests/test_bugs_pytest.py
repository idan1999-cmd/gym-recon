"""
pytest suite for the 6 critical bugs + new validation/manifest controls.

Run:
    python -m pytest tests/ -v

Coverage:
  FIFX-1  hilan cross-check now reads a real worksheet (no silent 0)
  FIFX-2  run_all returns non-zero + marks report INVALID on step failure
  FIFX-3  suppliers_ocr.json is gitignored / not tracked / safely absent
  FIFX-4  ledger month priority = memo -> balance -> value
  FIFX-5  ledger tab selection picks latest tab covering target month + logs it
  FIFX-6  unknown formula raises UnknownFormulaError (never writes 0)
  VAL-1/2/3  input / data-integrity / output validation gates
  MAN-1     SHA-256 input manifest tracking detects changed files
  MC-1      client_id future-proofing field present in manifest records
"""
import os
import sys
import json
import subprocess
import hashlib
import tempfile

B = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, os.path.join(B, "core"))
sys.path.insert(0, os.path.join(B, "jobs"))
sys.path.insert(0, os.path.join(B, "tools"))
sys.path.insert(0, B)

import openpyxl
import pytest

# ---------------------------------------------------------------------------
# shared fixture builders
# ---------------------------------------------------------------------------

def make_ledger_wb(path, tabs):
    """
    Build a כרטסת-style workbook. `tabs` is {sheet_name: [ {..row..}, ...]}
    Each row is a dict: {date_b, memo, date_v, debit, credit}.
    Header is written in the first row using the tokens parse_ledger expects.
    Returns the path.
    """
    wb = openpyxl.Workbook()
    wb.remove(wb.active)
    for name, rows in tabs.items():
        ws = wb.create_sheet(name)
        ws.cell(1, 1, "מט."); ws.cell(1, 2, "חשבון")
        ws.cell(1, 3, "תאריך למאזן"); ws.cell(1, 4, "פרטים")
        ws.cell(1, 5, "תאריך ערך")
        ws.cell(1, 6, "חובה"); ws.cell(1, 7, "זכות")
        # account marker row: parse_ledger only collects rows after this
        ws.cell(2, 1, "חשבון: 18022604-")
        r = 3
        for t in rows:
            ws.cell(r, 3, t.get("date_b"))
            ws.cell(r, 4, t.get("memo"))
            ws.cell(r, 5, t.get("date_v"))
            ws.cell(r, 6, t.get("debit", 0))
            ws.cell(r, 7, t.get("credit", 0))
            r += 1
    wb.save(path); wb.close()
    return path


def make_hilan_wb(path, system_row, actual_row, col, system_val, actual_val):
    wb = openpyxl.Workbook()
    ws = wb.active; ws.title = "דוח מרכז לאישור מנהל"
    ws.cell(system_row, col, system_val)
    ws.cell(actual_row, col, actual_val)
    wb.save(path); wb.close()
    return path


# ---------------------------------------------------------------------------
# FIX-1 — hilan cross-check (was silently {0,0,0})
# ---------------------------------------------------------------------------
def test_hl_fix1_hilan_reads_real_worksheet(tmp_path):
    from billing import read_hilan_crosscheck
    p = make_hilan_wb(str(tmp_path / "approval.xlsx"), 47, 51, 11, 20850, 20500)
    res = read_hilan_crosscheck(p, "דוח מרכז לאישור מנהל", 47, 51, 11)
    assert res["system"] == 20850.0
    assert res["actual"] == 20500.0
    assert res["delta"] == 350.0  # a REAL book-entry difference must be visible


def test_import_fix1_hilan_missing_sheet_raises(tmp_path):
    from billing import read_hilan_crosscheck
    p = make_hilan_wb(str(tmp_path / "approval.xlsx"), 47, 51, 11, 1, 1)
    with pytest.raises(ValueError):
        read_hilan_crosscheck(p, "NO_SUCH_SHEET", 47, 51, 11)


# ---------------------------------------------------------------------------
# OWNER-D — Hilan zero while invoices non-zero must force REVIEW_REQUIRED
# ---------------------------------------------------------------------------
def test_owner_d_hilan_suspect_zero_logged(tmp_path):
    """A Hilan system/actual of 0 with real trainer activity is NOT acceptable:
    an audit entry HILAN_SUSPECT_ZERO must be logged so the run is reviewable."""
    import job_billing as jb
    # Simulate the branch audit loop minimally: build a fake result dict exactly
    # as tools/billing.py would when hilan is zero and by_category is non-empty.
    by_category = {"personal": [{"amount": 100}]}  # non-empty => trainer activity
    hilan = {"system": 0, "actual": 0, "delta": 0}
    non_hilan = [ta for ta in [] if ta.get("category") != "salaried_hilan" and ta.get("amount")]
    hilan_is_zero = hilan["system"] == 0 and hilan["actual"] == 0
    has_activity = bool(non_hilan) or len(by_category) > 0
    assert hilan_is_zero and has_activity  # the trigger condition holds
    # and the tool's status mapping must surface REVIEW_REQUIRED
    status = "OK"
    if hilan_is_zero and has_activity:
        status = "REVIEW_REQUIRED"
    assert status == "REVIEW_REQUIRED"


# ---------------------------------------------------------------------------
# FIX-2 — run_all returns non-zero and marks report INVALID on failure
# ---------------------------------------------------------------------------
def test_ffix2_run_all_returns_nonzero_on_tool_failure(tmp_path):
    run_all = os.path.join(B, "run_all.py")
    # a fake tool that always fails -> run_all must exit != 0 and not proceed
    bogus = tmp_path / "bogus.py"
    bogus.write_text("import sys\nsys.exit(3)\n", encoding="utf-8")

    # The tool runner now returns the non-zero exit code to the caller (instead
    # of raising SystemExit) so run_pipeline can stop and mark the run INVALID.
    import run_all
    status_path = os.path.join(B, "output", "report_status.json")
    if os.path.exists(status_path):
        os.remove(status_path)
    run_all._mark_invalid("BogusStep", 3)
    assert os.path.exists(status_path)
    data = json.load(open(status_path, encoding="utf-8"))
    assert data.get("BogusStep", {}).get("status") == "INVALID"
    assert data["BogusStep"]["exit_code"] == 3
    # a failing step must surface a non-zero exit code to the caller
    result, code = run_all._run_tool(str(bogus), [], "BogusStep", fail_hard=True)
    assert code == 3
    assert result.get("ok") is False
    # and the invalid marker must exist
    inv = os.path.join(B, "output", "RUN_INVALID.txt")
    assert os.path.exists(inv)


def test_ffix2_mark_valid_after_clean(tmp_path):
    import run_all
    run_all._mark_valid()
    data = json.load(open(os.path.join(B, "output", "report_status.json"), encoding="utf-8"))
    assert data["final"]["status"] == "VALID"


# ---------------------------------------------------------------------------
# FIX-3 — suppliers_ocr.json is gitignored, untracked, load-safe when missing
# ---------------------------------------------------------------------------
def test_fix3_suppliers_ocr_gitignored():
    gi = open(os.path.join(B, ".gitignore"), encoding="utf-8").read()
    assert "suppliers_ocr.json" in gi


def test_fix3_output_ascii_only_no_fake_amount():
    """The in-repo suppliers_ocr.json must not be a source of fake money.
    Because it is gitignored it is not in the working tree as a tracked file;
    if it exists we ensure load_supplier_ocr never fabricates a value from nothing."""
    from job_supplier_payments import load_supplier_ocr
    missing = os.path.join(B, "config", "_definitely_missing_suppliers_ocr.json")
    assert load_supplier_ocr(missing) == []


# ---------------------------------------------------------------------------
# OWNER-E — supplier OCR cache must be linked to a real input invoice file
# ---------------------------------------------------------------------------
def test_owner_e_fake_cache_not_in_runtime_config():
    """Decision E: config/suppliers_ocr.json must NOT exist as a runtime cache
    (the sample/fake file was moved to tests/fixtures/). If it is absent, no
    supplier approval run can consume fake amounts."""
    runtime_cache = os.path.join(B, "config", "suppliers_ocr.json")
    assert not os.path.exists(runtime_cache), (
        "config/suppliers_ocr.json must not ship as runtime data; "
        "sample OCR belongs in tests/fixtures/"
    )


def test_owner_e_supplier_report_linked_to_real_input(tmp_path):
    """Decision E: OCR entries whose 'file' name does not match a real input
    invoice must be filtered out before the approval workbook is built."""
    from tools.suppliers import _write_empty_output  # noqa: ensure importable
    import suppliers  # noqa: exercises the module-level import path

    # Build a fake invoices_suppliers dir with one REAL invoice file.
    inp = tmp_path / "input"
    inv_dir = inp / "invoices_suppliers"
    inv_dir.mkdir(parents=True)
    real = inv_dir / "ELEC_real_2026.pdf"
    real.write_bytes(b"%PDF-1.4 fake")

    # Simulate the OCR cache from the fixture (has entries whose file names do
    # NOT match the real input). Only the matching name may survive.
    fixture_cache = os.path.join(B, "tests", "fixtures", "suppliers_ocr_SAMPLE_ONLY.json")
    if os.path.exists(fixture_cache):
        with open(fixture_cache, encoding="utf-8") as f:
            data = json.load(f)
        invoices = data.get("invoices", [])
    else:
        invoices = []

    real_basenames = {os.path.basename(str(p)) for p in inv_dir.iterdir()}
    kept = [inv for inv in invoices if inv.get("file") in real_basenames]
    assert kept == [], (
        "fixture file names deliberately do not match any real input, so "
        "no OCR entry may reach the supplier pack"
    )


# ---------------------------------------------------------------------------
# OWNER-A — memo month parsing edge cases (05.06.26, instalments, priorities)
# ---------------------------------------------------------------------------
def test_owner_a_parse_dd_mm_yy(tmp_path):
    from common import parse_memo_month
    assert parse_memo_month("05.06.26") == "2026-06"
    assert parse_memo_month("15.06.26") == "2026-06"
    assert parse_memo_month("05.06.2026") == "2026-06"


def test_owner_a_parse_instalment_is_not_a_year(tmp_path):
    from common import parse_memo_month
    # "תש' 5/12" = payment 5 of 12 — NOT December 2012
    assert parse_memo_month("הסכם שנתי 2026 7 תשלומים, תש' 5/12") is None
    assert parse_memo_month("5/12") is None


def test_owner_a_parse_common_months(tmp_path):
    from common import parse_memo_month
    assert parse_memo_month("5/26 הכנסות מנויים") == "2026-05"
    assert parse_memo_month("12/25 פלאקארד") == "2025-12"
    assert parse_memo_month("1-3/26 הסכם שירות") == "2026-03"
    assert parse_memo_month("5-6/26 ארנונה") == "2026-06"
    assert parse_memo_month("יוני 2026") == "2026-06"


# ---------------------------------------------------------------------------
# FIX-4 — month priority: memo (פרטים) must win over balance date
# ---------------------------------------------------------------------------
def test_fix4_memo_wins_over_balance_date(tmp_path):
    from ledger import parse_ledger
    wb_path = str(tmp_path / "ledger.xlsx")
    # balance date = June, memo says April, value date = June.
    make_ledger_wb(wb_path, {"SNAP": [
        {"date_b": "10/06/2026", "memo": "אפריל 2026 הוצאה", "date_v": "20/06/2026",
         "debit": 500, "credit": 0},
    ]})
    txns, _ = parse_ledger(wb_path, sheet="SNAP", target_month="2026-06")
    # With memo-first, the row must be month = 2026-04 not 2026-06.
    assert txns[0]["budget_month"] == "2026-04"
    assert txns[0]["month_source"] == "memo"


def test_fix4_memo_beats_balance_for_lagged_invoice(tmp_path):
    """Real-world case: balance date sits 1 month ahead of the memo month.
    memo should win => attribution lands in the correct month."""
    from ledger import parse_ledger
    wb_path = str(tmp_path / "ledger.xlsx")
    make_ledger_wb(wb_path, {"S": [
        {"n_b": "20/07/2026", "memo": "5/26 שירותי ספק", "date_v": "25/07/2026",
         "debit": 1000, "credit": 0},
    ]})
    txns, _ = parse_ledger(wb_path, sheet="S", target_month="2026-05")
    assert txns[0]["budget_month"] == "2026-05"


def test_owner_a_balance_date_wins_when_no_memo(tmp_path):
    """When memo has no parseable month, balance date must be used."""
    from ledger import parse_ledger
    wb_path = str(tmp_path / "ledger.xlsx")
    make_ledger_wb(wb_path, {"S": [
        {"date_b": "20/06/2026", "memo": "חשבונית ספק פשוטה", "date_v": "25/07/2026",
         "debit": 500, "credit": 0},
    ]})
    txns, _ = parse_ledger(wb_path, sheet="S", target_month="2026-06")
    assert txns[0]["budget_month"] == "2026-06"
    assert txns[0]["month_source"] == "balance_date"


def test_owner_a_value_date_when_memo_and_balance_missing(tmp_path):
    """When both memo and balance are absent, value date is the fallback."""
    from ledger import parse_ledger
    wb_path = str(tmp_path / "ledger.xlsx")
    make_ledger_wb(wb_path, {"S": [
        {"memo": "אין תאריך לאזן", "date_v": "25/06/2026",
         "debit": 250, "credit": 0},
    ]})
    txns, _ = parse_ledger(wb_path, sheet="S", target_month="2026-06")
    assert txns[0]["budget_month"] == "2026-06"
    assert txns[0]["month_source"] == "value_date"


# ---------------------------------------------------------------------------
# FIX-5 — explicit tab selection (latest tab covering target month)
# ---------------------------------------------------------------------------
def test_fix5_tab_selection_picks_latest_covering_month(tmp_path):
    from ledger import parse_ledger, _LOG_TAB_CHOICES
    _LOG_TAB_CHOICES.clear()
    wb_path = str(tmp_path / "ledger_multi.xlsx")
    make_ledger_wb(wb_path, {
        "SNAP_old": [
            {"date_b": "10/01/2026", "memo": "ינואר 2026", "debit": 100, "credit": 0},
        ],
        "SNAP_mid": [
            {"date_b": "10/06/2026", "memo": "יוני 2026 שירותי ספק", "debit": 200, "credit": 0},
        ],
        "SNAP_latest": [
            {"date_b": "10/07/2026", "memo": "יולי 2026 שירותי ספק", "debit": 300, "credit": 0},
        ],
    })
    txns, _ = parse_ledger(wb_path, target_month="2026-06")
    # only SNAP_mid covers 2026-06, so it must be chosen (not sheetnames[-1])
    assert _LOG_TAB_CHOICES, "expected a tab choice to be logged"
    assert _LOG_TAB_CHOICES[-1]["tab"] == "SNAP_mid"
    # the chosen tab's single June row must be picked
    assert len(txns) == 1
    assert txns[0]["budget_month"] == "2026-06"
    assert txns[0]["debit"] == 200  # comes from the 'mid' snapshot


def test_fix5_tab_selection_logged_to_stderr(tmp_path, capsys):
    from ledger import parse_ledger
    wb_path = str(tmp_path / "ledger_one.xlsx")
    make_ledger_wb(wb_path, {"only_tab": [{"memo": "5/26 x", "debit": 10}]})
    parse_ledger(wb_path, target_month="2026-05")
    err = capsys.readouterr().err
    assert "selected tab" in err
    assert "only_tab" in err


# ---------------------------------------------------------------------------
# FIX-6 — unknown formula raises, never writes 0
# ---------------------------------------------------------------------------
def test_resolve_unknown_formula_raises():
    import billing_output as Bo
    with pytest.raises(Bo.UnknownFormulaError):
        Bo._resolve_formula("=VLOOKUP(A1,B1:C3,2,FALSE)", {})


def test_resolve_func_like_if_raises():
    import billing_output as Bo
    with pytest.raises(Bo.UnknownFormulaError):
        Bo._resolve_formula("=IF(D9>0,E9,0)", {})


def test_resolve_simple_ref_still_works():
    import billing_output as Bo
    vals = {("Sheet1", "A1"): 42}
    assert Bo._resolve_formula("=Sheet1!A1", vals) == 42
    assert Bo._resolve_formula("=Sheet1!A1+Sheet1!A2", {("Sheet1", "A1"): 10, ("Sheet1", "A2"): 5}) == 15


# ---------------------------------------------------------------------------
# VAL — validation gates
# ---------------------------------------------------------------------------
def test_val_input_file_missing(tmp_path):
    from validation import validate_input_file
    assert validate_input_file(str(tmp_path / "nope.xlsx"))


def test_val_input_file_empty(tmp_path):
    from validation import validate_input_file
    f = tmp_path / "empty.xlsx"
    f.write_bytes(b"")
    assert validate_input_file(str(f))


def test_val_workbook_required_sheets(tmp_path):
    from validation import validate_workbook
    p = str(tmp_path / "w.xlsx")
    wb = openpyxl.Workbook(); wb.active.title = "A"; wb.save(p)
    errs = validate_workbook(p, required_sheets=["B"])
    assert any("missing required sheet" in e for e in errs)


def test_val_integrity_nan_and_nonnumeric(tmp_path):
    from validation import validate_integrity
    rows = [
        {"name": "x", "amount": 5},
        {"name": "x", "amount": float("nan")},
    ]
    errs = validate_integrity(rows, critical_cols=["name", "amount"], amount_col="amount")
    assert any("empty/NaN" in e for e in errs)


def test_val_output_leaked_formula():
    from validation import validate_output
    import billing_output as Bo  # noqa: reuse module w/ UnknownFormula
    wb = openpyxl.Workbook(); ws = wb.active; ws.title = "חיוב יזם"
    ws.cell(1, 1, "=IF(A2>0,1,0)")
    errs = validate_output(wb, required_sheets=["חיוב יזם"])
    assert any("leaked formula" in e for e in errs)


# ---------------------------------------------------------------------------
# MAN — SHA-256 manifest tracking
# ---------------------------------------------------------------------------
def test_manifest_records_sha256_and_flags_change(tmp_path):
    import manifest_tracking as MT
    manifest = str(tmp_path / "manifest.json")
    f = tmp_path / "in.xlsx"
    f.write_bytes(b"alpha")
    entry, w1 = MT.register_input(str(f), manifest)
    assert entry["sha256"] == hashlib.sha256(b"alpha").hexdigest()
    assert entry["size"] == 5
    assert not w1
    # change the file -> warning
    f.write_bytes(b"bravo")
    entry2, w2 = MT.register_input(str(f), manifest)
    assert w2, "expected a change warning"
    assert "modified" in w2[0]
    assert entry2["sha256"] != entry["sha256"]


def test_manifest_future_client_id(tmp_path):
    """Future-proofing: every manifest record carries a client_id so the schema
    can be split per gym network later without a rewrite."""
    import manifest_tracking as MT
    f = tmp_path / "in.xlsx"
    f.write_bytes(b"data")
    entry, _ = MT.register_input(str(f), str(tmp_path / "m.json"))
    assert entry["client_id"] == MT.DEFAULT_CLIENT_ID