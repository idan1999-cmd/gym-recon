"""
Invoice OCR — turn PDF/image invoices into structured schema.
Two paths:
  1. Gemini Vision OCR (Primary path when GEMINI_API_KEY is set in environment).
  2. Cache path (load config/invoices_ocr.json if present).

Supplier invoices use a separate schema and cache file (config/suppliers_ocr.json).
"""
import os, json, glob

# ---- Supplier invoice OCR schema ----
SUPPLIER_SCHEMA_HINT = {
    "file": "str",
    "supplier_name": "str",
    "tax_id": "str",
    "doc_number": "str",
    "doc_date": "YYYY-MM-DD",
    "total_amount": 0.0,
    "vat_amount": 0.0,
    "payment_terms_hint": "+30|+60|מזומן",
    "line_description": "str",
    "notes": ""
}

SUPPLIER_PROMPT = (
    "Extract this supplier invoice into strict JSON with keys: "
    "file, supplier_name, tax_id, doc_number, doc_date, total_amount, "
    "vat_amount, payment_terms_hint, line_description, notes. "
    "Rules: doc_date YYYY-MM-DD. total_amount and vat_amount numeric. "
    "payment_terms_hint one of: +30, +60, or מזומן. "
    "line_description is a short description of the service or product. "
    "Output raw valid JSON only without markdown formatting."
)

def ocr_supplier_single_file_gemini(p, gm):
    """OCR a single supplier invoice file using Gemini Vision model."""
    data = open(p, "rb").read()
    ext = p.lower()
    if ext.endswith(".pdf"):
        mime = "application/pdf"
    elif ext.endswith(".png"):
        mime = "image/png"
    elif ext.endswith(".jpg") or ext.endswith(".jpeg"):
        mime = "image/jpeg"
    else:
        mime = "application/octet-stream"

    resp = gm.generate_content([SUPPLIER_PROMPT, {"mime_type": mime, "data": data}])
    txt = resp.text.strip()
    if txt.startswith("```"):
        txt = txt.split("\n", 1)[-1].rsplit("```", 1)[0].strip()
    inv = json.loads(txt)
    inv["file"] = os.path.basename(p)
    return inv

def ocr_suppliers_with_gemini(image_paths, model="gemini-1.5-flash"):
    """Headless supplier OCR via Gemini with per-invoice isolation."""
    key = os.environ.get("GEMINI_API_KEY")
    if not key:
        raise RuntimeError("GEMINI_API_KEY not set — cannot use headless OCR path")
    import google.generativeai as genai
    genai.configure(api_key=key)
    gm = genai.GenerativeModel(model)

    out = []
    failed = []
    for p in image_paths:
        try:
            inv = ocr_supplier_single_file_gemini(p, gm)
            out.append(inv)
        except Exception as e:
            failed.append((os.path.basename(p), str(e)))

    return out, failed

