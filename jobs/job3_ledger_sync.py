"""
JOB 3 — כרטסת -> תקציב מול ביצוע  (overwrite-safe two-layer sync).

Core principle (spec §4): never store one 'actual'. For each month we keep
  <month> ביצוע (כרטסת)   -> system layer, overwritten every run
  <month> התאמה ידנית      -> manual layer, NEVER touched by the sync
  <month> ביצוע            -> formula = ledger + manual (what summaries point at)

This module is idempotent: on first run it INSERTS the two helper columns for a
month; on later runs it detects them and only rewrites the ledger layer, so the
manager's manual reallocations survive every re-sync.
"""
import openpyxl
from openpyxl.utils import get_column_letter

MONTHS_HE = ["ינואר","פברואר","מרץ","אפריל","מאי","יוני","יולי","אוגוסט",
             "ספטמבר","אוקטובר","נובמבר","דצמבר"]
SHEETS = {"מועדון":"תקציב מול ביצוע 2026 - מועדון",
          "פילאטיס":"תקציב מול ביצוע 2026 - פילאטיס"}
HEADER_ROW = 2
CODE_COL = 1

LEDGER_SUFFIX = "ביצוע (כרטסת)"
MANUAL_SUFFIX = "התאמה ידנית"
DISPLAY_SUFFIX = "ביצוע"

def _find_header(ws, text):
    for c in range(1, ws.max_column+1):
        if str(ws.cell(row=HEADER_ROW, column=c).value or "").strip() == text:
            return c
    return None

def _code_rows(ws):
    rows = {}
    for r in range(HEADER_ROW+1, ws.max_row+1):
        v = ws.cell(row=r, column=CODE_COL).value
        if v is None: continue
        if isinstance(v, float) and v.is_integer():
            code = str(int(v))
        elif isinstance(v, int):
            code = str(v)
        else:
            code = str(v).strip()
        if code.isdigit():
            rows[code] = r
    return rows

def ensure_two_layer(ws, month_he, year=2026):
    """
    Ensure the three-column block exists for `month_he`.
    Returns (ledger_col, manual_col, display_col).
    Idempotent — safe to call every run.
    """
    ledger_hdr  = f"{month_he} {LEDGER_SUFFIX}"
    manual_hdr  = f"{month_he} {MANUAL_SUFFIX}"
    display_hdr = f"{month_he} {DISPLAY_SUFFIX}"      # "<month> - ביצוע" or "<month> ביצוע"
    display_hdr_dash = f"{month_he} - {DISPLAY_SUFFIX}"

    lc = _find_header(ws, ledger_hdr)
    if lc is not None:
        mc = _find_header(ws, manual_hdr)
        dc = _find_header(ws, display_hdr) or _find_header(ws, display_hdr_dash)
        return lc, mc, dc

    # find existing display/ביצוע column for this month (dash or plain variant)
    dc = _find_header(ws, display_hdr_dash) or _find_header(ws, display_hdr)
    if dc is None:
        # month has only a budget column (e.g. June). Anchor after the budget col.
        budget_col = _find_header(ws, month_he)
        if budget_col is None:
            raise ValueError(f"month column '{month_he}' not found")
        # insert display col right after budget, then helper cols before it
        ws.insert_cols(budget_col+1)
        dc = budget_col+1
        ws.cell(row=HEADER_ROW, column=dc, value=display_hdr_dash)
    # insert TWO columns before the display column: ledger, manual
    ws.insert_cols(dc, 2)
    lc, mc, dc = dc, dc+1, dc+2
    ws.cell(row=HEADER_ROW, column=lc, value=ledger_hdr)
    ws.cell(row=HEADER_ROW, column=mc, value=manual_hdr)
    # display becomes a formula = ledger + manual, for every code row
    for r in range(HEADER_ROW+1, ws.max_row+1):
        code = ws.cell(row=r, column=CODE_COL).value
        if code is None: continue
        L, M = get_column_letter(lc), get_column_letter(mc)
        ws.cell(row=r, column=dc, value=f"=SUM({L}{r},{M}{r})")
    return lc, mc, dc

def sync_month(wb, sheet_key, month_he, month_key, movement, audit_log):
    ws = wb[SHEETS[sheet_key]]
    lc, mc, dc = ensure_two_layer(ws, month_he)
    code_rows = _code_rows(ws)
    # deterministic re-sync: clear the ledger layer for every code row first,
    # so a code that had data last run but none this run resets to 0 (manual layer untouched)
    for r in code_rows.values():
        ws.cell(row=r, column=lc, value=0)
    written = 0
    for (sk, code, mkey), amount in movement.items():
        if sk != sheet_key: continue
        if mkey != month_key: continue        # only the target month
        r = code_rows.get(code)
        if r is None: continue
        # write ONLY the ledger layer; never touch manual (mc)
        ws.cell(row=r, column=lc, value=round(amount, 2))
        written += 1
    audit_log.append({"type":"LEDGER_SYNC","severity":"INFO","ref":f"{sheet_key}/{month_he}",
                      "actual":written,"note":f"wrote {written} ledger-layer values"})
    return written

def run(budget_path, out_path, movement, target_month_he, audit_log, month_key=None):
    if month_key is None:
        idx = MONTHS_HE.index(target_month_he) + 1
        month_key = "2026-%02d" % idx
    wb = openpyxl.load_workbook(budget_path)
    total = 0
    for sk in SHEETS:
        total += sync_month(wb, sk, target_month_he, month_key, movement, audit_log)
    wb.save(out_path)
    return total
