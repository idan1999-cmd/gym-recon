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
FILL_RED_ALERT = PatternFill(start_color="FFEBEE", end_color="FFEBEE", fill_type="solid")
FONT_RED_ALERT = Font(name="Calibri", size=10, bold=True, color="C00000")
FILL_GREEN_OK = PatternFill(start_color="E8F5E9", end_color="E8F5E9", fill_type="solid")
FONT_GREEN_OK = Font(name="Calibri", size=10, color="2E7D32")
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


def _strip_top_metric_rows(ws):
    """
    Remove subscriber/metric rows at the top before the first P&L budget code row.
    """
    first_code_row = None
    for r in range(HEADER_ROW + 1, ws.max_row + 1):
        if _code_str(ws.cell(r, CODE_COL).value):
            first_code_row = r
            break
    if first_code_row and first_code_row > HEADER_ROW + 1:
        to_delete = list(range(HEADER_ROW + 1, first_code_row))
        for r in reversed(to_delete):
            ws.delete_rows(r, 1)
        return len(to_delete)
    return 0


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
    Phase 5: locate structural rows by label and layout.
    Returns dict with keys: expense_header, income_total, expense_total, grand_total
    """
    out = {}
    exp_h = None
    gtot = None
    for r in range(HEADER_ROW + 1, ws.max_row + 1):
        lbl = str(ws.cell(r, LABEL_COL).value or "").strip()
        code = _code_str(ws.cell(r, CODE_COL).value)
        if not lbl and not code:
            continue
        if lbl == "הוצאה" and exp_h is None:
            exp_h = r
            out["expense_header"] = r
        is_total = ("סה\"" in lbl) or ("סה”" in lbl) or ("סהכ" in lbl.replace('"', "").replace("”", "").replace(" ", ""))
        if is_total and "הכנס" in lbl:
            out["income_total"] = r
        elif is_total and "הוצא" in lbl:
            out["expense_total"] = r
        elif (is_total or "רווח" in lbl or "הפסד" in lbl) and gtot is None:
            gtot = r
            out["grand_total"] = r

    if "income_total" not in out and exp_h is not None:
        if exp_h > 1 and _code_str(ws.cell(exp_h - 1, CODE_COL).value) is None:
            out["income_total"] = exp_h - 1
    if "expense_total" not in out and gtot is not None:
        if gtot > 1 and _code_str(ws.cell(gtot - 1, CODE_COL).value) is None:
            out["expense_total"] = gtot - 1
    return out


def _find_rollup_rows(ws, ref_col=CODE_COL+2):
    """
    Returns (income_subtotal_row, expense_total_row, grand_total_row).
    """
    sec = _find_section_rows(ws)
    return (
        sec.get("income_total"),
        sec.get("expense_total"),
        sec.get("grand_total"),
    )


def _income_expense_code_sets(rows):
    """Split budget codes into income vs expense by code prefix."""
    income, expense = [], []
    for code, r in rows.items():
        if is_income_budget_code(code):
            income.append((code, r))
        else:
            expense.append((code, r))
    return income, expense


def _fill_rollup_totals(ws, target_col, rows, income_subtotal_row, expense_total_row, grand_total_row):
    """
    Phase 5: write NUMERIC totals using code-prefix sums across all layers.
    """
    style_ref_col = target_col - 4 if target_col - 4 >= 1 else target_col

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
    if inc_list or exp_list:
        income_total = round(sum(_num(ws.cell(r, target_col).value) for _, r in inc_list), 2)
        expense_total = round(sum(_num(ws.cell(r, target_col).value) for _, r in exp_list), 2)
    elif income_subtotal_row is not None and expense_total_row is not None:
        income_rows = [r for r in rows.values() if HEADER_ROW < r < income_subtotal_row]
        expense_rows = [r for r in rows.values() if income_subtotal_row < r < expense_total_row]
        income_total = round(sum(_num(ws.cell(r, target_col).value) for r in income_rows), 2)
        expense_total = round(sum(_num(ws.cell(r, target_col).value) for r in expense_rows), 2)
    else:
        return

    grand_total = round(expense_total + income_total, 2)

    if income_subtotal_row is not None:
        c = ws.cell(income_subtotal_row, target_col, value=income_total)
        _style_from(income_subtotal_row, c)
        if income_total < 0:
            c.font = RED

    if expense_total_row is not None:
        c = ws.cell(expense_total_row, target_col, value=expense_total)
        _style_from(expense_total_row, c)
        if expense_total < 0:
            c.font = RED

    if grand_total_row is not None:
        c = ws.cell(grand_total_row, target_col, value=grand_total)
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
    for pattern in (
        f"{month_he} - תכנון עדכני",
        f"{month_he} - תכנון ראשוני",
        f"{month_he} - תכנון",
        f"{month_he} תכנון",
        month_he,
        f"{month_he} ",
    ):
        c = _find_header(ws, pattern)
        if c is not None:
            return c
    return None


def _write_ytd(ws, rows, target_month_n, year_suffix="26"):
    """
    Phase 4: write YTD budget, actual, variance columns for months 1..N.
    Reuses existing summary columns if present.
    """
    if target_month_n < 1 or target_month_n > 12:
        return 0

    ytd_budget_h = f'סה"כ תקציב 1-{target_month_n}/{year_suffix}'
    ytd_actual_h = f'סה"כ ביצוע 1-{target_month_n}/{year_suffix}'
    ytd_var_h = "ביצוע מול תקציב"

    bc = None
    ac = None
    vc = None
    for c in range(1, ws.max_column + 1):
        h = str(ws.cell(HEADER_ROW, c).value or "").strip()
        is_budget_total = ("סה\"כ תקציב" in h) or ("סה”כ תקציב" in h) or ("סהכ תקציב" in h)
        is_actual_total = ("סה\"כ ביצוע" in h) or ("סה”כ ביצוע" in h) or ("סהכ ביצוע" in h)
        if is_budget_total and bc is None:
            bc = c
        elif is_actual_total and ac is None:
            ac = c
        elif ("ביצוע מול תקציב" in h or "הפרש YTD" in h) and vc is None:
            vc = c

    last_col = 1
    for c in range(1, ws.max_column + 1):
        if ws.cell(HEADER_ROW, c).value is not None:
            last_col = c

    ref_col = last_col
    if bc is None:
        last_col += 1
        bc = last_col
        for r in range(1, ws.max_row + 1):
            _copy_cell_style(ws.cell(r, ref_col), ws.cell(r, bc))
    ws.cell(HEADER_ROW, bc, value=ytd_budget_h)

    if ac is None:
        last_col = max(last_col, bc) + 1
        ac = last_col
        for r in range(1, ws.max_row + 1):
            _copy_cell_style(ws.cell(r, ref_col), ws.cell(r, ac))
    ws.cell(HEADER_ROW, ac, value=ytd_actual_h)

    if vc is None:
        last_col = max(last_col, ac) + 1
        vc = last_col
        for r in range(1, ws.max_row + 1):
            _copy_cell_style(ws.cell(r, ref_col), ws.cell(r, vc))
    current_vc_h = str(ws.cell(HEADER_ROW, vc).value or "").strip()
    if not current_vc_h or "הפרש YTD" in current_vc_h:
        ws.cell(HEADER_ROW, vc, value=ytd_var_h)

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

    # Fill rollup totals across all layers: ledger, manual, and display
    isub, etot, gtot = _find_rollup_rows(ws)
    _fill_rollup_totals(ws, lc, rows, isub, etot, gtot)
    _fill_rollup_totals(ws, mc, rows, isub, etot, gtot)
    _fill_rollup_totals(ws, dc, rows, isub, etot, gtot)
    return written, dc, rows, flipped


def _format_variance(ws, rows, target_month_n=12):
    """
    Highlight variances and overruns with prominent colors across every month and in YTD summary.
    """
    isub, etot, gtot = _find_rollup_rows(ws)

    # 1. Format each month's actual column vs budget column
    for i in range(1, target_month_n + 1):
        mhe = MONTHS_HE[i - 1]
        bcol = _find_month_budget_col(ws, mhe)
        dcol = _find_month_display_col(ws, mhe)
        if not bcol or not dcol:
            continue

        for code, r in rows.items():
            b_val = _num(ws.cell(r, bcol).value)
            d_val = _num(ws.cell(r, dcol).value)
            if ws.cell(r, dcol).value is None or (d_val == 0 and b_val == 0):
                continue

            if is_income_budget_code(code):
                # Income: target met if actual revenue is >= budget revenue
                if abs(d_val) < abs(b_val) - 100:  # missed revenue target
                    ws.cell(r, dcol).fill = FILL_RED_ALERT
                    ws.cell(r, dcol).font = FONT_RED_ALERT
                else:  # met/exceeded revenue target
                    ws.cell(r, dcol).fill = FILL_GREEN_OK
                    ws.cell(r, dcol).font = FONT_GREEN_OK
            else:
                # Expense: under budget is good, over budget is alert
                if d_val > b_val + 100:  # over budget
                    ws.cell(r, dcol).fill = FILL_RED_ALERT
                    ws.cell(r, dcol).font = FONT_RED_ALERT
                elif d_val > 0:  # on or under budget
                    ws.cell(r, dcol).fill = FILL_GREEN_OK
                    ws.cell(r, dcol).font = FONT_GREEN_OK

    # 2. Format YTD variance columns
    var_cols = []
    for c in range(1, ws.max_column + 1):
        h = str(ws.cell(HEADER_ROW, c).value or "").strip()
        if "ביצוע מול תקציב" in h or "הפרש YTD" in h:
            var_cols.append(c)

    for vc in var_cols:
        for code, r in rows.items():
            val = ws.cell(r, vc).value
            if isinstance(val, (int, float)):
                if is_income_budget_code(code):
                    if val > 100:
                        ws.cell(r, vc).fill = FILL_RED_ALERT
                        ws.cell(r, vc).font = FONT_RED_ALERT
                    elif val <= 0:
                        ws.cell(r, vc).fill = FILL_GREEN_OK
                        ws.cell(r, vc).font = FONT_GREEN_OK
                else:
                    if val > 100:
                        ws.cell(r, vc).fill = FILL_RED_ALERT
                        ws.cell(r, vc).font = FONT_RED_ALERT
                    elif val <= 0:
                        ws.cell(r, vc).fill = FILL_GREEN_OK
                        ws.cell(r, vc).font = FONT_GREEN_OK

        if gtot is not None:
            g_val = ws.cell(gtot, vc).value
            if isinstance(g_val, (int, float)):
                if g_val < 0:
                    ws.cell(gtot, vc).fill = FILL_RED_ALERT
                    ws.cell(gtot, vc).font = FONT_RED_ALERT
                else:
                    ws.cell(gtot, vc).fill = FILL_GREEN_OK
                    ws.cell(gtot, vc).font = FONT_GREEN_OK


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
    # Phase 1: strip pricing notes and top subscriber metric rows
    _strip_note_rows(ws)
    _strip_top_metric_rows(ws)
    written, dc, rows, flipped = _sync(
        ws, target_month_he, month_key, SHEET_KEY[branch_key], movement
    )
    # Phase 4: YTD through target month
    n = _month_num_from_key(month_key)
    year_suffix = str(month_key).split("-")[0][-2:] if month_key else "26"
    _write_ytd(ws, rows, n, year_suffix=year_suffix)
    _format_variance(ws, rows, target_month_n=n)
    _apply_polish(ws)
    _write_engine_footer(ws)
    out.save(out_path)
    out.close()
    return written
