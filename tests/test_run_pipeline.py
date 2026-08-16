"""
pytest for run_pipeline() per-run audit structure and strict validation.

Owner decisions covered:
  B — output/runs/<run_id>/{manifest.json, report_status.json, RUN_INVALID.txt, run.log}
  C — RUN_INVALID.txt only for INVALID; report_status VALID/REVIEW_REQUIRED/INVALID;
      failed run returns non-zero exit code
  F — strict validate gate (exit 0 AND parsed ok==true, no text matching)

Run:  python -m pytest tests/test_run_pipeline.py -v
"""
import os
import sys
import json
import shutil

B = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, os.path.join(B, "core"))
sys.path.insert(0, os.path.join(B, "jobs"))
sys.path.insert(0, os.path.join(B, "tools"))
sys.path.insert(0, B)

import pytest


def _latest_run_dir(output_dir):
    runs = os.path.join(output_dir, "runs")
    if not os.path.isdir(runs):
        return None
    ids = sorted(os.listdir(runs))
    return os.path.join(runs, ids[-1]) if ids else None


def test_validate_gate_ok_dict():
    import run_all
    assert run_all._validate_gate_passed({"ok": True}, 0) is True


def test_validate_gate_nonzero_fails():
    import run_all
    assert run_all._validate_gate_passed({"ok": True}, 1) is False


def test_validate_gate_ok_false_fails():
    import run_all
    assert run_all._validate_gate_passed({"ok": False}, 0) is False


def test_validate_gate_unparsed_fails():
    import run_all
    assert run_all._validate_gate_passed({"raw_stdout": "0 failed"}, 0) is False


def test_validate_gate_missing_keys_fails():
    import run_all
    # {ok:...} present but no pass/ok truthy => not valid
    assert run_all._validate_gate_passed({"foo": 1}, 0) is False


def test_run_context_creates_per_run_dir(tmp_path):
    import run_all
    ctx = run_all.RunContext(str(tmp_path), "20260803-120000")
    assert os.path.isdir(ctx.run_dir)
    assert os.path.exists(os.path.join(ctx.run_dir, "run.log"))
    # VALID runs must not leave RUN_INVALID.txt
    ctx.mark_valid()
    assert not os.path.exists(os.path.join(ctx.run_dir, "RUN_INVALID.txt"))
    assert not os.path.exists(os.path.join(tmp_path, "RUN_INVALID.txt"))


def test_run_context_invalid_writes_marker(tmp_path):
    import run_all
    ctx = run_all.RunContext(str(tmp_path), "20260803-120001")
    ctx.mark_invalid("Billing", 3)
    assert os.path.exists(os.path.join(ctx.run_dir, "RUN_INVALID.txt"))
    # owner decision C: the human marker must exist only for INVALID runs
    assert os.path.exists(os.path.join(tmp_path, "RUN_INVALID.txt"))
    # report_status.json must say INVALID with a non-zero exit code
    data = json.load(open(os.path.join(ctx.run_dir, "report_status.json"), encoding="utf-8"))
    assert data["status"] == "INVALID"
    assert data["exit_code"] == 3
    assert data["failed_step"] == "Billing"


def test_run_context_review_required_semantics(tmp_path):
    import run_all
    ctx = run_all.RunContext(str(tmp_path), "20260803-120002")
    ctx.review_required = True
    ctx.mark_valid()
    data = json.load(open(os.path.join(ctx.run_dir, "report_status.json"), encoding="utf-8"))
    # REVIEW_REQUIRED is NOT equivalent to VALID (owner decision C)
    assert data["status"] == "REVIEW_REQUIRED"
    assert data["exit_code"] == 0  # still a "successful" exit, but needs review


