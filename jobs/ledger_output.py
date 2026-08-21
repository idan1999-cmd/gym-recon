"""
Ledger Sync clean output — two standalone files:
  תקציב_מול_ביצוע_פילאטיס.xlsx  ,  תקציב_מול_ביצוע_חדר_כושר.xlsx

Each is a single-sheet extract of the matching budget tab, synced overwrite-safe
(two-layer: ביצוע(כרטסת) system layer + התאמה ידנית manual layer, display =
their sum written as a VALUE, not a formula, so numbers show in any viewer).

Phases (Idan feedback):
  1 strip pricing-note rows at bottom
  4 YTD columns through target month
  5 code-prefix rollups for income/expense totals
  6 enforce income negative / expense positive on system layer
"""
import sys, os, re
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "core"))
import openpyxl
from copy import copy
from openpyxl.styles import Font, PatternFill, Alignment
from openpyxl.utils import get_column_letter
from common import is_income_budget_code

MONTHS_HE = ["ינואר","פברואר","מרץ","אפריל","מאי","יוני","יולי","אוגוסט",
             "ספטמבר","אוקטובר","נובמבר","דצמבר"]
SRC_TABS = {"פילאטיס": "תקציב מול ביצוע 2026 - פילאטיס",
            "חדר כושר": "תקציב מול ביצוע 2026 - מועדון"}
SHEET_KEY = {"פילאטיס": "פילאטיס", "חדר כושר": "מועדון"}  # movement key
HEADER_ROW = 2
CODE_COL = 1
LABEL_COL = 2

RED = Font(color="C00000")
LEDGER_SUFFIX="ביצוע (כרטסת)"; MANUAL_SUFFIX="התאמה ידנית"; DISPLAY_SUFFIX="ביצוע"
ENGINE_FOOTER = "written by gym-recon ledger_sync — do not freestyle Excel"

# Pricing / helper note labels under the P&L (no budget code) — strip these
_NOTE_LABEL_RE = re.compile(
    r"(דמי\s*הרשמה|מנוי\s+פרימיום|מנוי\s+סטודיו|מנוי\s+חדר\s*כושר|"
    r"מנוי\s+נוער|מנוי\s+חיילים|מנוי\s+בוקר|מחיר\s+מנוי|שירותים\s+נוספים|"
    r"כרטיס[וו]?ת|מחיר\s+ממצוע|ממוצע\s+חודשי|"
    r"המחירים\s+לפני|ביאורים\s*:)",
    re.UNICODE,
)
# Structural labels we always keep (even without a code)
_KEEP_LABEL_RE = re.compile(
    r"(הוצאה|הכנסה|סה[\"”]?כ|רווח|הפסד|כמות\s+מנויים)",
    re.UNICODE,
)


def _num(x):
    try: return float(x)
    except (ValueError,TypeError): return 0.0


def _code_str(v):
    if v is None: return None
    if isinstance(v, float) and v.is_integer():
        return str(int(v))
    s = str(v).strip()
    return s if s.isdigit() else None


def _extract_tab(src_path, tab, out_path):
    """Copy one worksheet (values + basic style) into a new single-sheet wb."""
    wbv = openpyxl.load_workbook(src_path, data_only=True)
    src = wbv[tab]
    out = openpyxl.Workbook()
    ws = out.active; ws.title = tab[:31]
    ws.sheet_view.rightToLeft = True
    for row in src.iter_rows():
        for cell in row:
            if cell.value is None: continue
            nc = ws.cell(cell.row, cell.column, value=cell.value)
            if cell.has_style:
                nc.font=copy(cell.font); nc.fill=copy(cell.fill)
                nc.number_format=cell.number_format; nc.alignment=copy(cell.alignment)
                nc.border=copy(cell.border)
    for col, dim in src.column_dimensions.items():
        if dim.width: ws.column_dimensions[col].width=dim.width
    wbv.close()
    return out, ws


def _is_note_row(ws, r):
    """True if row is a pricing/helper note (no code + matches note label)."""
    code = _code_str(ws.cell(r, CODE_COL).value)
    if code:
        return False
    label = str(ws.cell(r, LABEL_COL).value or "").strip()
    if not label:
        return False
    if _KEEP_LABEL_RE.search(label):
        return False
    return bool(_NOTE_LABEL_RE.search(label))


