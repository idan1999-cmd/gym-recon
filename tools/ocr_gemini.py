"""
tools/ocr_gemini.py — Gemini Vision OCR tool for Hebrew invoices and supplier invoices.
Usage:
  python tools/ocr_gemini.py --invoices ./input/invoices --output ./config/invoices_ocr.json [--force]
  python tools/ocr_gemini.py --suppliers --invoices ./input/invoices_suppliers --output ./config/suppliers_ocr.json [--force]
"""
import sys
import os
import json
import argparse

# Add project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from core.ocr import gemini_available, ocr_with_gemini, load_or_ocr, ocr_suppliers_with_gemini, load_or_ocr_suppliers
import glob

def main():
    parser = argparse.ArgumentParser(description="Gemini Vision OCR for Hebrew invoices and supplier invoices")
    parser.add_argument("--invoices", default="./input/invoices", help="Directory containing invoice files")
    parser.add_argument("--output", default="./config/invoices_ocr.json", help="Output JSON cache path")
    parser.add_argument("--force", action="store_true", help="Force re-OCR even if cache exists")
    parser.add_argument("--suppliers", action="store_true", help="Use supplier invoice OCR schema (reads from input/invoices_suppliers)")
    args = parser.parse_args()

    if args.suppliers:
        _run_supplier_ocr(args)
        return

    invoices_dir = os.path.abspath(args.invoices)
    output_path = os.path.abspath(args.output)

    imgs = []
    if os.path.exists(invoices_dir):
        for ext in ("*.pdf", "*.png", "*.jpg", "*.jpeg"):
            imgs.extend(glob.glob(os.path.join(invoices_dir, ext)))
    imgs = sorted(list(set(imgs)))

    if not imgs and not os.path.exists(output_path):
        res = {
            "ok": True,
            "n_ok": 0,
            "n_fail": 0,
            "failed": [],
            "path": output_path,
            "message": "No invoice images found and no cache exists."
        }
        print(json.dumps(res, ensure_ascii=False))
        return

    if not args.force and os.path.exists(output_path):
        try:
            cache_data = json.load(open(output_path, encoding="utf-8"))
            inv_list = cache_data.get("invoices", []) if isinstance(cache_data, dict) else cache_data
            res = {
                "ok": True,
                "n_ok": len(inv_list),
                "n_fail": 0,
                "failed": [],
                "path": output_path,
                "cached": True
            }
            print(json.dumps(res, ensure_ascii=False))
            return
        except Exception as e:
            pass

    if not gemini_available():
        # Fallback to existing cache if possible, else fail gracefully
        if os.path.exists(output_path):
            try:
                cache_data = json.load(open(output_path, encoding="utf-8"))
                inv_list = cache_data.get("invoices", []) if isinstance(cache_data, dict) else cache_data
                res = {
                    "ok": True,
                    "n_ok": len(inv_list),
                    "n_fail": 0,
                    "failed": [],
                    "path": output_path,
                    "cached": True,
                    "warning": "GEMINI_API_KEY not set; using existing cache"
                }
                print(json.dumps(res, ensure_ascii=False))
                return
            except Exception:
                pass
        
        res = {
            "ok": False,
            "n_ok": 0,
            "n_fail": len(imgs),
            "failed": [os.path.basename(p) for p in imgs],
            "path": output_path,
            "error": "GEMINI_API_KEY environment variable is not set."
        }
        print(json.dumps(res, ensure_ascii=False))
        sys.exit(0) # Exit gracefully with JSON status

    invoices, failed_files = ocr_with_gemini(imgs)
    
    existing_map = {}
    if os.path.exists(output_path) and not args.force:
        try:
            old_data = json.load(open(output_path, encoding="utf-8"))
            old_list = old_data.get("invoices", []) if isinstance(old_data, dict) else old_data
            for inv in old_list:
                if isinstance(inv, dict) and "file" in inv:
                    existing_map[inv["file"]] = inv
        except Exception:
            pass

    for inv in invoices:
        existing_map[inv["file"]] = inv

    final_invoices = list(existing_map.values())
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    json.dump({"invoices": final_invoices}, open(output_path, "w", encoding="utf-8"), ensure_ascii=False, indent=2)

    res = {
        "ok": len(failed_files) == 0,
        "n_ok": len(invoices),
        "n_fail": len(failed_files),
        "failed": [f[0] for f in failed_files],
        "path": output_path
    }
    print(json.dumps(res, ensure_ascii=False))

def _run_supplier_ocr(args):
    """Run supplier-specific OCR pipeline."""
    invoices_dir = os.path.abspath(args.invoices)
    output_path = os.path.abspath(args.output)

    imgs = []
    if os.path.exists(invoices_dir):
        for ext in ("*.pdf", "*.png", "*.jpg", "*.jpeg"):
            imgs.extend(glob.glob(os.path.join(invoices_dir, ext)))
    imgs = sorted(list(set(imgs)))

    if not imgs and not os.path.exists(output_path):
        res = {
            "ok": True,
            "n_ok": 0,
            "n_fail": 0,
            "failed": [],
            "path": output_path,
            "message": "No supplier invoice images found and no cache exists."
        }
        print(json.dumps(res, ensure_ascii=False))
        return

    if not args.force and os.path.exists(output_path):
        try:
            cache_data = json.load(open(output_path, encoding="utf-8"))
            inv_list = cache_data.get("invoices", []) if isinstance(cache_data, dict) else cache_data
            res = {
                "ok": True,
                "n_ok": len(inv_list),
                "n_fail": 0,
                "failed": [],
                "path": output_path,
                "cached": True
            }
            print(json.dumps(res, ensure_ascii=False))
            return
        except Exception as e:
            pass

    if not gemini_available():
        if os.path.exists(output_path):
            try:
                cache_data = json.load(open(output_path, encoding="utf-8"))
                inv_list = cache_data.get("invoices", []) if isinstance(cache_data, dict) else cache_data
                res = {
                    "ok": True,
                    "n_ok": len(inv_list),
                    "n_fail": 0,
                    "failed": [],
                    "path": output_path,
                    "cached": True,
                    "warning": "GEMINI_API_KEY not set; using existing cache"
                }
                print(json.dumps(res, ensure_ascii=False))
                return
            except Exception:
                pass

        res = {
            "ok": False,
            "n_ok": 0,
            "n_fail": len(imgs),
            "failed": [os.path.basename(p) for p in imgs],
            "path": output_path,
            "error": "GEMINI_API_KEY environment variable is not set."
        }
        print(json.dumps(res, ensure_ascii=False))
        sys.exit(0)

    invoices, failed_files = ocr_suppliers_with_gemini(imgs)

    existing_map = {}
    if os.path.exists(output_path) and not args.force:
        try:
            old_data = json.load(open(output_path, encoding="utf-8"))
            old_list = old_data.get("invoices", []) if isinstance(old_data, dict) else old_data
            for inv in old_list:
                if isinstance(inv, dict) and "file" in inv:
                    existing_map[inv["file"]] = inv
        except Exception:
            pass

    for inv in invoices:
        existing_map[inv["file"]] = inv

    final_invoices = list(existing_map.values())
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    json.dump({"invoices": final_invoices}, open(output_path, "w", encoding="utf-8"), ensure_ascii=False, indent=2)

    res = {
        "ok": len(failed_files) == 0,
        "n_ok": len(invoices),
        "n_fail": len(failed_files),
        "failed": [f[0] for f in failed_files],
        "path": output_path
    }
    print(json.dumps(res, ensure_ascii=False))


if __name__ == "__main__":
    main()
