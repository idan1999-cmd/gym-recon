#!/usr/bin/env python3
"""
Orchestrator — calls tools in pipeline order.

  python run_all.py --input ./input --output ./output --month 6 [--branch all]

Pipeline: preflight -> ocr (if invoices) -> billing -> ledger_sync -> suppliers -> validate

Owner direction (2026-08):
  * The AGENT is the product. Agents call `run_pipeline()` directly; `run_all.py`
    is only a thin CLI wrapper over it. `run_month.bat` is LEGACY.
  * Every run produces a per-run audit dir:  output/runs/<run_id>/
        manifest.json         (inputs + outputs + their SHA-256 hashes)
        report_status.json    (VALID / REVIEW_REQUIRED / INVALID + step results)
        RUN_INVALID.txt       (ONLY when the run is invalid)
        run.log               (captured tool stdout/stderr)
  * Exit codes reflect reality: 0 = VALID or REVIEW_REQUIRED, non-zero = INVALID.
  * Strict validate gate: a run is VALID only if validate.py exits 0 AND its
    parsed JSON says ok=true AND no required validation gate is missing.
"""
import sys
import os
import json
import argparse
import logging
import subprocess
import datetime

_root = os.path.abspath(os.path.dirname(__file__))
sys.path.insert(0, os.path.join(_root, "core"))
sys.path.insert(0, os.path.join(_root, "jobs"))
sys.path.insert(0, _root)

from inputs import preflight
from manifest_tracking import sha256_of_file
from validation import validate_input_file, validate_workbook

MONTHS_HE = [
    "ינואר", "פברואר", "מרץ", "אפריל", "מאי", "יוני",
    "יולי", "אוגוסט", "ספטמבר", "אוקטובר", "נובמבר", "דצמבר",
]

log = logging.getLogger("gym-recon.run_all")

# A pipeline run context set by run_pipeline(); module-level helpers write per-run
# artifacts when it is set, and fall back to top-level output/ when called
# directly (kept for the unit tests / agent convenience).
_CURRENT_RUN = None


