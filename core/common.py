"""
Pure functions shared by all three jobs. No I/O side effects beyond reading config.
Written so each function can be lifted into an n8n Code node later without rewrite.
"""
import json, os, re, unicodedata
from datetime import datetime

CONFIG_DIR = os.path.join(os.path.dirname(__file__), "..", "config")

# ---------- config loaders ----------
def load_json(name):
    with open(os.path.join(CONFIG_DIR, name), encoding="utf-8") as f:
        return json.load(f)

def load_aliases():   return load_json("trainer_aliases.json")
def load_pay_matrix():return load_json("pay_matrix.json")
def load_account_map():return load_json("account_map.json")

# ---------- name normalization / matching ----------
_HONORIFICS = ["מר", "גב'", "גב", "ד\"ר"]

def normalize_name(s):
    if s is None: return ""
    s = unicodedata.normalize("NFKC", str(s))
    s = s.replace("‏", "").replace("‎", "")   # strip RTL/LTR marks
    s = re.sub(r"[\"'`.,]", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    for h in _HONORIFICS:
        if s.startswith(h + " "):
            s = s[len(h)+1:]
    return s

def _token_set_ratio(a, b):
    """Lightweight token-set similarity 0..100, no external deps."""
    ta, tb = set(normalize_name(a).split()), set(normalize_name(b).split())
    if not ta or not tb: return 0
    inter = ta & tb
    # ratio favouring shared tokens; symmetric
    return int(100 * (2 * len(inter)) / (len(ta) + len(tb)))

def resolve_trainer(raw_name, aliases_cfg):
    """
    Returns (trainer_id, canonical_name, score, method) or
    (None, None, best_score, 'UNMAPPED') if below threshold.
    """
    if raw_name is None: return (None, None, 0, "EMPTY")
    norm = normalize_name(raw_name)
    if norm in aliases_cfg.get("_ignore_tokens", []) or norm == "":
        return (None, None, 0, "IGNORED")
    thr = aliases_cfg.get("review_threshold", 88)
    # 1) exact / normalized alias match
    for t in aliases_cfg["trainers"]:
        for al in t["aliases"]:
            if normalize_name(al) == norm:
                return (t["trainer_id"], t["canonical_name"], 100, "EXACT")
    # 2) fuzzy token-set
    best = (None, None, 0)
    for t in aliases_cfg["trainers"]:
        for al in t["aliases"]:
            sc = _token_set_ratio(al, norm)
            if sc > best[2]:
                best = (t["trainer_id"], t["canonical_name"], sc)
    if best[2] >= thr:
        return (best[0], best[1], best[2], "FUZZY")
    return (None, None, best[2], "UNMAPPED")

# ---------- date helpers ----------
def parse_date_any(s):
    """Parse dd/mm/yyyy, dd.mm.yy, d.m, yyyy-mm-dd -> datetime or None."""
    if s is None: return None
    if isinstance(s, datetime): return s
    s = str(s).strip()
    for fmt in ("%d/%m/%Y", "%d/%m/%y", "%d.%m.%Y", "%d.%m.%y",
                "%Y-%m-%d", "%Y-%m-%d %H:%M:%S", "%d/%m", "%d.%m"):
        try:
            d = datetime.strptime(s, fmt)
            if fmt in ("%d/%m", "%d.%m"):
                d = d.replace(year=datetime.now().year)
            return d
        except ValueError:
            continue
    return None

def month_key(d):
    d = parse_date_any(d)
    return d.strftime("%Y-%m") if d else None

# Hebrew month names for memo parsing (deterministic, not AI)
_HE_MONTHS = {
    "ינואר": 1, "פברואר": 2, "מרץ": 3, "אפריל": 4, "מאי": 5, "יוני": 6,
    "יולי": 7, "אוגוסט": 8, "ספטמבר": 9, "אוקטובר": 10, "נובמבר": 11, "דצמבר": 12,
}
# Patterns in פרטים like "5/26 הכנסות", "05.06.2026", "חודש יוני 2026"
_MEMO_MDY = re.compile(r"(?<!\d)(\d{1,2})[./](\d{2,4})(?!\d)")
# Full d.m.yy / dd.mm.yyyy form, matched before _MEMO_MDY so "05.06.26" is read
# as day 05 month 06 year 26 (-> 2026-06), never split as "05/06".
_MEMO_DMY = re.compile(r"(?<!\d)(\d{1,2})[./](\d{1,2})[./](\d{2,4})(?!\d)")
_MEMO_HE = re.compile(
    r"(?:חודש\s+)?(" + "|".join(_HE_MONTHS.keys()) + r")\s*(\d{2,4})?"
)
# Installment notation: "תש' 5/12", "תשלום 3/6", "מס' 1/4" — is number-of-payment,
# not a date. If a match sits right after one of these words, ignore it.
_INSTALLMENT_HINT = re.compile(r"(?:\u05ea\u05e9|\u05ea\u05e9\u05dc\u05d5\u05dd|\u05de\u05e1)(?:\u0027|\u05f3|\s)?")

def _resolve_year(y, fallback):
    y = int(y)
    if y >= 100:
        return y
    # two-digit year: 2020.. dropped; a bare '12' here would be an instalment,
    # not a year, so only map to 19xx if < 20 is implausible -> force 20xx.
    return 2000 + y

def parse_memo_month(text, default_year=None):
    """
    Deterministic month from ledger memo (פרטים). Returns 'YYYY-MM' or None.
    Behavior: memo is an independent candidate; the CALLER decides priority
    (current engine: memo -> balance date -> value date).
    Patterns: 5/26, 05.06.26, 5/2026, יוני 2026, חודש מאי.
    Skips NPV instalment notation such as 'תש' 5/12' (not a year).
    """
    if text is None:
        return None
    s = str(text).strip()
    if not s:
        return None
    year_fallback = default_year or datetime.now().year

    # 1) explicit dd.mm.yy — prefer the full triple so "05.06.26" -> 2026-06
    m = _MEMO_DMY.search(s)
    if m:
        d, month, y = int(m.group(1)), int(m.group(2)), _resolve_year(m.group(3), year_fallback)
        if 1 <= month <= 12:
            return f"{y:04d}-{month:02d}"

    # 2) month. year: m/yy or m/yyyy
    m = _MEMO_MDY.search(s)
    if m:
        start = m.start()
        a, b = int(m.group(1)), int(m.group(2))
        # Instalment notation ("תש' 5/12" / "5/12") where 12 is one-of-N, not a
        # year. Also reject 2-digit years < 20 outright (implausible in 2026
        # books; e.g. '5/12' -> 2012 is clearly not a service year).
        if b < 100 and b < 20:
            pass  # not a valid year — fall through to other patterns below
        elif _INSTALLMENT_HINT.search(s[:start]) and b <= 31:
            pass  # instalment — not a date; fall through
        else:
            if b > 31:  # year part
                month, year = a, b
            elif a > 12 and b <= 12:  # day.month -> month
                month, year = b, year_fallback
            elif a <= 12:
                month, year = a, (b if b > 31 else (2000 + b if b < 100 else b))
            else:
                month = None
            if month is not None and 1 <= month <= 12:
                return f"{_resolve_year(year, year_fallback):04d}-{month:02d}"

    m2 = _MEMO_HE.search(s)
    if m2:
        month = _HE_MONTHS[m2.group(1)]
        yraw = m2.group(2)
        year = _resolve_year(yraw, year_fallback) if yraw else year_fallback
        return f"{year:04d}-{month:02d}"
    return None

def service_month_from_dates(date_list):
    """The month most session_dates fall in (service month, NOT doc date)."""
    months = {}
    for d in date_list or []:
        mk = month_key(d)
        if mk: months[mk] = months.get(mk, 0) + 1
    if not months: return None
    return max(months.items(), key=lambda kv: kv[1])[0]

def is_income_budget_code(code):
    """Budget line codes that are income (boss: store as negative)."""
    c = str(code or "").strip()
    return c.startswith("80") or c.startswith("81")

# ---------- audit log ----------
import uuid
def audit_entry(atype, trainer_id=None, ref=None, month=None,
                expected=None, actual=None, amount=None,
                severity="INFO", note=""):
    return {
        "id": str(uuid.uuid4()),
        "ts": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "type": atype, "trainer_id": trainer_id, "ref": ref, "month": month,
        "expected": expected, "actual": actual, "amount": amount,
        "severity": severity, "note": note,
    }


def best_fuzzy_candidate(raw_name, aliases_cfg):
    """Closest existing trainer by token-set ratio -> (canonical, id, score) or (None,None,0)."""
    norm = normalize_name(raw_name)
    best = (None, None, 0)
    for t in aliases_cfg["trainers"]:
        for al in t["aliases"]:
            sc = _token_set_ratio(al, norm)
            if sc > best[2]:
                best = (t["canonical_name"], t["trainer_id"], sc)
    return best

def propose_new_trainer(inv, aliases_cfg):
    """Build a ready-to-approve directory proposal for an unmapped invoice trainer.
    The manager reviews this; on approval it becomes a trainer_aliases.json entry."""
    raw = inv.get("trainer")
    cand_name, cand_id, cand_score = best_fuzzy_candidate(raw, aliases_cfg)
    rates = [li.get("rate") for li in inv.get("line_items", []) if li.get("rate") is not None]
    # Hebrew names won't survive an ASCII slug; fall back to tax id, else counter-free hash
    slug = re.sub(r"[^a-z0-9]+", "_", (raw or "").strip().lower()).strip("_")
    if slug:
        suggested_id = "t_" + slug
    elif inv.get("issuer_tax_id"):
        suggested_id = "t_" + re.sub(r"\D", "", str(inv["issuer_tax_id"]))[:9]
    else:
        suggested_id = "t_new"
    return {
        "raw_name": raw,
        "suggested_trainer_id": suggested_id[:40],
        "issuer_tax_id": inv.get("issuer_tax_id"),
        "branch": inv.get("branch"),
        "category": inv.get("category"),
        "invoiced_rate": rates[0] if rates else None,
        "all_rates": rates,
        "stated_total": inv.get("stated_total"),
        "closest_existing": {"name": cand_name, "id": cand_id, "score": cand_score},
        "action": ("likely typo of '%s' (%d%%) — merge?" % (cand_name, cand_score))
                  if cand_score >= 70 else "no close match — add as NEW freelancer",
    }