def _strip_note_rows(ws):
    """
    Phase 1: remove pricing-note rows so January leftovers don't appear
    under the P&L. Delete from bottom up so indices stay valid.
    Returns count deleted.
    """
    to_delete = []
    for r in range(HEADER_ROW + 1, ws.max_row + 1):
        if _is_note_row(ws, r):
            to_delete.append(r)
    for r in reversed(to_delete):
        ws.delete_rows(r, 1)
    return len(to_delete)


def _find_header(ws, text):
    for c in range(1, ws.max_column+1):
        if str(ws.cell(HEADER_ROW,c).value or "").strip()==text: return c
    return None


def _code_rows(ws):
    rows={}
    for r in range(HEADER_ROW+1, ws.max_row+1):
        code = _code_str(ws.cell(r, CODE_COL).value)
        if code:
            rows[code] = r
    return rows


def _copy_cell_style(src_cell, target_cell):
    if src_cell is not None and src_cell.has_style:
        target_cell.font = copy(src_cell.font)
        target_cell.fill = copy(src_cell.fill)
        target_cell.border = copy(src_cell.border)
        target_cell.alignment = copy(src_cell.alignment)
        target_cell.number_format = src_cell.number_format


def _ensure_two_layer(ws, month_he):
    disp = f"{month_he} - {DISPLAY_SUFFIX}"
    disp2 = f"{month_he} {DISPLAY_SUFFIX}"
    led = f"{month_he} {LEDGER_SUFFIX}"
    man = f"{month_he} {MANUAL_SUFFIX}"
    lc = _find_header(ws, led)
    if lc is not None:
        return lc, _find_header(ws, man), (_find_header(ws, disp) or _find_header(ws, disp2))
    dc = _find_header(ws, disp) or _find_header(ws, disp2)
    ref_col = None
    if dc is None:
        bcol = _find_header(ws, month_he) or _find_header(ws, month_he + " ")
        if bcol is None:
            bcol = 3
        ws.insert_cols(bcol + 1)
        dc = bcol + 1
        ws.cell(HEADER_ROW, dc, value=disp)
        ref_col = bcol
    else:
        ref_col = dc - 1 if dc > 1 else dc

    ws.insert_cols(dc, 2)
    lc, mc, dc = dc, dc + 1, dc + 2
    ws.cell(HEADER_ROW, lc, value=led)
    ws.cell(HEADER_ROW, mc, value=man)
    ws.cell(HEADER_ROW, dc, value=disp)

    # Propagate styles across all rows for inserted columns
    for r in range(1, ws.max_row + 1):
        src_c = ws.cell(r, ref_col)
        for col_idx in (lc, mc, dc):
            _copy_cell_style(src_c, ws.cell(r, col_idx))

    return lc, mc, dc


def _find_section_rows(ws):
    """
    Phase 5: locate structural rows by label (not blank-row heuristics).
    Returns dict with optional keys: expense_header, income_total, expense_total, grand_total
    """
    out = {}
    for r in range(HEADER_ROW + 1, ws.max_row + 1):
        lbl = str(ws.cell(r, LABEL_COL).value or "").strip()
        if not lbl:
            continue
        if lbl == "הוצאה" and "expense_header" not in out:
            out["expense_header"] = r
        # Require סה"כ-style total (not bare header "הכנסה" which also contains סה as substring of ... no —
        # "הכנסה" ends with "סה"; require explicit total marker.
        is_total = ("סה\"" in lbl) or ("סה”" in lbl) or ("סהכ" in lbl.replace('"', "").replace("”", "").replace(" ", ""))
        if is_total and "הכנס" in lbl:
            out["income_total"] = r
        elif is_total and "הוצא" in lbl:
            out["expense_total"] = r
        elif "רווח" in lbl or "הפסד" in lbl:
            out["grand_total"] = r
        elif is_total and "תקציב" in lbl and "grand_total" not in out:
            out.setdefault("grand_total", r)
    return out


