"""
tools/billing.py — Trainer billing (validate invoices + write Excel).
Usage:
  python tools/billing.py --input ./input --output ./output --month 6 [--branch club|pilates|all]
"""
import sys
import os
import json
import argparse

_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(_root, "core"))
sys.path.insert(0, os.path.join(_root, "jobs"))
sys.path.insert(0, _root)

from inputs import resolve_inputs
from common import load_json, load_aliases, load_pay_matrix
from ocr import load_or_ocr
from arbox import load_sessions
import job_billing as jb
import billing_output as bo

MONTHS_HE = [
    "ינואר", "פברואר", "מרץ", "אפריל", "מאי", "יוני",
    "יולי", "אוגוסט", "ספטמבר", "אוקטובר", "נובמבר", "דצמבר",
]


def _num(x):
    try:
        return float(x)
    except (ValueError, TypeError):
        return 0.0


def read_hilan_crosscheck(wb_path, sheet_name, system_row, actual_row, col):
    """
    Bug-1 fix: read the Hilan cross-check (system vs actual salary) from a
    WORKBOOK's specific WORKSHEET tab.

    Previously the code called .cell() on the Workbook object, which does not
    have a .cell() method, raising AttributeError every run. That exception was
    silently swallowed, so hilan always resolved to {0,0,0} and the cross-check
    always looked "OK".

    This operates on the worksheet (ws[fg]) exactly like openpyxl expects.

    Returns {"system": float, "actual": float, "delta": float} or raises
    ValueError if the sheet is missing — so the caller can STOP the pipeline
    instead of silently passing a fake zero.
    """
    import openpyxl
    wb = openpyxl.load_workbook(wb_path, data_only=True)
    try:
        if sheet_name not in wb.sheetnames:
            raise ValueError(
                f"Hilan cross-check: sheet '{sheet_name}' not found in {wb_path}"
            )
        ws = wb[sheet_name]
        sys_v = ws.cell(system_row, col).value
        act_v = ws.cell(actual_row, col).value
        sys_h = _num(sys_v)
        act_h = _num(act_v)
        delta = abs(sys_h - act_h)
        return {"system": sys_h, "actual": act_h, "delta": round(delta, 2)}
    finally:
        wb.close()


