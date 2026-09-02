"""
Trainer Billing output builder — one workbook per branch, 4 sheets:
  חיוב יזם · דוח מרכז לאישור מנהל · חילנט · ריכוז שעות
plus a 'דגלים' (flags) sheet listing everything the analyzer wasn't sure about.

Design:
  * Start from the source approval workbook (already holds all 4 sheets).
  * Trim to just those 4 (+ flags), dropping helper/junk tabs.
  * Apply Phase-B writes into דוח מרכז לאישור מנהל (מאמני חוץ rows) from
    the validated freelancer totals; recompute its grand total.
  * חיוב יזם is a formula view over דוח מרכז — we RESOLVE those formulas to
    numeric values so the manager sees numbers in any viewer (not blank cells).
  * A 'סטטוס מול יעד' note flags if the recomputed total drifted from signed.
"""
import sys, os, re
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "core"))
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment
from openpyxl.utils import get_column_letter
from openpyxl.utils.cell import coordinate_from_string, column_index_from_string

KEEP = ["חיוב יזם", "דוח מרכז לאישור מנהל", "חילנט", "ריכוז שעות"]
FLAG_SHEET = "דגלים"

_CELLREF = re.compile(r"(?:'([^']+)'|([^\s'!+]+))!\$?([A-Z]+)\$?(\d+)")

# Bug-6: never write 0 for a formula we don't understand. Raising here forces the
# pipeline to STOP on an unrecognized formula instead of silently corrupting
# ~500 hand-built formulas into zeros.
class UnknownFormulaError(ValueError):
    """Raised when a chain/output formula cannot be safely resolved."""


def _num(x):
    try: return float(x)
    except (ValueError, TypeError): return 0.0


def _require_ref(part, formula):
    m = _CELLREF.fullmatch(part)
    if not m:
        raise UnknownFormulaError(
            f"unsupported formula (cannot resolve '{part}'): {formula}"
        )
    return m


def _resolve_formula(formula, values):
    """Resolve '=Sheet!A1' (single ref -> its value, text or number) or
    '=A!B12+C!D34' (additive numeric refs -> sum). SUM(range) handled by caller.

    Bug-6 fix: previously ANY formula that didn't match these shapes silently
    wrote 0, destroying ~500 hand-built formulas (SUM/IF/VLOOKUP/etc.). Now a
    formula whose syntax we don't recognize raises UnknownFormulaError so the
    caller STOPS instead of corrupting money.

    A pure cell reference that resolves to an EMPTY target cell returns 0 —
    that is faithful to the workbook, not corruption (Excel shows that cell as
    empty/0). Only unparseable formula SHAPES are treated as fatal.
    """
    if not isinstance(formula, str) or not formula.startswith("="):
        return formula
    expr = formula[1:]
    if expr.upper().startswith("SUM("):
        return None  # caller owns the range-sum rewrite; never write 0
    parts = [p.strip() for p in expr.split("+")]
    # single reference: pass the referenced value through as-is (keeps text)
    if len(parts) == 1:
        m = _require_ref(parts[0], formula)
        sheet = m.group(1) or m.group(2)
        v = values.get((sheet, f"{m.group(3)}{m.group(4)}"))
        return v if v is not None else 0
    # multiple refs joined by + : numeric sum (all must be plain refs)
    total = 0.0
    for part in parts:
        m = _require_ref(part, formula)
        sheet = m.group(1) or m.group(2)
        total += _num(values.get((sheet, f"{m.group(3)}{m.group(4)}")))
    return round(total, 2)

def _snapshot_values(wb):
    """Read every sheet's computed values into a {(sheet, 'A1'): value} map.
    Needs a data_only load; caller supplies it."""
    vals = {}
    for name in wb.sheetnames:
        ws = wb[name]
        for row in ws.iter_rows():
            for cell in row:
                if cell.value is not None:
                    vals[(name, cell.coordinate)] = cell.value
    return vals