def _find_rollup_rows(ws, ref_col=CODE_COL+2):
    """
    Backward-compatible API used by tests.
    Prefer label-based section rows; fall back to legacy blank-row scan.
    Returns (income_subtotal_row, expense_total_row, grand_total_row).
    """
    sec = _find_section_rows(ws)
    if sec.get("income_total") or sec.get("expense_total") or sec.get("grand_total"):
        return (
            sec.get("income_total"),
            sec.get("expense_total"),
            sec.get("grand_total"),
        )

    exp_header_row = sec.get("expense_header")
    if exp_header_row is None:
        for r in range(HEADER_ROW+1, ws.max_row+1):
            if str(ws.cell(r, LABEL_COL).value or "").strip()=="הוצאה":
                exp_header_row=r; break
    if exp_header_row is None:
        return None,None,None

    income_subtotal_row=None
    for r in range(HEADER_ROW+1, exp_header_row):
        v_code=ws.cell(r,CODE_COL).value
        v_ref=ws.cell(r,ref_col).value
        if v_code is None and isinstance(v_ref,(int,float)):
            income_subtotal_row=r

    grand_total_row=None
    for r in range(exp_header_row+1, ws.max_row+1):
        lbl=str(ws.cell(r,LABEL_COL).value or "")
        if "סה\"כ" in lbl or "סה”כ" in lbl or "רווח" in lbl:
            grand_total_row=r; break
    if grand_total_row is None:
        return income_subtotal_row,None,None

    expense_total_row=None
    for r in range(exp_header_row+1, grand_total_row):
        v_code=ws.cell(r,CODE_COL).value
        v_ref=ws.cell(r,ref_col).value
        if v_code is None and isinstance(v_ref,(int,float)):
            expense_total_row=r
    if expense_total_row is None and grand_total_row-1>exp_header_row:
        expense_total_row=grand_total_row-1

    return income_subtotal_row,expense_total_row,grand_total_row


def _income_expense_code_sets(rows):
    """Split budget codes into income vs expense by code prefix."""
    income, expense = [], []
    for code, r in rows.items():
        if is_income_budget_code(code):
            income.append((code, r))
        else:
            expense.append((code, r))
    return income, expense


def _fill_rollup_totals(ws, dc, rows, income_subtotal_row, expense_total_row, grand_total_row):
    """
    Phase 5: write NUMERIC totals using code-prefix sums when possible.
    """
    style_ref_col = dc - 4 if dc - 4 >= 1 else dc

    def _style_from(ref_row, target_cell):
        if ref_row is None:
            return
        ref_cell = ws.cell(ref_row, style_ref_col)
        if ref_cell.has_style:
            target_cell.font = copy(ref_cell.font)
            target_cell.fill = copy(ref_cell.fill)
            target_cell.number_format = ref_cell.number_format
            target_cell.alignment = copy(ref_cell.alignment)
            target_cell.border = copy(ref_cell.border)

    inc_list, exp_list = _income_expense_code_sets(rows)
    # Prefer explicit income/expense code sets; fall back to row-range split
    if inc_list or exp_list:
        income_total = round(sum(_num(ws.cell(r, dc).value) for _, r in inc_list), 2)
        expense_total = round(sum(_num(ws.cell(r, dc).value) for _, r in exp_list), 2)
    elif income_subtotal_row is not None and expense_total_row is not None:
        income_rows = [r for r in rows.values() if HEADER_ROW < r < income_subtotal_row]
        expense_rows = [r for r in rows.values() if income_subtotal_row < r < expense_total_row]
        income_total = round(sum(_num(ws.cell(r, dc).value) for r in income_rows), 2)
        expense_total = round(sum(_num(ws.cell(r, dc).value) for r in expense_rows), 2)
    else:
        return

    grand_total = round(expense_total + income_total, 2)

    if income_subtotal_row is not None:
        c = ws.cell(income_subtotal_row, dc, value=income_total)
        _style_from(income_subtotal_row, c)
        if income_total < 0:
            c.font = RED

    if expense_total_row is not None:
        c = ws.cell(expense_total_row, dc, value=expense_total)
        _style_from(expense_total_row, c)
        if expense_total < 0:
            c.font = RED

    if grand_total_row is not None:
        c = ws.cell(grand_total_row, dc, value=grand_total)
        _style_from(grand_total_row, c)
        if grand_total < 0:
            c.font = RED