def main():
    parser = argparse.ArgumentParser(description="Trainer billing from invoices")
    parser.add_argument("--input", default="./input", help="Input directory")
    parser.add_argument("--output", default="./output", help="Output directory")
    parser.add_argument("--month", type=int, required=True, help="Month number 1-12")
    parser.add_argument(
        "--branch", default="all", choices=["all", "club", "pilates"],
        help="Branch to process (default: all)"
    )
    args = parser.parse_args()

    month_he = MONTHS_HE[args.month - 1]
    month_key = "2026-%02d" % args.month
    input_dir = os.path.abspath(args.input)
    output_dir = os.path.abspath(args.output)
    os.makedirs(output_dir, exist_ok=True)

    branch_map = {"all": None, "club": "חדר כושר", "pilates": "פילאטיס"}
    target_branch = branch_map[args.branch]

    roles = resolve_inputs(input_dir)
    if not roles.get("arbox"):
        print(json.dumps({"ok": False, "error": "Arbox file not found in input"}, ensure_ascii=False))
        sys.exit(1)

    branches = load_json("branches.json")["branches"]
    aliases = load_aliases()
    pay = load_pay_matrix()

    ocr_path = roles.get("invoices_ocr") or os.path.join(os.path.dirname(output_dir), "config", "invoices_ocr.json")
    invoices = load_or_ocr(roles.get("invoices_dir"), ocr_path)
    if not invoices:
        print(json.dumps({"ok": False, "error": "No invoices found or OCR cache empty"}, ensure_ascii=False))
        sys.exit(1)

    sessions = load_sessions(roles["arbox"], aliases)
    audit_log = []
    results = {}

    for bk, cfg in branches.items():
        if target_branch and bk != target_branch:
            continue

        wb_path = roles["approval"].get(bk)
        if not wb_path:
            audit_log.append({
                "type": "BILLING_SKIP", "branch": bk,
                "note": f"No approval workbook found for {bk}"
            })
            continue

        log = []
        by_category, held, trainer_amounts = jb.validate_invoices(
            invoices, bk, sessions, aliases, pay, log
        )

        branch_file_key = "פילאטיס" if bk == "פילאטיס" else "חדר_כושר"

        hilan = {}
        try:
            hilan = read_hilan_crosscheck(
                wb_path,
                cfg["approval_sheet"],
                cfg["hilan_system_row"],
                cfg["hilan_actual_row"],
                cfg["hilan_col"],
            )
        except Exception as e:  # noqa: BLE001 — Bug-1: no longer silently zero
            audit_log.append({
                "type": "HILAN_CROSSCHECK_FAILED",
                "branch": bk,
                "note": f"could not read Hilan cross-check: {e}",
                "severity": "ERROR",
            })
            print(json.dumps({
                "ok": False,
                "branch": bk,
                "error": f"Hilan cross-check failed: {e}",
            }, ensure_ascii=False))
            sys.exit(1)

        trainer_amounts.append({
            "raw_name": "חילנט (שכר, מצטבר לענף)", "trainer_id": None, "tax_id": None,
            "category": "salaried_hilan", "amount": hilan["actual"],
            "source_invoice": None, "service_month": month_key,
        })

        # Owner decision D: a Hilan zero-total while there is real trainer
        # activity must NOT be silently accepted. Set REVIEW_REQUIRED so the
        # agent/owner knows human review is needed before this branch is trusted.
        non_hilan_amounts = [
            ta["amount"] for ta in trainer_amounts
            if ta.get("category") != "salaried_hilan" and ta.get("amount")
        ]
        hilan_is_zero = (hilan["system"] == 0 and hilan["actual"] == 0)
        has_trainer_activity = bool(non_hilan_amounts) or len(by_category) > 0
        hilan_suspect = hilan_is_zero and has_trainer_activity
        if hilan_suspect:
            audit_log.append({
                "type": "HILAN_SUSPECT_ZERO",
                "branch": bk,
                "severity": "WARN",
                "note": "Hilan system/actual totals are 0 while trainer invoices or "
                        "Arbox sessions are non-zero — manual review required",
                "expected": 0,
                "actual": hilan["actual"],
            })

        ta_path = os.path.join(output_dir, f"trainer_amounts_{branch_file_key}.json")
        json.dump(trainer_amounts, open(ta_path, "w", encoding="utf-8"), ensure_ascii=False, indent=2)

        new_trainers = [e["proposal"] for e in log
                        if e.get("type") == "UNMAPPED_NAME" and e.get("proposal")]

        missing = jb.missing_receipts(bk, sessions, aliases, trainer_amounts, month_key)

        out_path = os.path.join(output_dir, f"חיוב_{branch_file_key}.xlsx")
        total = bo.build(bk, cfg, wb_path, by_category, held, new_trainers,
                         hilan, out_path, cfg["total_target"], missing_receipts=missing,
                         all_sessions=sessions, aliases=aliases)

        status = "OK" if abs(total - cfg["total_target"]) < 0.05 else "REVIEW"
        if hilan_suspect:
            status = "REVIEW_REQUIRED"

        results[bk] = {
            "label": cfg["label"],
            "grand_total": round(total, 2),
            "target": cfg["total_target"],
            "drift": round(total - cfg["total_target"], 2),
            "status": status,
            "hilan_suspect_zero": hilan_suspect,
            "n_held": len(held),
            "n_new_trainers": len(new_trainers),
            "n_missing_receipts": len(missing),
            "output_path": out_path,
            "trainer_amounts_path": ta_path,
        }
        audit_log.extend(log)

    audit_path = os.path.join(output_dir, "audit_log.json")

    existing_log = []
    if os.path.exists(audit_path):
        try:
            existing_log = json.load(open(audit_path, encoding="utf-8"))
            if isinstance(existing_log, dict):
                existing_log = []
        except Exception:
            existing_log = []
    existing_log.extend(audit_log)
    json.dump(existing_log, open(audit_path, "w", encoding="utf-8"), ensure_ascii=False, indent=2)

    review_required = any(
        r.get("status") in ("REVIEW", "REVIEW_REQUIRED") for r in results.values()
    )
    summary = {
        "ok": True,
        "branches": results,
        "audit_log_path": audit_path,
        "n_audit_entries": len(audit_log),
        "review_required": review_required,
        "status": "REVIEW_REQUIRED" if review_required else "VALID",
    }
    print(json.dumps(summary, ensure_ascii=False))


if __name__ == "__main__":
    main()