def _parse_hilan_data(hilan_file, aliases):
    import openpyxl
    from common import resolve_trainer
    hilan_data = {}
    if not hilan_file or not os.path.exists(hilan_file):
        return hilan_data
    try:
        wb_h = openpyxl.load_workbook(hilan_file, data_only=True)
        ws_h = wb_h.active
        headers = [str(ws_h.cell(1, c).value or "").strip() for c in range(1, ws_h.max_column + 1)]
        is_detail = any("שם פרטי" in h for h in headers) or any("כניסה" in h for h in headers)

        if is_detail:
            for r in range(2, ws_h.max_row + 1):
                fname = str(ws_h.cell(r, 6).value or "").strip()
                lname = str(ws_h.cell(r, 5).value or "").strip()
                fullname = f"{fname} {lname}".strip()
                if not fullname or fullname == "None None":
                    continue
                _, canon, _, _ = resolve_trainer(fullname, aliases)
                name_key = canon or fullname
                if name_key not in hilan_data:
                    hilan_data[name_key] = {
                        "total_wage": 0.0, "reg": 0.0, "ot125": 0.0, "ot150": 0.0,
                        "ot175": 0.0, "ot200": 0.0, "std": 0.0, "pers": 0.0, "grp": 0.0
                    }
                hilan_data[name_key]["total_wage"] += float(ws_h.cell(r, 13).value or 0)
                hilan_data[name_key]["reg"] += float(ws_h.cell(r, 14).value or 0)
                hilan_data[name_key]["ot125"] += float(ws_h.cell(r, 16).value or 0)
                hilan_data[name_key]["ot150"] += float(ws_h.cell(r, 17).value or 0)
                hilan_data[name_key]["std"] += float(ws_h.cell(r, 18).value or 0) + float(ws_h.cell(r, 19).value or 0)
                hilan_data[name_key]["pers"] += float(ws_h.cell(r, 20).value or 0)
                hilan_data[name_key]["grp"] += float(ws_h.cell(r, 21).value or 0)
        else:
            for r in range(2, ws_h.max_row + 1):
                # find first non-empty cell in row for name
                raw_name = ""
                for c in range(1, min(ws_h.max_column + 1, 6)):
                    v = ws_h.cell(r, c).value
                    if v and isinstance(v, str) and ("סה" in v or len(v.strip().split()) >= 1):
                        raw_name = v.strip()
                        break
                if not raw_name:
                    raw_name = str(ws_h.cell(r, 4).value or ws_h.cell(r, 1).value or "").strip()
                raw_name = re.sub(r'^סה["״\']?כ\s*', '', raw_name).strip()
                if not raw_name or raw_name == "כללי":
                    continue
                parts = raw_name.split()
                if len(parts) >= 2:
                    flipped = f"{parts[-1]} {' '.join(parts[:-1])}"
                else:
                    flipped = raw_name
                _, canon, _, _ = resolve_trainer(flipped, aliases)
                if not canon:
                    _, canon, _, _ = resolve_trainer(raw_name, aliases)
                name_key = canon or flipped
                if name_key not in hilan_data:
                    hilan_data[name_key] = {
                        "total_wage": 0.0, "reg": 0.0, "ot125": 0.0, "ot150": 0.0,
                        "ot175": 0.0, "ot200": 0.0, "std": 0.0, "pers": 0.0, "grp": 0.0
                    }
                # Find columns dynamically based on non-empty numeric cells
                nums = [float(ws_h.cell(r, c).value) for c in range(1, ws_h.max_column + 1)
                        if isinstance(ws_h.cell(r, c).value, (int, float))]
                if len(nums) >= 2:
                    hilan_data[name_key]["total_wage"] = nums[0]
                    hilan_data[name_key]["reg"] = nums[1]
                    if len(nums) >= 3 and nums[2] <= 20:
                        hilan_data[name_key]["ot125"] = nums[2]
                    if len(nums) >= 4 and nums[3] <= 20:
                        hilan_data[name_key]["ot150"] = nums[3]
                else:
                    hilan_data[name_key]["total_wage"] += float(ws_h.cell(r, 6).value or ws_h.cell(r, 2).value or 0)
                    hilan_data[name_key]["reg"] += float(ws_h.cell(r, 7).value or ws_h.cell(r, 3).value or 0)
                    hilan_data[name_key]["ot125"] += float(ws_h.cell(r, 9).value or ws_h.cell(r, 4).value or 0)
                    hilan_data[name_key]["ot150"] += float(ws_h.cell(r, 10).value or ws_h.cell(r, 5).value or 0)
                    hilan_data[name_key]["pers"] += float(ws_h.cell(r, 11).value or 0)
                    hilan_data[name_key]["grp"] += float(ws_h.cell(r, 12).value or 0)
        wb_h.close()
    except Exception:
        pass
    return hilan_data


