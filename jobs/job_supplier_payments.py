"""
Supplier Payments Job — match supplier invoices against the whitelist,
categorize by branch (Club/Pilates) and payment terms (+30/+60), and
flag unknown suppliers for manager review.

Architecture:
  Phase A — MATCH & CATEGORIZE
    * Load supplier OCR cache + supplier_whitelist.json
    * Match each invoice supplier_name against whitelist (exact -> alias)
    * Categorize by branch based on account_code prefix (180=Club, 181=Pilates)
    * Separate by payment_terms (+30, +60, or other)
    * If unknown supplier, mark HOLD_NEW_SUPPLIER

  Phase B — REPORT
    * Return structured data for Excel output builder
"""
import sys, os, json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "core"))
sys.path.insert(0, os.path.dirname(__file__))
from common import load_json

CONFIG_DIR = os.path.join(os.path.dirname(__file__), "..", "config")


def _num(x):
    try:
        return float(x)
    except (ValueError, TypeError):
        return 0.0


def _normalize_name(s):
    """Normalize supplier name for matching."""
    if s is None:
        return ""
    import unicodedata
    s = unicodedata.normalize("NFKC", str(s))
    s = s.replace("‏", "").replace("‎", "")
    s = " ".join(s.split()).strip()
    return s.lower()


def load_supplier_whitelist():
    """Load config/supplier_whitelist.json."""
    return load_json("supplier_whitelist.json")


def load_supplier_ocr(cache_path):
    """Load supplier OCR cache from path."""
    if not os.path.exists(cache_path):
        return []
    with open(cache_path, encoding="utf-8") as f:
        data = json.load(f)
    if isinstance(data, dict) and "invoices" in data:
        return data["invoices"]
    if isinstance(data, list):
        return data
    return []


def match_supplier(supplier_name, whitelist):
    """
    Match a supplier name against the whitelist.
    Returns (supplier_entry, method) or (None, 'UNMATCHED').
    Methods: EXACT, ALIAS, UNMATCHED.
    """
    if not supplier_name:
        return None, "EMPTY"
    norm = _normalize_name(supplier_name)
    best_alias = (None, 0)

    for entry in whitelist.get("suppliers", []):
        # Exact match on name
        if _normalize_name(entry["name"]) == norm:
            return entry, "EXACT"
        # Alias match
        for alias in entry.get("aliases", []):
            alias_norm = _normalize_name(alias)
            if alias_norm == norm:
                return entry, "ALIAS"
            # Partial / substring match as fallback
            score = 0
            if alias_norm in norm or norm in alias_norm:
                score = len(set(alias_norm.split()) & set(norm.split()))
            if score > best_alias[1]:
                best_alias = (entry, score)

    # No exact/alias match — return best partial if decent, else unmatched
    if best_alias[0] and best_alias[1] > 0:
        return best_alias[0], "PARTIAL"
    return None, "UNMATCHED"


def process_supplier_invoices(supplier_invoices, whitelist):
    """
    Process a list of supplier invoice dicts against the whitelist.

    Returns:
      payments_30  -> list of dicts for +30 day terms, matched
      payments_60  -> list of dicts for +60 day terms, matched
      held         -> list of dicts for unmatched / unknown suppliers
      totals       -> dict with total_30, total_60, n_held
    """
    payments_30 = []
    payments_60 = []
    held = []

    for inv in supplier_invoices:
        supplier_name = inv.get("supplier_name", "")
        entry, method = match_supplier(supplier_name, whitelist)

        total = _num(inv.get("total_amount"))
        vat = _num(inv.get("vat_amount"))
        payment_hint = inv.get("payment_terms_hint", "+30")

        base = {
            "supplier_name": supplier_name,
            "tax_id": inv.get("tax_id", ""),
            "doc_number": inv.get("doc_number", ""),
            "doc_date": inv.get("doc_date", ""),
            "total_amount": round(total, 2),
            "vat_amount": round(vat, 2),
            "payment_terms_hint": payment_hint,
            "line_description": inv.get("line_description", ""),
            "file": inv.get("file", ""),
        }

        if entry is None:
            base["status"] = "HOLD_NEW_SUPPLIER"
            base["match_method"] = method
            base["account_code"] = None
            base["branch"] = None
            base["category"] = None
            base["gl_code"] = None
            held.append(base)
            continue

        account_code = entry["account_code"]
        branch = entry.get("branch", "מועדון")
        category = entry.get("category", "")
        gl_code = account_code  # GL account code from whitelist

        base["status"] = "MATCHED"
        base["match_method"] = method
        base["account_code"] = account_code
        base["branch"] = branch
        base["category"] = category
        base["gl_code"] = gl_code

        # Determine effective payment terms: whitelist takes precedence,
        # OCR hint is fallback
        terms = entry.get("payment_terms", payment_hint)

        if terms == "+60":
            payments_60.append(base)
        else:
            # Default to +30 for מזומן, +30, or other
            payments_30.append(base)

    totals = {
        "total_30": round(sum(i["total_amount"] for i in payments_30), 2),
        "total_60": round(sum(i["total_amount"] for i in payments_60), 2),
        "n_held": len(held),
    }

    return payments_30, payments_60, held, totals


def run(ocr_cache_path, whitelist_path=None):
    """
    Run the full supplier payments pipeline from OCR cache.
    Returns (payments_30, payments_60, held, totals).
    """
    whitelist = load_supplier_whitelist() if whitelist_path is None else json.load(open(whitelist_path, encoding="utf-8"))
    invoices = load_supplier_ocr(ocr_cache_path)

    if not invoices:
        return [], [], [], {"total_30": 0, "total_60": 0, "n_held": 0}

    return process_supplier_invoices(invoices, whitelist)