def _enforce_income_sign(ws, lc, mc, dc, rows):
    """
    Phase 6: income codes must be ≤ 0 on ledger/display; flip if positive.
    Returns list of flipped codes.
    """
    flipped = []
    for code, r in rows.items():
        if not is_income_budget_code(code):
            continue
        led = _num(ws.cell(r, lc).value)
        if led > 0:
            ws.cell(r, lc, value=round(-led, 2))
            flipped.append(code)
        disp = round(_num(ws.cell(r, lc).value) + _num(ws.cell(r, mc).value), 2)
        c = ws.cell(r, dc, value=disp)
        if disp < 0:
            c.font = RED
    return flipped


def _month_num_from_key(month_key):
    try:
        return int(str(month_key).split("-")[1])
    except (IndexError, ValueError):
        return 6


def _find_month_display_col(ws, month_he):
    """Find display (ביצוע) column for a Hebrew month name."""
    for text in (
        f"{month_he} - {DISPLAY_SUFFIX}",
        f"{month_he} {DISPLAY_SUFFIX}",
        f"{month_he}-{DISPLAY_SUFFIX}",
    ):
        c = _find_header(ws, text)
        if c is not None:
            return c
    # bare month name is usually budget, not actual — skip
    return None


def _find_month_budget_col(ws, month_he):
    return _find_header(ws, month_he) or _find_header(ws, month_he + " ")


def _write_ytd(ws, rows, target_month_n, year_suffix="26"):
    """
    Phase 4: write YTD budget, actual, variance columns for months 1..N.
    """
    if target_month_n < 1 or target_month_n > 12:
        return 0

    ytd_budget_h = f'סה"כ תקציב 1-{target_month_n}/{year_suffix}'
    ytd_actual_h = f'סה"כ ביצוע 1-{target_month_n}/{year_suffix}'
    ytd_var_h = f"הפרש YTD 1-{target_month_n}/{year_suffix}"

    # Place after last used header col
    last_col = 1
    for c in range(1, ws.max_column + 1):
        if ws.cell(HEADER_ROW, c).value is not None:
            last_col = c

    # Reuse existing columns if same header already present
    bc = _find_header(ws, ytd_budget_h)
    ac = _find_header(ws, ytd_actual_h)
    vc = _find_header(ws, ytd_var_h)
    ref_col = last_col
    if bc is None:
        last_col += 1
        bc = last_col
        ws.cell(HEADER_ROW, bc, value=ytd_budget_h)
        for r in range(1, ws.max_row + 1):
            _copy_cell_style(ws.cell(r, ref_col), ws.cell(r, bc))
    if ac is None:
        last_col = max(last_col, bc) + 1
        ac = last_col
        ws.cell(HEADER_ROW, ac, value=ytd_actual_h)
        for r in range(1, ws.max_row + 1):
            _copy_cell_style(ws.cell(r, ref_col), ws.cell(r, ac))
    if vc is None:
        last_col = max(last_col, ac) + 1
        vc = last_col
        ws.cell(HEADER_ROW, vc, value=ytd_var_h)
        for r in range(1, ws.max_row + 1):
            _copy_cell_style(ws.cell(r, ref_col), ws.cell(r, vc))

    budget_cols = []
    actual_cols = []
    for i in range(1, target_month_n + 1):
        mhe = MONTHS_HE[i - 1]
        bcol = _find_month_budget_col(ws, mhe)
        dcol = _find_month_display_col(ws, mhe)
        if bcol:
            budget_cols.append(bcol)
        if dcol:
            actual_cols.append(dcol)

    written = 0
    for code, r in rows.items():
        bsum = round(sum(_num(ws.cell(r, c).value) for c in budget_cols), 2)
        asum = round(sum(_num(ws.cell(r, c).value) for c in actual_cols), 2)
        var = round(asum - bsum, 2)
        ws.cell(r, bc, value=bsum)
        c_a = ws.cell(r, ac, value=asum)
        if asum < 0:
            c_a.font = RED
        c_v = ws.cell(r, vc, value=var)
        if var < 0:
            c_v.font = RED
        written += 1

    # YTD rollups on section rows
    isub, etot, gtot = _find_rollup_rows(ws)
    for col in (bc, ac, vc):
        _fill_rollup_totals(ws, col, rows, isub, etot, gtot)

    return written