# ---------------------------------------------------------------------------
# run context: per-run audit dir under output/runs/<run_id>/
# ---------------------------------------------------------------------------
class RunContext:
    def __init__(self, output_dir, run_id):
        self.output_dir = output_dir
        self.run_id = run_id
        self.run_dir = os.path.join(output_dir, "runs", run_id)
        os.makedirs(self.run_dir, exist_ok=True)
        self.steps = {}
        self.review_required = False
        self.status = "VALID"
        self.failed_step = None
        self.exit_code = 0
        self._log_path = os.path.join(self.run_dir, "run.log")
        self.ts = datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ")
        with open(self._log_path, "w", encoding="utf-8") as f:
            f.write(f"# run {run_id} @ {self.ts}\n")

    def log(self, msg):
        line = f"[{self.run_id}] {msg}"
        log.info(line)
        with open(self._log_path, "a", encoding="utf-8") as f:
            f.write(line + "\n")

    def record_step(self, label, ok, exit_code, result=None):
        self.steps[label] = {
            "ok": bool(ok), "exit_code": int(exit_code),
            "result": result if isinstance(result, dict) else {"ok": bool(ok)},
        }

    def mark_invalid(self, label, code):
        self.status = "INVALID"
        self.failed_step = label
        self.exit_code = int(code)
        self.record_step(label, False, code)
        self.log(f"MARK INVALID: step '{label}' exit {code}")
        self._write_status()
        self._write_invalid_marker()

    def mark_valid(self):
        self.status = "REVIEW_REQUIRED" if self.review_required else "VALID"
        self.exit_code = 0
        self.log(f"MARK {self.status}")
        self._write_status()
        self._clear_invalid_marker()

    def _write_status(self):
        payload = {
            "run_id": self.run_id,
            "ts": self.ts,
            "status": self.status,
            "pipeline": "run_all",
            "failed_step": self.failed_step,
            "exit_code": self.exit_code,
            "review_required": self.review_required,
            "steps": self.steps,
        }
        run_path = os.path.join(self.run_dir, "report_status.json")
        with open(run_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
        # mirror a "latest run" pointer at the top of output/ for the agent
        top = os.path.join(self.output_dir, "report_status.json")
        with open(top, "w", encoding="utf-8") as f:
            json.dump({"latest_run": self.run_id, **payload}, f, ensure_ascii=False, indent=2)

    def _write_invalid_marker(self):
        # RUN_INVALID.txt exists ONLY for INVALID runs (owner decision C)
        for p in (os.path.join(self.run_dir, "RUN_INVALID.txt"),
                  os.path.join(self.output_dir, "RUN_INVALID.txt")):
            with open(p, "w", encoding="utf-8") as f:
                f.write(f"THIS RUN IS INVALID ({self.run_id})\n"
                        f"Failed step: {self.failed_step} (exit {self.exit_code})\n"
                        f"Do NOT use output/ from this run.\n")

    def _clear_invalid_marker(self):
        for p in (os.path.join(self.run_dir, "RUN_INVALID.txt"),
                  os.path.join(self.output_dir, "RUN_INVALID.txt")):
            if os.path.exists(p):
                os.remove(p)


# ---------------------------------------------------------------------------
# tool runner
# ---------------------------------------------------------------------------
def _run_tool(tool_script, args_list, label, fail_hard=True, ctx=None):
    """Run one pipeline step, tee stdout/stderr to the run log, and return
    (result_dict, exit_code). If the step fails:
      - mark the run INVALID (per-run report_status.json + RUN_INVALID.txt)
      - if fail_hard, halt the whole pipeline by returning the non-zero code
    """
    cmd = [sys.executable, tool_script] + args_list
    if ctx:
        ctx.log(f"[{label}] Running: {' '.join(cmd)}")
    else:
        log.info(f"[{label}] Running: {' '.join(cmd)}")
    proc = subprocess.run(cmd, capture_output=True, text=True, cwd=_root, timeout=600)
    if ctx:
        ctx.log(proc.stdout)
        if proc.stderr:
            ctx.log("STDERR: " + proc.stderr[:2000])
    else:
        if proc.stdout:
            print(proc.stdout[:2000])
        if proc.stderr:
            print("STDERR:", proc.stderr[:1000])
    try:
        result = json.loads(proc.stdout.strip().split("\n")[-1])
    except (json.JSONDecodeError, IndexError):
        result = {"ok": proc.returncode == 0, "raw_stdout": proc.stdout[:500]}
    if ctx:
        ctx.record_step(label, proc.returncode == 0, proc.returncode, result)
    if proc.returncode != 0:
        if ctx:
            ctx.mark_invalid(label, proc.returncode)
        else:
            _default_mark_invalid(label, proc.returncode)
        if fail_hard:
            return result, proc.returncode
    return result, proc.returncode


def _default_mark_invalid(label, code):
    if _CURRENT_RUN:
        _CURRENT_RUN.mark_invalid(label, code)
    else:
        # no run context (direct helper call from tests) -> write top-level files
        import datetime as _dt
        status_path = os.path.join(_root, "output", "report_status.json")
        status = {"status": "INVALID", "pipeline": "run_all",
                  "failed_step": label, "exit_code": code,
                  "ts": _dt.datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ")}
        prev = {}
        if os.path.exists(status_path):
            try:
                prev = json.load(open(status_path, encoding="utf-8"))
            except Exception:
                prev = {}
        prev.update({label: status})
        os.makedirs(os.path.dirname(status_path), exist_ok=True)
        with open(status_path, "w", encoding="utf-8") as f:
            json.dump(prev, f, ensure_ascii=False, indent=2)
        inv = os.path.join(_root, "output", "RUN_INVALID.txt")
        with open(inv, "w", encoding="utf-8") as f:
            f.write(f"THIS RUN IS INVALID\nFailed step: {label} (exit {code})\n")


def _default_mark_valid():
    if _CURRENT_RUN:
        _CURRENT_RUN.mark_valid()
        return
    import datetime as _dt
    status_path = os.path.join(_root, "output", "report_status.json")
    status = {"status": "VALID", "pipeline": "run_all",
              "ts": _dt.datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ")}
    prev = {}
    if os.path.exists(status_path):
        try:
            prev = json.load(open(status_path, encoding="utf-8"))
        except Exception:
            prev = {}
    prev["final"] = status
    os.makedirs(os.path.dirname(status_path), exist_ok=True)
    with open(status_path, "w", encoding="utf-8") as f:
        json.dump(prev, f, ensure_ascii=False, indent=2)
    inv = os.path.join(_root, "output", "RUN_INVALID.txt")
    if os.path.exists(inv):
        os.remove(inv)


def _mark_invalid(label, code):
    _default_mark_invalid(label, code)


def _mark_valid():
    _default_mark_valid()


# ---------------------------------------------------------------------------
# manifest (per-run)
# ---------------------------------------------------------------------------
def _hash_input(role, path, ctx):
    if not path:
        return None
    return {
        "role": role,
        "filename": os.path.basename(path),
        "path": os.path.abspath(path),
        "sha256": sha256_of_file(path),
        "size": os.path.getsize(path),
    }


def _hash_output(output_dir, filename, ctx):
    p = os.path.join(output_dir, filename)
    if not os.path.exists(p):
        return None
    return {"file": filename, "sha256": sha256_of_file(p),
            "size": os.path.getsize(p)}


def _write_manifest(ctx, roles, inputs, outputs, ledger_tab=None):
    manifest = {
        "run_id": ctx.run_id,
        "ts": ctx.ts,
        "client_id": "ariel_a_street_mall",
        "inputs": inputs,
        "outputs": [o for o in outputs if o],
        "selected_ledger_tab": ledger_tab,
        "config_versions": {
            "engine": "gym-recon",
        },
    }
    with open(os.path.join(ctx.run_dir, "manifest.json"), "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)
    ctx.log(f"manifest written: {ctx.run_dir}/manifest.json")


# ---------------------------------------------------------------------------
# main pipeline
# ---------------------------------------------------------------------------
def run_pipeline(input_dir, output_dir, month=0, branch="all"):
    """
    Run the full month pipeline under a per-run audit dir.
    Returns the exit code: 0 = VALID or REVIEW_REQUIRED, non-zero = INVALID.
    The caller (agent/tool) can inspect output/runs/<run_id>/report_status.json
    for the status, and output/RUN_INVALID.txt to confirm failure.
    """
    global _CURRENT_RUN
    input_dir = os.path.abspath(input_dir)
    output_dir = os.path.abspath(output_dir)
    os.makedirs(output_dir, exist_ok=True)

    run_id = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    ctx = RunContext(output_dir, run_id)
    _CURRENT_RUN = ctx

    month_he = MONTHS_HE[month - 1] if month else None

    try:
        # 1. PREFLIGHT
        ok, lines, roles = preflight(input_dir)
        ctx.log("=== PREFLIGHT ===")
        for line in lines:
            ctx.log(line)

        # 2. INPUT VALIDATION GATE (fail-closed, non-zero)
        for role in ("ledger", "budget", "arbox"):
            path = roles.get(role)
            if not path:
                continue
            errs = validate_input_file(path)
            if not errs:
                errs = validate_workbook(path)
            if errs:
                for e in errs:
                    ctx.log(f"[input-validation] ERROR: {e}")
                ctx.mark_invalid("input:" + role, 1)
                return ctx.exit_code

        # 3. MANIFEST INPUTS (provenance — SHA-256)
        input_entries = []
        for role in ("ledger", "budget", "arbox"):
            ent = _hash_input(role, roles.get(role), ctx)
            if ent:
                input_entries.append(ent)
                ctx.log(f"[manifest] {role}: {ent['filename']} sha256={ent['sha256'][:12]}...")
        for br, path in (roles.get("approval") or {}).items():
            ent = _hash_input("approval:" + br, path, ctx)
            if ent:
                input_entries.append(ent)

        # 4. OCR (only if an invoices folder is present)
        if roles.get("invoices_dir"):
            result, code = _run_tool(
                os.path.join(_root, "tools", "ocr_gemini.py"),
                ["--invoices", roles["invoices_dir"],
                 "--output", os.path.join(_root, "config", "invoices_ocr.json")],
                "OCR", fail_hard=False, ctx=ctx)
            if code != 0:
                ctx.mark_invalid("OCR", code)
                return ctx.exit_code
        else:
            ctx.log("[OCR] No invoices folder — skipping")

        # 5. BILLING
        if roles.get("arbox") and any(roles.get("approval", {}).values()):
            result, code = _run_tool(
                os.path.join(_root, "tools", "billing.py"),
                ["--input", input_dir, "--output", output_dir,
                 "--month", str(month), "--branch", branch],
                "Billing", fail_hard=False, ctx=ctx)
            if code != 0:
                ctx.mark_invalid("Billing", code)
                return ctx.exit_code
            # REVIEW_REQUIRED from billing flags review state (owner decision C/D)
            for br, bres in (result.get("branches") or {}).items():
                if bres.get("status") in ("REVIEW", "REVIEW_REQUIRED"):
                    ctx.review_required = True
                    ctx.log(f"[billing] branch {br}: {bres.get('status')} — human review needed")
        else:
            ctx.log("[Billing] Missing Arbox or approval workbooks — skipping")

        # 6. LEDGER SYNC
        ledger_tab = None
        if roles.get("ledger") and roles.get("budget"):
            result, code = _run_tool(
                os.path.join(_root, "tools", "ledger_sync.py"),
                ["--input", input_dir, "--output", output_dir,
                 "--month", str(month), "--branch", branch],
                "Ledger Sync", fail_hard=False, ctx=ctx)
            if code != 0:
                ctx.mark_invalid("Ledger Sync", code)
                return ctx.exit_code
            ledger_tab = (result or {}).get("selected_ledger_tab")
            ctx.log(f"[ledger] selected tab: {ledger_tab}")
        else:
            ctx.log("[Ledger] Missing ledger or budget — skipping")

        # 7. SUPPLIERS (only if real supplier PDFs exist; suppliers.py is itself
        #    guarded against fabricated OCR data — owner decision E)
        supplier_invoices_dir = os.path.join(input_dir, "invoices_suppliers")
        has_supplier_pdfs = os.path.isdir(supplier_invoices_dir) and any(
            f.lower().endswith((".pdf", ".png", ".jpg", ".jpeg"))
            for f in os.listdir(supplier_invoices_dir)
        )
        if has_supplier_pdfs:
            result, code = _run_tool(
                os.path.join(_root, "tools", "suppliers.py"),
                ["--input", input_dir, "--output", output_dir,
                 "--month", str(month)],
                "Suppliers", fail_hard=False, ctx=ctx)
            if code != 0:
                ctx.mark_invalid("Suppliers", code)
                return ctx.exit_code
        else:
            ctx.log("[Suppliers] No real supplier invoice files — skipping")

        # 8. VALIDATE — STRICT GATE (owner decision F)
        result, code = _run_tool(
            os.path.join(_root, "tools", "validate.py"),
            ["--output", output_dir],
            "Validate", fail_hard=False, ctx=ctx)
        valid = _validate_gate_passed(result, code)
        if not valid:
            ctx.log("[Validate] STRICT GATE FAILED — run is INVALID")
            ctx.mark_invalid("Validate", code if code else 1)
            return ctx.exit_code

        # 9. MANIFEST OUTPUTS (hashes of deliverables)
        outputs = [
            _hash_output(output_dir, "תקציב_מול_ביצוע_חדר_כושר.xlsx", ctx),
            _hash_output(output_dir, "תקציב_מול_ביצוע_פילאטיס.xlsx", ctx),
            _hash_output(output_dir, "חיוב_חדר_כושר.xlsx", ctx),
            _hash_output(output_dir, "חיוב_פילאטיס.xlsx", ctx),
            _hash_output(output_dir, "ספקים_לאישור_מנהל.xlsx", ctx),
        ]
        _write_manifest(ctx, roles, input_entries, outputs, ledger_tab=ledger_tab)

        # 10. FINAL STATUS
        ctx.mark_valid()
        ctx.log("Done. Check output/ folder and sheets דגלים / דגלים ספקים.")
        ctx.log(f"Status: {ctx.status} (exit {ctx.exit_code})")
        return ctx.exit_code

    except SystemExit as e:
        ctx.mark_invalid("pipeline", int(getattr(e, "code", 1)))
        return ctx.exit_code
    except Exception as e:  # noqa: BLE001 — any unhandled error fails the run
        ctx.log(f"[pipeline] UNHANDLED EXCEPTION: {e}")
        ctx.mark_invalid("pipeline", 2)
        return ctx.exit_code
    finally:
        _CURRENT_RUN = None


def _validate_gate_passed(result, code):
    """Strict validation gate (owner decision F):
    VALID only when validate.py exited 0 AND its JSON parsed AND ok==true.
    Text matching like '0 failed' is NOT proof of success."""
    if code != 0:
        return False
    if not isinstance(result, dict):
        return False
    if result.get("ok") is not True and result.get("pass") is not True:
        return False
    return True


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", default="./input")
    ap.add_argument("--output", default="./output")
    ap.add_argument("--month", type=int, default=0)
    ap.add_argument("--branch", default="all", choices=["all", "club", "pilates"])
    args = ap.parse_args()

    month = args.month
    if month == 0:
        month = (datetime.datetime.now().replace(day=1) - datetime.timedelta(days=1)).month
        print(f"[RunAll] No --month given, defaulting to previous month: {month} ({MONTHS_HE[month-1]})")
    else:
        print(f"[RunAll] Month: {month} ({MONTHS_HE[month-1]})")

    code = run_pipeline(args.input, args.output, month=month, branch=args.branch)
    sys.exit(code)


if __name__ == "__main__":
    main()