def load_or_ocr_suppliers(invoices_dir, cache_json, invoice_globs=("*.pdf", "*.png", "*.jpg", "*.jpeg"), force=False):
    """
    Load cached supplier invoices or run Gemini OCR if cache absent/forced.
    """
    if cache_json and os.path.exists(cache_json) and not force:
        try:
            data = json.load(open(cache_json, encoding="utf-8"))
            if isinstance(data, dict) and "invoices" in data:
                return data["invoices"]
            elif isinstance(data, list):
                return data
        except Exception:
            pass

    imgs = []
    if invoices_dir and os.path.exists(invoices_dir):
        for g in invoice_globs:
            imgs += glob.glob(os.path.join(invoices_dir, g))
    imgs = sorted(list(set(imgs)))

    if gemini_available() and imgs:
        invoices, failed = ocr_suppliers_with_gemini(imgs)
        existing_map = {}
        if cache_json and os.path.exists(cache_json):
            try:
                old_data = json.load(open(cache_json, encoding="utf-8"))
                old_list = old_data.get("invoices", []) if isinstance(old_data, dict) else old_data
                for inv in old_list:
                    if isinstance(inv, dict) and "file" in inv:
                        existing_map[inv["file"]] = inv
            except Exception:
                pass
        for inv in invoices:
            existing_map[inv["file"]] = inv

        final_invoices = list(existing_map.values())
        if cache_json:
            os.makedirs(os.path.dirname(os.path.abspath(cache_json)), exist_ok=True)
            json.dump({"invoices": final_invoices}, open(cache_json, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
        return final_invoices

    if cache_json and os.path.exists(cache_json):
        data = json.load(open(cache_json, encoding="utf-8"))
        return data.get("invoices", []) if isinstance(data, dict) else data

    return []

SCHEMA_HINT = {
    "file": "str",
    "trainer": "str",
    "doc_number": "str",
    "doc_date": "YYYY-MM-DD",
    "issuer_tax_id": "str",
    "billed_to": "str",
    "stated_total": 0.0,
    "vat_included": False,
    "unit_kind": "session|hour|monthly",
    "category": "personal|studio|group|class|other",
    "branch": "פילאטיס|חדר כושר",
    "line_items": [{"desc": "", "qty": 0, "rate": 0, "total": 0}],
    "session_dates": ["d.m.yy or DD/MM/YYYY"],
    "notes": ""
}

PROMPT = (
    "Extract this fitness-trainer invoice into strict JSON with keys: "
    "file, trainer, doc_number, doc_date, issuer_tax_id, billed_to, stated_total, "
    "vat_included, unit_kind, category, branch, line_items, session_dates, notes. "
    "Rules: doc_date YYYY-MM-DD. stated_total numeric. line_items[].rate numeric or 0. "
    "unit_kind one of: session, hour, monthly. category one of: personal, studio, group, class, other. "
    "branch one of: פילאטיס, חדר כושר. session_dates = list of service date strings listed. "
    "Output raw valid JSON only without markdown formatting."
)

def gemini_available():
    return bool(os.environ.get("GEMINI_API_KEY"))

def ocr_single_file_gemini(p, gm):
    """OCR a single invoice file using Gemini Vision model."""
    data = open(p, "rb").read()
    ext = p.lower()
    if ext.endswith(".pdf"):
        mime = "application/pdf"
    elif ext.endswith(".png"):
        mime = "image/png"
    elif ext.endswith(".jpg") or ext.endswith(".jpeg"):
        mime = "image/jpeg"
    else:
        mime = "application/octet-stream"

    resp = gm.generate_content([PROMPT, {"mime_type": mime, "data": data}])
    txt = resp.text.strip()
    if txt.startswith("```"):
        txt = txt.split("\n", 1)[-1].rsplit("```", 1)[0].strip()
    inv = json.loads(txt)
    inv["file"] = os.path.basename(p)
    return inv

def ocr_with_gemini(image_paths, model="gemini-1.5-flash"):
    """Headless OCR via Gemini with per-invoice isolation."""
    key = os.environ.get("GEMINI_API_KEY")
    if not key:
        raise RuntimeError("GEMINI_API_KEY not set — cannot use headless OCR path")
    import google.generativeai as genai
    genai.configure(api_key=key)
    gm = genai.GenerativeModel(model)

    out = []
    failed = []
    for p in image_paths:
        try:
            inv = ocr_single_file_gemini(p, gm)
            out.append(inv)
        except Exception as e:
            failed.append((os.path.basename(p), str(e)))

    return out, failed

def load_or_ocr(invoices_dir, cache_json, invoice_globs=("*.pdf", "*.png", "*.jpg", "*.jpeg"), force=False):
    """
    Load cached invoices or run Gemini OCR if cache absent/forced.
    """
    if cache_json and os.path.exists(cache_json) and not force:
        try:
            data = json.load(open(cache_json, encoding="utf-8"))
            if isinstance(data, dict) and "invoices" in data:
                return data["invoices"]
            elif isinstance(data, list):
                return data
        except Exception:
            pass

    imgs = []
    if invoices_dir and os.path.exists(invoices_dir):
        for g in invoice_globs:
            imgs += glob.glob(os.path.join(invoices_dir, g))
    imgs = sorted(list(set(imgs)))

    if gemini_available() and imgs:
        invoices, failed = ocr_with_gemini(imgs)
        # Merge with existing cache if present
        existing_map = {}
        if cache_json and os.path.exists(cache_json):
            try:
                old_data = json.load(open(cache_json, encoding="utf-8"))
                old_list = old_data.get("invoices", []) if isinstance(old_data, dict) else old_data
                for inv in old_list:
                    if isinstance(inv, dict) and "file" in inv:
                        existing_map[inv["file"]] = inv
            except Exception:
                pass
        for inv in invoices:
            existing_map[inv["file"]] = inv

        final_invoices = list(existing_map.values())
        if cache_json:
            os.makedirs(os.path.dirname(os.path.abspath(cache_json)), exist_ok=True)
            json.dump({"invoices": final_invoices}, open(cache_json, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
        return final_invoices

    if cache_json and os.path.exists(cache_json):
        data = json.load(open(cache_json, encoding="utf-8"))
        return data.get("invoices", []) if isinstance(data, dict) else data

    return []

