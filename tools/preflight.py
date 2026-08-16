"""
tools/preflight.py — Check input readiness.
Usage: python tools/preflight.py --input ./input
"""
import sys
import os
import json
import argparse

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from core.inputs import preflight


def main():
    parser = argparse.ArgumentParser(description="Preflight: check input readiness")
    parser.add_argument("--input", default="./input", help="Input directory")
    args = parser.parse_args()

    input_dir = os.path.abspath(args.input)
    if not os.path.isdir(input_dir):
        result = {"ok": False, "error": f"Input directory not found: {input_dir}"}
        print(json.dumps(result, ensure_ascii=False))
        sys.exit(1)

    ok, lines, roles = preflight(input_dir)

    print("=== PREFLIGHT ===")
    print("\n".join(lines))
    print("=================")

    result = {
        "ok": ok,
        "ledger": bool(roles.get("ledger")),
        "budget": bool(roles.get("budget")),
        "arbox": bool(roles.get("arbox")),
        "approval_filates": bool(roles.get("approval", {}).get("פילאטיס")),
        "approval_club": bool(roles.get("approval", {}).get("חדר כושר")),
        "invoices_dir": bool(roles.get("invoices_dir")),
        "invoices_ocr": bool(roles.get("invoices_ocr")),
        "notes": roles.get("notes", []),
    }
    print(json.dumps(result, ensure_ascii=False))
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