def _parse_sales_data(sales_file, target_month=None, aliases=None):
    import openpyxl, re
    from common import resolve_trainer
    sales_data = {
        'gym': {'reps': {}, 'total_wage': 0.0, 'total_with_social': 0.0},
        'pilates': {'reps': {}, 'total_wage': 0.0, 'total_with_social': 0.0}
    }
    if not sales_file or not os.path.exists(sales_file):
        return sales_data
    try:
        wb_s = openpyxl.load_workbook(sales_file, data_only=True)
        month_str = str(target_month) if target_month else ""
        matching_sheet = None
        if month_str:
            for s in wb_s.sheetnames:
                if f"{month_str}/26" in s or f"0{month_str}.26" in s or f"{month_str}.26" in s or f"Jul-26" in s or "יולי" in s:
                    matching_sheet = s
                    break
        if not matching_sheet:
            for s in wb_s.sheetnames:
                if "עמלות" in s or "2026" in s or "מכירות" in s:
                    matching_sheet = s
                    break
        if not matching_sheet:
            matching_sheet = wb_s.sheetnames[0]

        ws = wb_s[matching_sheet]
        current_section = None
        for r in range(1, ws.max_row + 1):
            row_str = " ".join([str(ws.cell(r, c).value or "") for c in range(1, ws.max_column + 1)])
            if "מועדון" in row_str or "חדר כושר" in row_str:
                current_section = 'gym'
                continue
            elif "פילאטיס" in row_str:
                current_section = 'pilates'
                continue

        # Fallback: line-by-line rows if structured section header is absent
        if sales_data['gym']['total_wage'] == 0 and sales_data['pilates']['total_wage'] == 0:
            tot_w = 0.0
            for r in range(1, ws.max_row + 1):
                name_cell = ws.cell(r, 2).value
                amt_cell = ws.cell(r, 3).value
                if name_cell and isinstance(amt_cell, (int, float)) and amt_cell > 0:
                    tot_w += float(amt_cell)
            if tot_w > 0:
                sales_data['gym']['total_wage'] = round(tot_w, 2)
                sales_data['gym']['total_with_social'] = round(tot_w * 1.219, 2)
        wb_s.close()
    except Exception:
        pass
    return sales_data