def test_run_context_manifest_written(tmp_path):
    import run_all
    ctx = run_all.RunContext(str(tmp_path), "20260803-120003")
    # fabricate one input + one output for the manifest
    inp = tmp_path / "input" / "ledger.xlsx"
    inp.parent.mkdir(parents=True)
    inp.write_bytes(b"ledger-content")
    out = tmp_path / "תקציב_מול_ביצוע_חדר_כושר.xlsx"
    out.write_bytes(b"output-content")
    inputs = [run_all._hash_input("ledger", str(inp), ctx)]
    outputs = [run_all._hash_output(str(tmp_path), "תקציב_מול_ביצוע_חדר_כושר.xlsx", ctx)]
    run_all._write_manifest(ctx, {}, inputs, outputs, ledger_tab="13.7")
    m = json.load(open(os.path.join(ctx.run_dir, "manifest.json"), encoding="utf-8"))
    assert m["run_id"] == "20260803-120003"
    assert m["inputs"][0]["role"] == "ledger"
    assert len(m["inputs"][0]["sha256"]) == 64  # full sha-256 hex
    assert m["selected_ledger_tab"] == "13.7"
    assert m["outputs"][0]["file"] == "תקציב_מול_ביצוע_חדר_כושר.xlsx"
    # multi-client future-proofing: client_id always present
    assert m["client_id"] == "ariel_a_street_mall"


def test_run_pipeline_clears_previous_invalid_marker(tmp_path, monkeypatch):
    """An INVALID run must write the marker; a successful run must remove a
    stale RUN_INVALID.txt from a prior failure."""
    import run_all

    # Stub the heavy/real steps so the test is fast and deterministic:
    # preflight reports one ledger file that FAILS input validation.
    def fake_preflight(input_dir):
        lines = ["x ledger MISSING"]
        roles = {"ledger": str(tmp_path / "nope.xlsx"), "budget": None,
                 "arbox": None, "approval": {}, "invoices_dir": None,
                 "invoices_ocr": None, "notes": []}
        return False, lines, roles

    def fake_run_tool(tool_script, args_list, label, fail_hard=True, ctx=None):
        return {"ok": True}, 0

    monkeypatch.setattr(run_all, "preflight", fake_preflight)
    monkeypatch.setattr(run_all, "_run_tool", fake_run_tool)

    output_dir = str(tmp_path / "output")
    os.makedirs(output_dir, exist_ok=True)
    stale = os.path.join(output_dir, "RUN_INVALID.txt")
    with open(stale, "w", encoding="utf-8") as f:
        f.write("stale")

    # First run: ledger fails input validation -> INVALID, marker present.
    code = run_all.run_pipeline(str(tmp_path / "input"), output_dir, month=6)
    assert code != 0
    assert os.path.exists(stale)
    run_dir = _latest_run_dir(output_dir)
    assert run_dir is not None
    data = json.load(open(os.path.join(run_dir, "report_status.json"), encoding="utf-8"))
    assert data["status"] == "INVALID"
    assert data["failed_step"] == "input:ledger"


def test_run_pipeline_success_marks_valid_and_writes_manifest(tmp_path, monkeypatch):
    """Happy path with no failing inputs: VALID status, per-run manifest with
    SHA-256s, no RUN_INVALID.txt anywhere."""
    import run_all

    # No roles at all -> every tool is skipped except Validate, which we stub.
    def fake_preflight(input_dir):
        roles = {"ledger": None, "budget": None, "arbox": None,
                 "approval": {}, "invoices_dir": None, "invoices_ocr": None,
                 "notes": []}
        return True, ["everything empty"], roles

    calls = []

    def fake_run_tool(tool_script, args_list, label, fail_hard=True, ctx=None):
        calls.append(label)
        if ctx:
            ctx.record_step(label, True, 0, {"ok": True})
        return {"ok": True}, 0

    monkeypatch.setattr(run_all, "preflight", fake_preflight)
    monkeypatch.setattr(run_all, "_run_tool", fake_run_tool)

    output_dir = str(tmp_path / "output")
    input_dir = str(tmp_path / "input")
    os.makedirs(input_dir, exist_ok=True)
    code = run_all.run_pipeline(input_dir, output_dir, month=6)

    assert code == 0
    assert "Validate" in calls  # strict gate must run
    run_dir = _latest_run_dir(output_dir)
    assert run_dir is not None
    data = json.load(open(os.path.join(run_dir, "report_status.json"), encoding="utf-8"))
    assert data["status"] == "VALID"
    assert data["exit_code"] == 0
    assert not os.path.exists(os.path.join(run_dir, "RUN_INVALID.txt"))
    assert not os.path.exists(os.path.join(output_dir, "RUN_INVALID.txt"))
    # manifest with provenance fields
    m = json.load(open(os.path.join(run_dir, "manifest.json"), encoding="utf-8"))
    assert m["run_id"] == data["run_id"]
    assert m["client_id"] == "ariel_a_street_mall"
    assert "outputs" in m
    # validate step must have been recorded in the per-run status
    assert "Validate" in data["steps"]
    assert data["steps"]["Validate"]["ok"] is True


