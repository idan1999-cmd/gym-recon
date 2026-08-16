"""
tools/suppliers.py — General Supplier Invoice Processor.
Extract invoice fields from supplier PDFs/images, match against whitelist,
categorize by payment terms (+30/+60), and produce approval workbook.

Usage:
  python tools/suppliers.py --input ./input --output ./output --month 6
  python tools/suppliers.py --input ./input --output ./output --month 6 --force-ocr
"""
import sys
import os
import json
import argparse

_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(_root, "core"))
sys.path.insert(0, os.path.join(_root, "jobs"))
sys.path.insert(0, _root)

from core.ocr import gemini_available, load_or_ocr_suppliers
from core.inputs import resolve_inputs
from jobs.job_supplier_payments import process_supplier_invoices, load_supplier_whitelist
from jobs.supplier_output import build as build_output

MONTHS_HE = [
    "ינואר", "פברואר", "מרץ", "אפריל", "מאי", "יוני",
    "יולי", "אוגוסט", "ספטמבר", "אוקטובר", "נובמבר", "דצמבר",
]


def _write_empty_output(output_dir, month):
    """Owner decision E: when there are no real supplier invoices (or the OCR
    cache cannot be linked to real input files), write an EXPLICIT empty pack and
    report ok=True with zero totals — a truthful 'nothing to approve' rather than
    a fabricated list. The output file carries a marker sheet note."""
    from jobs.supplier_output import build as build_output
    out_path = os.path.join(output_dir, "ספקים_לאישור_מנהל.xlsx")
    empty_totals = {"total_30": 0, "total_60": 0, "n_held": 0}
    result = build_output([], [], [], empty_totals, out_path, month=month)
    print(f"[Suppliers] Output: {out_path}")
    summary = {
        "ok": True,
        "total_30": 0,
        "total_60": 0,
        "n_held": 0,
        "n_matched_30": 0,
        "n_matched_60": 0,
        "output_path": out_path,
        "note": "no real supplier invoices linked to OCR — empty pack written",
    }
    print(json.dumps(summary, ensure_ascii=False))
    return 0