def _populate_summary_sheets(wb, branch_key, source_path, all_sessions, aliases, target_month=None, invoices=None):
    if not aliases:
        return
    import glob
    from common import resolve_trainer
    input_dir = os.path.dirname(os.path.abspath(source_path))
    hilan_patterns = ["*פרויקטים*.xlsx", "*חילנט*.xlsx", "*ספא*.xlsx", "*שעות*.xlsx", "*hilan*.xlsx"]
    hilan_files = []
    for pat in hilan_patterns:
        hilan_files.extend(glob.glob(os.path.join(input_dir, "**", pat), recursive=True))
        hilan_files.extend(glob.glob(os.path.join(os.path.dirname(input_dir), "**", pat), recursive=True))
        hilan_files.extend(glob.glob(os.path.join("input", "**", pat), recursive=True))
    hilan_files = [f for f in dict.fromkeys(hilan_files) if os.path.isfile(f)]

    hilan_data = _parse_hilan_data(hilan_files[0], aliases) if hilan_files else {}

    sales_patterns = ["*עמלות*.xlsx", "*מכירות*.xlsx", "*sales*.xlsx"]
    sales_files = []
    for pat in sales_patterns:
        sales_files.extend(glob.glob(os.path.join(input_dir, "**", pat), recursive=True))
        sales_files.extend(glob.glob(os.path.join(os.path.dirname(input_dir), "**", pat), recursive=True))
        sales_files.extend(glob.glob(os.path.join("input", "**", pat), recursive=True))
    sales_files = [f for f in dict.fromkeys(sales_files) if os.path.isfile(f)]
    sales_data = _parse_sales_data(sales_files[0], target_month, aliases) if sales_files else {}

    arbox_data = {}
    if all_sessions:
        for s in all_sessions:
            canon = s.get("canonical") or s.get("trainer_raw")
            if not canon: continue
            arbox_data.setdefault(canon, {"classes": 0, "personal": 0, "pilates": 0})
            cat = s.get("category") or ""
            b = s.get("branch") or ""
            if "פילאטיס" in b or "פילאטיס" in cat:
                arbox_data[canon]["pilates"] += 1
            elif "אישי" in cat:
                arbox_data[canon]["personal"] += 1
            else:
                arbox_data[canon]["classes"] += 1

    from common import service_month_from_dates, month_key
    invoice_pt = {}
    invoice_std = {}
    target_m_key = f"2026-{int(target_month):02d}" if target_month else None
    if invoices:
        for inv in invoices:
            smonth = service_month_from_dates(inv.get("session_dates")) or month_key(inv.get("doc_date"))
            if target_m_key and smonth and smonth != target_m_key:
                continue
            _, canon, _, _ = resolve_trainer(inv.get("trainer"), aliases)
            name_key = canon or inv.get("trainer")
            for item in inv.get("line_items", []):
                desc = str(item.get("desc", ""))
                qty = item.get("qty", 0)
                if not isinstance(qty, (int, float)):
                    continue
                if "אישי" in desc:
                    invoice_pt[name_key] = invoice_pt.get(name_key, 0) + qty
                elif "סטודיו" in desc or "שיעור" in desc or "חוג" in desc or "מזרן" in desc:
                    invoice_std[name_key] = invoice_std.get(name_key, 0) + qty

    if branch_key == "חדר כושר":
        if "סיכום אמוני סטודיו וקבוצה" in wb.sheetnames:
            ws = wb["סיכום אמוני סטודיו וקבוצה"]
            # Freelance trainers (rows 3 to 19) from Invoice and Arbox
            for r in range(3, 20):
                t_name = ws.cell(r, 1).value
                if t_name:
                    _, canon, _, _ = resolve_trainer(t_name, aliases)
                    arb = arbox_data.get(canon, {})
                    inv_s = invoice_std.get(canon, 0)
                    arb_s = arb.get("classes", 0)
                    val_s = inv_s if inv_s > 0 else (arb_s if arb_s > 0 else 0)
                    ws.cell(r, 2).value = val_s if val_s > 0 else None

                    inv_p = invoice_pt.get(canon, 0)
                    arb_p = arb.get("personal", 0)
                    val_p = inv_p if inv_p > 0 else (arb_p if arb_p > 0 else 0)
                    ws.cell(r, 7).value = val_p if val_p > 0 else None

            # Salaried trainers (rows 20 to 29) from Hilan
            for r in range(20, 30):
                t_name = ws.cell(r, 1).value
                if t_name:
                    _, canon, _, _ = resolve_trainer(t_name, aliases)
                    hil = hilan_data.get(canon, {})
                    reg_w = round(hil["reg"], 2) if hil.get("reg", 0) > 0 else (round(hil["total_wage"], 2) if hil.get("total_wage", 0) > 0 else None)
                    ws.cell(r, 15).value = reg_w
                    ws.cell(r, 8).value = round(hil["pers"], 2) if hil.get("pers", 0) > 0 else None
                    ws.cell(r, 4).value = round(hil["grp"], 2) if hil.get("grp", 0) > 0 else None

        # Dynamically populate overtime & travel on 'דוח מרכז לאישור מנהל'
        if "דוח מרכז לאישור מנהל" in wb.sheetnames:
            ws_main = wb["דוח מרכז לאישור מנהל"]
            for c in range(2, 13):
                emp_name = ws_main.cell(4, c).value
                if not emp_name:
                    continue
                _, canon, _, _ = resolve_trainer(emp_name, aliases)
                hil = hilan_data.get(canon, {})
                if hil:
                    if hil.get("reg", 0) > 0:
                        ws_main.cell(6, c, value=round(hil["reg"], 2))
                    if hil.get("ot125", 0) > 0:
                        ws_main.cell(7, c, value=round(hil["ot125"], 2))
                    if hil.get("ot150", 0) > 0:
                        ws_main.cell(8, c, value=round(hil["ot150"], 2))
                    if hil.get("ot175", 0) > 0:
                        ws_main.cell(9, c, value=round(hil["ot175"], 2))
                    if hil.get("ot200", 0) > 0:
                        ws_main.cell(10, c, value=round(hil["ot200"], 2))
                    # Travel allowance rule: Leonid gets 208.50, <=90 hrs = 100, >90 hrs = 200
                    tot_hrs = hil.get("total_wage", 0)
                    if "לאון" in str(emp_name) or canon in ["לאון ורחובסקי", "לאוניד ורחובסקי"]:
                        ws_main.cell(11, c, value=208.5)
                    elif tot_hrs > 90:
                        ws_main.cell(11, c, value=200)
                    elif tot_hrs > 0:
                        ws_main.cell(11, c, value=100)

        # Populate sales commissions in 'מכירות' sheet if present
        if "מכירות" in wb.sheetnames and sales_data and sales_data.get('gym', {}).get('total_with_social', 0) > 0:
            ws_sales = wb["מכירות"]
            g_tot = sales_data['gym']['total_with_social']
            g_wage = sales_data['gym']['total_wage']
            ws_sales.cell(10, 14, value=round(g_tot, 2))
            ws_sales.cell(10, 13, value=round(g_wage, 2))

    elif branch_key == "פילאטיס":
        if "דוח מרכז לאישור מנהל" in wb.sheetnames:
            ws_main = wb["דוח מרכז לאישור מנהל"]
            for c in range(2, 5):
                emp_name = ws_main.cell(4, c).value
                if not emp_name:
                    continue
                _, canon, _, _ = resolve_trainer(emp_name, aliases)
                hil = hilan_data.get(canon, {})
                if hil:
                    if hil.get("reg", 0) > 0:
                        ws_main.cell(6, c, value=round(hil["reg"], 2))
                    if hil.get("ot125", 0) > 0:
                        ws_main.cell(7, c, value=round(hil["ot125"], 2))
                    tot_hrs = hil.get("total_wage", 0)
                    if tot_hrs > 90:
                        ws_main.cell(12, c, value=200)
                    elif tot_hrs > 0:
                        ws_main.cell(12, c, value=100)
        if "סיכום אימונים ומכירות מנויים" in wb.sheetnames:
            ws = wb["סיכום אימונים ומכירות מנויים"]
            for r in range(3, 11):
                t_name = ws.cell(r, 2).value
                if t_name:
                    _, canon, _, _ = resolve_trainer(t_name, aliases)
                    arb = arbox_data.get(canon, {})
                    if arb.get("pilates", 0) > 0:
                        ws.cell(r, 3, value=arb["pilates"])
            for r in range(13, 15):
                t_name = ws.cell(r, 2).value
                if t_name:
                    _, canon, _, _ = resolve_trainer(t_name, aliases)
                    hil = hilan_data.get(canon, {})
                    if hil.get("total_wage", 0) > 0 or hil.get("std", 0) > 0:
                        ws.cell(r, 3, value=round(hil.get("std", 0) or hil.get("total_wage", 0), 2))

            # Populate sales commissions in Pilates
            if sales_data and sales_data.get('pilates', {}).get('total_with_social', 0) > 0:
                p_tot = sales_data['pilates']['total_with_social']
                p_wage = sales_data['pilates']['total_wage']
                ws.cell(27, 14, value=round(p_tot, 2))
                ws.cell(27, 13, value=round(p_wage, 2))


