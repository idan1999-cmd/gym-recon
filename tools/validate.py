"""
tools/validate.py — Run acceptance tests + output validation.
Usage:
  python tools/validate.py [--output ./output]
"""
import sys
import os
import json
import argparse
import subprocess


def main():
    parser = argparse.ArgumentParser(description="Validate gym-recon outputs")
    parser.add_argument("--output", default="./output", help="Output directory to check")
    args = parser.parse_args()

    output_dir = os.path.abspath(args.output)
    root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

    results = {"tests": [], "output_validation": [], "pass": True}

    # 1) Run acceptance tests
    test_path = os.path.join(root, "tests", "test_acceptance.py")
    if os.path.exists(test_path):
        print("Running acceptance tests...")
        try:
            proc = subprocess.run(
                [sys.executable, test_path],
                capture_output=True, text=True, cwd=root, timeout=60
            )
            print(proc.stdout)
            if proc.stderr:
                print("STDERR:", proc.stderr)
            passed = "0 failed" in proc.stdout
            results["tests"].append({
                "name": "test_acceptance.py",
                "passed": passed,
                "exit_code": proc.returncode,
            })
            if not passed:
                results["pass"] = False
        except Exception as e:
            results["tests"].append({
                "name": "test_acceptance.py",
                "passed": False,
                "error": str(e),
            })
            results["pass"] = False
    else:
        results["tests"].append({
            "name": "test_acceptance.py",
            "skipped": "file not found",
        })

    # 2) Check output xlsx exist
    required_outputs = [
        "תקציב_מול_ביצוע_פילאטיס.xlsx",
        "תקציב_מול_ביצוע_חדר_כושר.xlsx",
        "חיוב_פילאטיס.xlsx",
        "חיוב_חדר_כושר.xlsx",
    ]
    for fname in required_outputs:
        fpath = os.path.join(output_dir, fname)
        exists = os.path.exists(fpath)
        results["output_validation"].append({
            "file": fname,
            "exists": exists,
        })
        if not exists:
            results["pass"] = False
            print(f"  FAIL  {fname} not found in output")

    # 3) Check audit_log.json
    audit_path = os.path.join(output_dir, "audit_log.json")
    if os.path.exists(audit_path):
        try:
            audit_data = json.load(open(audit_path, encoding="utf-8"))
            results["output_validation"].append({
                "file": "audit_log.json",
                "exists": True,
                "entries": len(audit_data) if isinstance(audit_data, list) else 0,
            })
        except Exception:
            results["output_validation"].append({
                "file": "audit_log.json",
                "exists": True,
                "error": "invalid JSON",
            })
            results["pass"] = False
    else:
        results["output_validation"].append({
            "file": "audit_log.json",
            "exists": False,
        })
        if not results.get("skipped_output_check"):
            results["pass"] = False

    # 4) Check supplier output if expected
    supplier_out = os.path.join(output_dir, "ספקים_לאישור_מנהל.xlsx")
    # Also check config/suppliers_ocr.json to know if supplier processing is expected
    config_dir = os.path.join(root, "config")
    supplier_cache = os.path.join(config_dir, "suppliers_ocr.json")
    if os.path.exists(supplier_out):
        results["output_validation"].append({
            "file": "ספקים_לאישור_מנהל.xlsx",
            "exists": True,
        })
        print(f"  PASS  ספקים_לאישור_מנהל.xlsx found")
    elif os.path.exists(supplier_cache):
        # Supplier cache exists but output missing — flag it
        results["output_validation"].append({
            "file": "ספקים_לאישור_מנהל.xlsx",
            "exists": False,
            "expected": True,
            "note": "suppliers_ocr.json exists but output not generated"
        })
        print(f"  WARN  ספקים_לאישור_מנהל.xlsx expected (suppliers_ocr.json exists) but not found")

    # 5) Check trainer_amounts json files
    for suffix in ["חדר_כושר", "פילאטיס"]:
        ta_path = os.path.join(output_dir, f"trainer_amounts_{suffix}.json")
        if os.path.exists(ta_path):
            try:
                ta_data = json.load(open(ta_path, encoding="utf-8"))
                results["output_validation"].append({
                    "file": f"trainer_amounts_{suffix}.json",
                    "exists": True,
                    "entries": len(ta_data) if isinstance(ta_data, list) else 0,
                })
            except Exception:
                pass

    print(f"\n{'='*40}")
    total_checks = len(results["tests"]) + len(results["output_validation"])
    passed_checks = sum(
        1 for t in results["tests"] if t.get("passed")
    ) + sum(
        1 for v in results["output_validation"] if v.get("exists")
    )
    print(f"  PASS: {passed_checks}/{total_checks}")
    print(f"  OVERALL: {'PASS' if results['pass'] else 'FAIL'}")
    print(json.dumps(results, ensure_ascii=False))
    sys.exit(0 if results['pass'] else 1)


if __name__ == "__main__":
    main()