def _sync(ws, month_he, month_key, sheet_key, movement):
    lc, mc, dc = _ensure_two_layer(ws, month_he)
    rows = _code_rows(ws)
    for r in rows.values():
        ws.cell(r, lc, value=0)
    written = 0
    for (sk, code, mk), amt in movement.items():
        if sk != sheet_key or mk != month_key:
            continue
        r = rows.get(code)
        if r is None:
            continue
        ws.cell(r, lc, value=round(amt, 2))
        written += 1

    # display = ledger + manual
    for r in rows.values():
        disp = round(_num(ws.cell(r, lc).value) + _num(ws.cell(r, mc).value), 2)
        c = ws.cell(r, dc, value=disp)
        if disp < 0:
            c.font = RED

    # Phase 6: force income sign on system layer
    flipped = _enforce_income_sign(ws, lc, mc, dc, rows)

    isub, etot, gtot = _find_rollup_rows(ws)
    _fill_rollup_totals(ws, dc, rows, isub, etot, gtot)
    return written, dc, rows, flipped


def _format_variance(ws, rows):
    """Colour the 'ביצוע מול תקציב' column green(≥0)/red(<0) if present."""
    vc = _find_header(ws, "ביצוע מול תקציב")
    if vc is None:
        return
    for r in rows.values():
        v = ws.cell(r, vc).value
        if isinstance(v, (int, float)):
            ws.cell(r, vc).font = Font(color=("00A050" if v >= 0 else "C00000"))


def _apply_polish(ws):
    """Clean layout, freeze panes, show gridlines, auto-widen columns, format numbers."""
    ws.sheet_view.rightToLeft = True
    if ws.views.sheetView:
        ws.views.sheetView[0].showGridLines = True
    ws.freeze_panes = "C3"

    ws.column_dimensions["A"].width = 14
    ws.column_dimensions["B"].width = 34

    acct_format = '_ * #,##0_ ;_ * \\-#,##0_ ;_ * "-"??_ ;_ @_ '
    for c in range(3, ws.max_column + 1):
        col_letter = get_column_letter(c)
        hdr_val = str(ws.cell(HEADER_ROW, c).value or "")
        ws.column_dimensions[col_letter].width = max(len(hdr_val) + 4, 16)

    for r in range(HEADER_ROW + 1, ws.max_row + 1):
        for c in range(3, ws.max_column + 1):
            cell = ws.cell(r, c)
            if isinstance(cell.value, (int, float)):
                if not cell.number_format or cell.number_format == "General":
                    cell.number_format = acct_format


def _write_engine_footer(ws):
    r = ws.max_row + 2
    ws.cell(r, 1, value=ENGINE_FOOTER)
    ws.cell(r, 1).font = Font(italic=True, color="808080", size=9)


def build(src_path, branch_key, movement, out_path, target_month_he="יוני",
          month_key="2026-06"):
    tab = SRC_TABS[branch_key]
    out, ws = _extract_tab(src_path, tab, out_path)
    # Phase 1: strip pricing notes before any writes
    _strip_note_rows(ws)
    written, dc, rows, flipped = _sync(
        ws, target_month_he, month_key, SHEET_KEY[branch_key], movement
    )
    # Phase 4: YTD through target month
    n = _month_num_from_key(month_key)
    year_suffix = str(month_key).split("-")[0][-2:] if month_key else "26"
    _write_ytd(ws, rows, n, year_suffix=year_suffix)
    _format_variance(ws, rows)
    _apply_polish(ws)
    _write_engine_footer(ws)
    out.save(out_path)
    out.close()
    return written