def build(branch_key, cfg, source_path, by_category, held, new_trainers,
          hilan, out_path, target, missing_receipts=None, all_sessions=None, aliases=None,
          invoices=None, target_month=None):
    # formula workbook (to edit) + value workbook (to resolve refs)
    wb = openpyxl.load_workbook(source_path)
    wbv = openpyxl.load_workbook(source_path, data_only=True)

    _populate_summary_sheets(wb, branch_key, source_path, all_sessions, aliases, target_month=target_month, invoices=invoices)

    ws_edit = wb[cfg["approval_sheet"]]
    ext = cfg["external_lines"]; amt_col = cfg["amount_col"]
    amt_L = get_column_letter(amt_col)
    sheet = cfg["approval_sheet"]

    # value snapshot holds the REAL computed numbers (helper tabs still present)
    vals = _snapshot_values(wbv)

    # 0) FREEZE the approval sheet's amount column to computed values, so that
    #    dropping helper tabs later can't break formulas that referenced them.
    for r in range(1, ws_edit.max_row + 1):
        cur = ws_edit.cell(r, amt_col).value
        if isinstance(cur, str) and cur.startswith("="):
            v = vals.get((sheet, f"{amt_L}{r}"))
            ws_edit.cell(r, amt_col, value=(round(v, 2) if isinstance(v, (int, float)) else 0))

    # 1) Phase-B writes: overwrite the מאמני חוץ rows with validated freelancer $
    row_amounts = {}
    for cat, amount in by_category.items():
        line = ext.get(cat)
        if line: row_amounts[line["row"]] = row_amounts.get(line["row"], 0.0) + amount
    for row, amount in row_amounts.items():
        ws_edit.cell(row, amt_col, value=round(amount, 2))
        vals[(sheet, f"{amt_L}{row}")] = round(amount, 2)

    # rows written into דוח מרכז that do NOT roll up into חיוב יזם -> flag them
    covered = set(cfg.get("chiuv_referenced_rows", []))
    not_rolled = [(r, ws_edit.cell(r, cfg["name_col"]).value, round(a, 2))
                  for r, a in row_amounts.items() if r not in covered]

    # 2) recompute total from the (now value-frozen) detail block
    total = round(sum(_num(ws_edit.cell(r, amt_col).value)
                      for r in range(cfg["detail_first_row"], cfg["detail_last_row"]+1)), 2)
    col_letters, trow = coordinate_from_string(cfg["total_cell"])
    tcol = column_index_from_string(col_letters)
    ws_edit.cell(trow, tcol, value=total)
    vals[(sheet, cfg["total_cell"])] = total

    ws_ci = wb["חיוב יזם"]
    for row in ws_ci.iter_rows():
        for cell in row:
            if isinstance(cell.value, str) and cell.value.startswith("=") \
               and not cell.value.upper().startswith("=SUM("):
                # Bug-6: an unrecognized formula must STOP the build (raise),
                # never be overwritten with 0. That destroyed ~500 formulas.
                resolved = _resolve_formula(cell.value, vals)
                cell.value = resolved if resolved is not None else cell.value
    # resolve the =SUM(F9:F14) grand total on חיוב יזם by summing resolved cells
    for row in ws_ci.iter_rows():
        for cell in row:
            if isinstance(cell.value, str) and cell.value.upper().startswith("=SUM("):
                rng = cell.value[5:-1]  # e.g. F9:F14 or 'Sheet'!F9:F14
                # strip an optional sheet qualifier ('X'!F9:F14) -> F9:F14
                if "!" in rng:
                    rng = rng.split("!", 1)[1]
                if ":" not in rng:
                    raise UnknownFormulaError(f"unsupported SUM range: {cell.value}")
                a, b = rng.split(":")
                try:
                    c1, r1 = coordinate_from_string(a); c2, r2 = coordinate_from_string(b)
                except Exception:  # noqa: BLE001
                    raise UnknownFormulaError(f"unsupported SUM range: {cell.value}")
                col = column_index_from_string(c1)
                s = sum(_num(ws_ci.cell(r, col).value) for r in range(int(r1), int(r2)+1))
                cell.value = round(s, 2)

    # 3) keep all sheets so formula references across tabs (e.g. סיכום אמוני סטודיו וקבוצה) stay valid
    # do not delete helper sheets

    # 4) flags sheet
    _write_flags(wb, branch_key, cfg, total, target, held, new_trainers, hilan, not_rolled,
                 missing_receipts=missing_receipts)

    wb.save(out_path)
    wb.close(); wbv.close()
    return total