def main():
    parser = argparse.ArgumentParser(description="General Supplier Invoice Processor")
    parser.add_argument("--input", default="./input", help="Input directory")
    parser.add_argument("--output", default="./output", help="Output directory")
    parser.add_argument("--month", type=int, default=0, help="Month number 1-12 (default: previous month)")
    parser.add_argument("--force-ocr", action="store_true", help="Force re-OCR even if cache exists")
    args = parser.parse_args()

    input_dir = os.path.abspath(args.input)
    output_dir = os.path.abspath(args.output)
    os.makedirs(output_dir, exist_ok=True)

    month = args.month
    if month == 0:
        import datetime
        month = (datetime.datetime.now().replace(day=1) - datetime.timedelta(days=1)).month
        month_he = MONTHS_HE[month - 1]
        print(f"[Suppliers] No --month given, defaulting to previous month: {month} ({month_he})")
    else:
        month_he = MONTHS_HE[month - 1]
        print(f"[Suppliers] Month: {month} ({month_he})")

    config_dir = os.path.join(_root, "config")
    supplier_ocr_cache = os.path.join(config_dir, "suppliers_ocr.json")
    supplier_invoices_dir = os.path.join(input_dir, "invoices_suppliers")

    # Step 1: Run OCR or load cache
    print(f"[Suppliers] Checking supplier invoices in: {supplier_invoices_dir}")

    # Owner decision E: a supplier OCR cache is ONLY trustworthy if it can be
    # linked to a real input invoice file in invoices_suppliers/. A stray cache
    # (e.g. sample/test data) must never flow into an approval workbook.
    def _real_pdf_files():
        if not os.path.isdir(supplier_invoices_dir):
            return []
        return sorted(
            os.path.join(supplier_invoices_dir, f)
            for f in os.listdir(supplier_invoices_dir)
            if f.lower().endswith((".pdf", ".png", ".jpg", ".jpeg"))
        )

    real_invoice_files = _real_pdf_files()
    if not real_invoice_files:
        # No real supplier invoices to process — report empty, never fabricate.
        print("[Suppliers] No real supplier invoice files in input/invoices_suppliers — skipping supplier pack (no OCR data used).")
        _write_empty_output(output_dir, month)
        return 0

    has_files = bool(real_invoice_files)
    if has_files and (args.force_ocr or not os.path.exists(supplier_ocr_cache)):
        if not gemini_available():
            # Fallback: use existing cache or create empty
            if os.path.exists(supplier_ocr_cache):
                print("[Suppliers] GEMINI_API_KEY not set — using existing cache")
                invoices = _load_or_empty(supplier_ocr_cache)
            else:
                print("[Suppliers] WARNING: GEMINI_API_KEY not set and no cache exists. Run ocr_gemini.py --suppliers first or set the key.")
                print("[Suppliers] Proceeding with empty supplier list.")
                invoices = []
        else:
            print("[Suppliers] Running supplier OCR via Gemini...")
            invoices = load_or_ocr_suppliers(supplier_invoices_dir, supplier_ocr_cache, force=args.force_ocr)
            print(f"[Suppliers] OCR complete: {len(invoices)} invoices processed")
    else:
        if has_files and os.path.exists(supplier_ocr_cache):
            print(f"[Suppliers] Using cached supplier OCR ({len(load_supplier_cache(supplier_ocr_cache))} invoices)")
        invoices = _load_or_empty(supplier_ocr_cache)

    # Owner decision E: only invoices whose 'file' names match a real input file
    # may enter the approval pack. Anything else is treated as foreign data.
    real_basenames = {os.path.basename(p) for p in real_invoice_files}
    invoices = [inv for inv in invoices
                if inv.get("file") in real_basenames]
    if len(invoices) == 0 and has_files:
        print("[Suppliers] WARNING: OCR cache entries do not match any real input invoice file — no supplier data used.")
        _write_empty_output(output_dir, month)
        return 0

    # Step 2: Load whitelist
    whitelist = load_supplier_whitelist()
    print(f"[Suppliers] Loaded whitelist: {len(whitelist.get('suppliers', []))} known suppliers")

    # Step 3: Process — match, categorize, separate
    payments_30, payments_60, held, totals = process_supplier_invoices(invoices, whitelist)
    print(f"[Suppliers] Matched +30: {len(payments_30)} invoices, total {totals['total_30']}")
    print(f"[Suppliers] Matched +60: {len(payments_60)} invoices, total {totals['total_60']}")
    print(f"[Suppliers] Held (unknown): {totals['n_held']} suppliers")

    # Step 4: Build Excel output
    out_path = os.path.join(output_dir, "ספקים_לאישור_מנהל.xlsx")
    result = build_output(payments_30, payments_60, held, totals, out_path, month=month)
    print(f"[Suppliers] Output: {out_path}")

    summary = {
        "ok": True,
        "total_30": totals["total_30"],
        "total_60": totals["total_60"],
        "n_held": totals["n_held"],
        "n_matched_30": len(payments_30),
        "n_matched_60": len(payments_60),
        "output_path": out_path,
    }
    print(json.dumps(summary, ensure_ascii=False))
    return 0


def _load_or_empty(cache_path):
    """Load supplier OCR cache or return empty list."""
    from jobs.job_supplier_payments import load_supplier_ocr
    if os.path.exists(cache_path):
        return load_supplier_ocr(cache_path)
    return []


def load_supplier_cache(cache_path):
    """Load supplier OCR cache safely."""
    if os.path.exists(cache_path):
        try:
            with open(cache_path, encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict) and "invoices" in data:
                return data["invoices"]
            if isinstance(data, list):
                return data
        except Exception:
            pass
    return []


if __name__ == "__main__":
    sys.exit(main())
