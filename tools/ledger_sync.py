"""
tools/ledger_sync.py — Push ledger into budget (overwrite-safe two-layer).
Usage:
  python tools/ledger_sync.py --input ./input --output ./output --month 6 [--branch club|pilates|all]
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
from common import load_json, load_account_map
from ledger import parse_ledger, monthly_movement, _LOG_TAB_CHOICES
import ledger_output as lo

MONTHS_HE = [
    "ינואר", "פברואר", "מרץ", "אפריל", "מאי", "יוני",
    "יולי", "אוגוסט", "ספטמבר", "אוקטובר", "נובמבר", "דצמבר",
]


def main():
    parser = argparse.ArgumentParser(description="Ledger sync into budget")
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

    roles = resolve_inputs(input_dir, target_month=args.month)
    if not roles.get("ledger"):
        result = {"ok": False, "error": "Ledger file not found in input"}
        print(json.dumps(result, ensure_ascii=False))
        sys.exit(1)

    if not roles.get("budget"):
        result = {"ok": False, "error": "Budget file not found in input"}
        print(json.dumps(result, ensure_ascii=False))
        sys.exit(1)

    am = load_account_map()
    try:
        txns, subtotals = parse_ledger(roles["ledger"], target_month=month_key)
        movement, unmapped = monthly_movement(txns, am)
    except Exception as e:
        movement, unmapped = {}, []
        print(f"[ledger] No separate ledger transactions found ({e}) — using budget actuals directly", file=sys.stderr)


    branches = load_json("branches.json")["branches"]
    results = {}

    for bk in branches:
        if target_branch and bk != target_branch:
            continue

        branch_file_key = "פילאטיס" if bk == "פילאטיס" else "חדר_כושר"
        out_path = os.path.join(output_dir, f"תקציב_מול_ביצוע_{branch_file_key}.xlsx")

        n = lo.build(roles["budget"], bk, movement, out_path, month_he, month_key)

        results[bk] = {
            "label": branches[bk]["label"],
            "n_cells_written": n,
            "output_path": out_path,
        }

    summary = {
        "ok": True,
        "branches": results,
        "n_unmapped_accounts": len(unmapped),
        "unmapped_accounts": list(unmapped)[:50] if unmapped else [],
        "selected_ledger_tab": _LOG_TAB_CHOICES[-1].get("tab") if _LOG_TAB_CHOICES else None,
    }
    print(json.dumps(summary, ensure_ascii=False))


if __name__ == "__main__":
    main()