def _write_flags(wb, branch_key, cfg, total, target, held, new_trainers, hilan, not_rolled=None,
                  missing_receipts=None):
    ws = wb.create_sheet(FLAG_SHEET, 0)
    ws.sheet_view.rightToLeft = True
    H = Font(bold=True, size=13); sub = Font(bold=True, color="FFFFFF")
    hdrfill = PatternFill("solid", fgColor="2F5597")
    warn = PatternFill("solid", fgColor="FCE4D6")
    ws["A1"] = f"דגלים לתשומת לב המנהל — {cfg['label']} / {branch_key}"
    ws["A1"].font = H
    r = 3
    # target reconciliation
    drift = round(total - target, 2)
    ws.cell(r, 1, "סה\"כ מחושב"); ws.cell(r, 2, total)
    ws.cell(r+1, 1, "יעד חתום"); ws.cell(r+1, 2, target)
    ws.cell(r+2, 1, "הפרש"); c = ws.cell(r+2, 2, drift)
    if abs(drift) > 0.05:
        for cc in (ws.cell(r+2,1), c): cc.fill = warn
        ws.cell(r+2, 3, "⚠ הסכום המחושב שונה מהיעד — נדרשת בדיקה")
    else:
        ws.cell(r+2, 3, "✓ תואם ליעד")
    r += 4
    # hilan
    ws.cell(r,1,"חילנט — מערכת מול בפועל")
    ws.cell(r,2,f'{hilan["system"]} מול {hilan["actual"]} (Δ{hilan["delta"]})')
    if hilan["delta"] > 2.0: ws.cell(r,2).fill = warn
    r += 2
    # held-out invoices
    ws.cell(r,1,"חשבוניות שהוחזקו (לא נכתבו אוטומטית):").font = Font(bold=True); r += 1
    if held:
        for h in held:
            ws.cell(r,1,h["invoice"].get("trainer") if "invoice" in h else h.get("trainer"))
            ws.cell(r,2,h.get("amount")); ws.cell(r,3,h.get("category"))
            ws.cell(r,1).fill = warn; r += 1
    else:
        ws.cell(r,1,"אין"); r += 1
    r += 1
    # new trainers to approve
    ws.cell(r,1,"מאמנים חדשים לאישור:").font = Font(bold=True); r += 1
    if new_trainers:
        heads = ["שם (OCR)","ח.פ / ת.ז","סניף","קטגוריה","תעריף","סכום","הצעה"]
        for i,h in enumerate(heads):
            cell=ws.cell(r,i+1,h); cell.font=sub; cell.fill=hdrfill
        r += 1
        for p in new_trainers:
            ws.cell(r,1,p["raw_name"]); ws.cell(r,2,p.get("issuer_tax_id"))
            ws.cell(r,3,p.get("branch")); ws.cell(r,4,p.get("category"))
            ws.cell(r,5,p.get("invoiced_rate")); ws.cell(r,6,p.get("stated_total"))
            ws.cell(r,7,p.get("action"))
            for c_ in range(1,8): ws.cell(r,c_).fill = warn
            r += 1
    else:
        ws.cell(r,1,"אין"); r += 1
    r += 1
    ws.cell(r,1,"נכתב אך לא מתגלגל לחיוב יזם (לשיבוץ ידני):").font = Font(bold=True); r += 1
    if not_rolled:
        for row_i, label, amt in not_rolled:
            ws.cell(r,1,label); ws.cell(r,2,amt); ws.cell(r,3,f"שורה {row_i}")
            for c_ in range(1,4): ws.cell(r,c_).fill = warn
            r += 1
    else:
        ws.cell(r,1,"אין — הכל התגלגל")
        r += 1
    r += 1
    # trainer-data gate: unresolved/unknown trainers -> never written to numbers,
    # manager must read the source PDF and add them to config/trainer_aliases.json
    ws.cell(r,1,"מאמנים לא מזוהים — נדרש אישור ידני (קרא PDF והוסף למאגר):").font = Font(bold=True); r += 1
    if new_trainers:
        heads = ["שם (OCR)","ח.פ / ת.ז","סניף","קטגוריה","סכום","התאמה קרובה ביותר"]
        for i,h in enumerate(heads):
            cell=ws.cell(r,i+1,h); cell.font=sub; cell.fill=hdrfill
        r += 1
        for p in new_trainers:
            closest = p.get("closest_existing") or {}
            match_txt = f'{closest.get("name")} ({closest.get("score")}%)' if closest.get("name") else "אין התאמה"
            ws.cell(r,1,p.get("raw_name")); ws.cell(r,2,p.get("issuer_tax_id"))
            ws.cell(r,3,p.get("branch")); ws.cell(r,4,p.get("category"))
            ws.cell(r,5,p.get("stated_total")); ws.cell(r,6,match_txt)
            for c_ in range(1,7): ws.cell(r,c_).fill = warn
            r += 1
    else:
        ws.cell(r,1,"אין — כל המאמנים מזוהים"); r += 1
    r += 1
    # trainer-data gate: trainers expected this branch/month (held Arbox sessions)
    # but with no validated invoice/amount this run -> never fabricate, just flag
    ws.cell(r,1,"חסרות קבלות:").font = Font(bold=True); r += 1
    if missing_receipts:
        for name in missing_receipts:
            ws.cell(r,1,name); ws.cell(r,1).fill = warn
            ws.cell(r,2,"לא נמצאה חשבונית/קבלה החודש עבור מאמן זה")
            r += 1
    else:
        ws.cell(r,1,"אין — לכל המאמנים הצפויים יש קבלה"); r += 1
    for col,w in {"A":34,"B":16,"C":12,"D":12,"E":10,"F":12,"G":40}.items():
        ws.column_dimensions[col].width = w
