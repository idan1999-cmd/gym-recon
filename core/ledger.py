"""Ledger (כרטסת) parser. Header-name driven (layouts differ per snapshot tab)."""
import openpyxl, csv, re, sys
from common import month_key, parse_memo_month

HEADER_TOKEN = "מט."
ACCT_RE = re.compile(r"חשבון:\s*(\d+)-")
H_CREDIT = "זכות"
H_DEBIT = "חובה"
H_BALANCE_DATE = "תאריך למאזן"
H_VALUE_DATE = "תאריך ערך"
H_MEMO = "פרטים"

# Bug-4 (per owner): memo (פרטים) must win over balance date. Evidence: 105 rows
# show a +1 month lag when balance-date is used, causing ₪28,651 drift in June.
# The priority is now memo -> balance -> value. This is a deliberate change from
# the earlier balance-first rule (see .opencode/decisions.md) — documented in
# BUILD_LOG.md. Keep it a named constant so it is easy to revert.
MONTH_PRIORITY = ["memo", "balance_date", "value_date"]

# Bug-5: log which ledger tab was selected.
import logging as _logging
_log = _logging.getLogger("gym-recon.ledger")
_LOG_TAB_CHOICES = []


def _rows_from_xlsx(path, sheet=None, target_month=None):
    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    if sheet:
        ws = wb[sheet]
    else:
        # Bug-5 fix: select the LATEST tab that actually covers the target month,
        # not just wb.sheetnames[-1] (which swung ~₪240k between tabs).
        ws = _select_ledger_tab(wb, target_month, path)
    rows = [list(r) for r in ws.iter_rows(values_only=True)]
    wb.close()
    return rows


def _select_ledger_tab(wb, target_month, path):
    """Pick the snapshot tab that best covers target_month.
    Strategy: among tabs that parse and contain >= 1 transaction mapped to
    target_month, choose the one with the most target-month rows (latest covers).
    Fall back to the last tab only if nothing matches. Log the explicit choice.
    """
    names = wb.sheetnames
    _log.debug("tab selection for month=%s among %s tabs", target_month, len(names))
    if not names:
        raise ValueError("ledger workbook has no sheets")

    scored = []
    for n in names:
        try:
            txns, _ = parse_ledger(path, sheet=n)
        except Exception:  # noqa: BLE001
            continue
        if target_month:
            matched = sum(1 for t in txns if t["budget_month"] == target_month)
        else:
            matched = len(txns)
        if matched > 0:
            scored.append((n, matched))
    if scored:
        # prefer highest coverage; on a tie prefer the later tab
        chosen = max(scored, key=lambda x: (x[1], names.index(x[0])))[0]
    else:
        chosen = names[-1]
    _LOG_TAB_CHOICES.append({"tab": chosen, "path": path, "target_month": target_month})
    print(f"[ledger] selected tab '{chosen}' (target_month={target_month}) "
          f"of {len(names)} tabs", file=sys.stderr)
    return wb[chosen]

def _rows_from_csv(path):
    with open(path, encoding="utf-8-sig", newline="") as f:
        return [r for r in csv.reader(f)]

def parse_ledger(path, sheet=None, target_month=None):
    rows = _rows_from_xlsx(path, sheet, target_month)
    hdr = None
    for i, r in enumerate(rows):
        if r and str(r[0]).strip() == HEADER_TOKEN:
            hdr = i; break
    if hdr is None:
        raise ValueError("ledger header row (מט.) not found")
    header = [str(c).strip() if c is not None else "" for c in rows[hdr]]
    def col(name): return header.index(name) if name in header else None
    ci_credit, ci_debit = col(H_CREDIT), col(H_DEBIT)
    ci_bdate, ci_vdate = col(H_BALANCE_DATE), col(H_VALUE_DATE)
    ci_memo = col(H_MEMO)
    if ci_credit is None or ci_debit is None:
        raise ValueError("ledger missing זכות/חובה columns: %s" % header)
    def cell(r, ci): return r[ci] if (ci is not None and len(r) > ci) else None
    def num(x):
        try: return float(x) if x not in (None, "") else 0.0
        except (ValueError, TypeError): return 0.0
    txns, subtotals = [], {}
    cur = None
    for r in rows[hdr+1:]:
        c0 = str(r[0]).strip() if r and r[0] is not None else ""
        m = ACCT_RE.search(c0)
        if m: cur = m.group(1); continue
        if c0.replace('"', '').startswith("סהכ לחשבון"): subtotals[cur] = r; continue
        if cur is None: continue
        # Bug-4 month priority (per owner): memo -> balance -> value -> scan.
        # Priority order is a named constant (MONTH_PRIORITY) for easy revert.
        bal_mk = month_key(cell(r, ci_bdate))
        memo_mk = parse_memo_month(cell(r, ci_memo)) if ci_memo is not None else None
        val_mk = month_key(cell(r, ci_vdate))
        candidates = {"memo": memo_mk, "balance_date": bal_mk, "value_date": val_mk}
        month_source = None
        for key in MONTH_PRIORITY:
            if candidates.get(key):
                mk, month_source = candidates[key], key
                break
        else:
            mk = None
            for v in reversed(r):
                mk = month_key(v)
                if mk:
                    month_source = "scan"
                    break
        if not mk: continue
        txns.append({
            "account": cur, "budget_month": mk,
            "debit": num(cell(r, ci_debit)), "credit": num(cell(r, ci_credit)),
            "month_source": month_source,
            "memo": cell(r, ci_memo) if ci_memo is not None else None,
        })
    return txns, subtotals

def monthly_movement(txns, account_map):
    accts = account_map["accounts"]; excl = account_map.get("exclude_prefixes", [])
    out, unmapped = {}, set()
    for t in txns:
        acc = t["account"]
        if any(acc.startswith(p) for p in excl): continue
        meta = accts.get(acc)
        if not meta: unmapped.add(acc); continue
        key = (meta["sheet"], meta["budget_code"], t["budget_month"])
        out[key] = out.get(key, 0.0) + (t["debit"] - t["credit"])
    return out, unmapped