def test_run_pipeline_strict_gate_halts_on_bad_validate(tmp_path, monkeypatch):
    """Owner decision F: if validate.py exits 0 but its JSON says ok=false (or
    is unparseable), the run is INVALID even though no tool crashed."""
    import run_all

    def fake_preflight(input_dir):
        roles = {"ledger": None, "budget": None, "arbox": None,
                 "approval": {}, "invoices_dir": None, "invoices_ocr": None,
                 "notes": []}
        return True, [], roles

    def fake_run_tool(tool_script, args_list, label, fail_hard=True, ctx=None):
        # validate exits 0 but reports ok=false -> strict gate must fail it
        return {"ok": False, "raw_stdout": "0 failed but checksums bad"}, 0

    monkeypatch.setattr(run_all, "preflight", fake_preflight)
    monkeypatch.setattr(run_all, "_run_tool", fake_run_tool)

    output_dir = str(tmp_path / "output")
    input_dir = str(tmp_path / "input")
    os.makedirs(input_dir, exist_ok=True)
    code = run_all.run_pipeline(input_dir, output_dir, month=6)
    assert code != 0
    run_dir = _latest_run_dir(output_dir)
    data = json.load(open(os.path.join(run_dir, "report_status.json"), encoding="utf-8"))
    assert data["status"] == "INVALID"
    assert data["failed_step"] == "Validate"
    assert os.path.exists(os.path.join(output_dir, "RUN_INVALID.txt"))


def test_run_pipeline_ledger_tab_propagates_to_manifest(tmp_path, monkeypatch):
    """The chosen ledger tab must reach the manifest via the Ledger Sync JSON
    result (the subprocess tab choice cannot be read in-process)."""
    import openpyxl
    import run_all

    # real, openable workbooks so the input-validation gate passes
    ledger_p = tmp_path / "ledger.xlsx"
    budget_p = tmp_path / "budget.xlsx"
    for p in (ledger_p, budget_p):
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Sheet1"
        ws.append(["כלום", "חובה", "זכות"])
        wb.save(p)
        wb.close()

    def fake_preflight(input_dir):
        roles = {"ledger": str(ledger_p), "budget": str(budget_p),
                 "arbox": None, "approval": {}, "invoices_dir": None,
                 "invoices_ocr": None, "notes": []}
        return True, [], roles

    def fake_run_tool(tool_script, args_list, label, fail_hard=True, ctx=None):
        if label == "Ledger Sync":
            if ctx:
                ctx.record_step(label, True, 0, {"ok": True})
            return {"ok": True, "selected_ledger_tab": "SNAP_mid"}, 0
        if ctx:
            ctx.record_step(label, True, 0, {"ok": True})
        return {"ok": True}, 0

    monkeypatch.setattr(run_all, "preflight", fake_preflight)
    monkeypatch.setattr(run_all, "_run_tool", fake_run_tool)

    output_dir = str(tmp_path / "output")
    input_dir = str(tmp_path / "input")
    os.makedirs(input_dir, exist_ok=True)
    code = run_all.run_pipeline(input_dir, output_dir, month=6)
    assert code == 0
    run_dir = _latest_run_dir(output_dir)
    m = json.load(open(os.path.join(run_dir, "manifest.json"), encoding="utf-8"))
    assert m["selected_ledger_tab"] == "SNAP_mid"
