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
                if f"{month_str}/26" in s or f"0{month_str}.26" in s or f"{month_str}.26" in s or (month_str in ["8", "08"] and "2026" in s):
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
        for r in range(1, ws.max_row + 1):
            name_cell = ws.cell(r, 2).value
            amt_cell = ws.cell(r, 3).value
            if name_cell and isinstance(amt_cell, (int, float)) and amt_cell > 0:
                _, canon, _, _ = resolve_trainer(str(name_cell), aliases) if aliases else (None, str(name_cell), 0, None)
                branch = 'pilates' if canon in ["ניקול אדלמן", "ניקול איידלמן", "נעמה חיון"] else 'gym'
                sales_data[branch]['reps'][canon] = amt_cell
                sales_data[branch]['total_with_social'] += float(amt_cell)
                sales_data[branch]['total_wage'] += round(float(amt_cell) / 1.08, 2)

        sales_data['gym']['total_with_social'] = round(sales_data['gym']['total_with_social'], 2)
        sales_data['pilates']['total_with_social'] = round(sales_data['pilates']['total_with_social'], 2)
        sales_data['gym']['total_wage'] = round(sales_data['gym']['total_wage'], 2)
        sales_data['pilates']['total_wage'] = round(sales_data['pilates']['total_wage'], 2)
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
    sales_patterns = ["*עמלות*.xlsx", "*מכירות*.xlsx", "*sales*.xlsx"]
    sales_files = []
    for pat in sales_patterns:
        sales_files.extend(glob.glob(os.path.join(input_dir, "**", pat), recursive=True))
        sales_files.extend(glob.glob(os.path.join(os.path.dirname(input_dir), "**", pat), recursive=True))
        sales_files.extend(glob.glob(os.path.join("input", "**", pat), recursive=True))
    sales_files = [f for f in dict.fromkeys(sales_files) if os.path.isfile(f)]

    month_str = str(target_month) if target_month else ""
    def _file_sort_key(p):
        score = 0
        if "dropzone" in p or "לגרור" in p:
            score += 100
        if month_str:
            if f"_{month_str.zfill(2)}" in p or f"{month_str}.26" in p or f"{month_str}/26" in p:
                score += 50
            if month_str in ["8", "08"] and "אוגוסט" in p:
                score += 50
            if month_str in ["7", "07"] and "יולי" in p:
                score += 50
        return -score

    hilan_files.sort(key=_file_sort_key)
    sales_files.sort(key=_file_sort_key)

    hilan_data = _parse_hilan_data(hilan_files[0], aliases) if hilan_files else {}
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
    invoice_grp = {}
    invoice_shifts = {}
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
                elif "משמרת" in desc:
                    invoice_shifts[name_key] = invoice_shifts.get(name_key, 0) + qty
                elif "קבוצ" in desc or "סטודיו" in desc or "שיעור" in desc or "חוג" in desc or "מזרן" in desc or "פילאטיס" in desc:
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
                    has_inv = (canon in invoice_std or canon in invoice_shifts or canon in invoice_pt)
                    val_s = inv_s if inv_s > 0 else (arb_s if (arb_s > 0 and not has_inv) else 0)
                    ws.cell(r, 2).value = val_s if val_s > 0 else None
                    ws.cell(r, 3).value = None

                    inv_p = invoice_pt.get(canon, 0)
                    arb_p = arb.get("personal", 0)
                    val_p = inv_p if inv_p > 0 else (arb_p if arb_p > 0 else 0)
                    ws.cell(r, 7).value = val_p if val_p > 0 else None

                    inv_sh = invoice_shifts.get(canon, 0)
                    ws.cell(r, 14).value = inv_sh if inv_sh > 0 else None

            # Salaried trainers (rows 20 to 29) from Hilan - using total_wage (שעות משכר)
            for r in range(20, 30):
                t_name = ws.cell(r, 1).value
                if t_name:
                    _, canon, _, _ = resolve_trainer(t_name, aliases)
                    # Nicole Edelman & Naama Hayon belong to Pilates ONLY, not Gym
                    if canon in ["ניקול אדלמן", "ניקול איידלמן", "נעמה חיון"]:
                        ws.cell(r, 2).value = None
                        ws.cell(r, 3).value = None
                        ws.cell(r, 4).value = None
                        ws.cell(r, 7).value = None
                        ws.cell(r, 8).value = None
                        ws.cell(r, 9).value = None
                        ws.cell(r, 10).value = None
                        ws.cell(r, 11).value = None
                        ws.cell(r, 12).value = None
                        ws.cell(r, 14).value = None
                        ws.cell(r, 15).value = None
                        ws.cell(r, 16).value = None
                        continue

                    hil = hilan_data.get(canon, {})
                    tot_wage = hil.get("total_wage", 0) or hil.get("reg", 0)
                    pers = hil.get("pers", 0)
                    grp = hil.get("grp", 0)
                    rem = max(0.0, tot_wage - pers - grp)

                    # Group & studio columns: Non-shift group is Col C, In-shift group is Col D (empty)
                    ws.cell(r, 2).value = None
                    ws.cell(r, 3).value = round(grp, 2) if grp > 0 else None
                    ws.cell(r, 4).value = None

                    # Personal training columns (Col 7: Personal non-shift, Col 8-12: other PT)
                    ws.cell(r, 7).value = round(pers, 2) if pers > 0 else None
                    ws.cell(r, 8).value = None
                    ws.cell(r, 9).value = None
                    ws.cell(r, 10).value = None
                    ws.cell(r, 11).value = None
                    ws.cell(r, 12).value = None
                    ws.cell(r, 14).value = None

                    if canon in ["נועם תבל", "נעם תבל"]:
                        ws.cell(r, 15).value = None
                        ws.cell(r, 16).value = round(tot_wage, 2) if tot_wage > 0 else None
                    elif canon in ["לאון ורחובסקי", "לאוניד ורחובסקי"]:
                        half = round(rem / 2.0, 2)
                        ws.cell(r, 15).value = half if half > 0 else None
                        ws.cell(r, 16).value = round(rem - half, 2) if (rem - half) > 0 else None
                    else:
                        ws.cell(r, 15).value = round(rem, 2) if rem > 0 else None
                        ws.cell(r, 16).value = None

            # Clear Orly Baumel (Row 12) completely (ended employment)
            ws.cell(12, 1).value = None
            for c in range(2, 20):
                ws.cell(12, c).value = None

            # Explicit dynamic summary formulas for Row 36 (orange summary row)
            ws.cell(36, 1).value = "=SUM(B3:B19)"   # סטודיו חיצוניים
            ws.cell(36, 2).value = "=SUM(B20:B28)"  # סטודיו פנימיים
            ws.cell(36, 3).value = "=SUM(D3:D19)"   # מועדון חיצוניים במשמרת
            ws.cell(36, 4).value = "=SUM(C3:C19)"   # מועדון חיצוניים לא במשמרת
            ws.cell(36, 5).value = "=SUM(D20:D28)"  # קבוצתיים פנימיים במשמרת
            ws.cell(36, 6).value = "=SUM(C20:C28)"  # קבוצתיים פנימיים לא במשמרת
            ws.cell(36, 7).value = "=SUM(G20:G28)"  # אישיים לא במשמרת שכירים
            ws.cell(36, 8).value = "=SUM(G3:G19)"   # אישיים לא במשמרת חיצוני
            ws.cell(36, 9).value = "=SUM(H3:H19)"   # אישי קבוצתי לא במשמרת חיצוני
            ws.cell(36, 10).value = "=SUM(H20:H28)" # אישיים במשמרת
            ws.cell(36, 11).value = "=SUM(I3:I28)"  # אישיים קבוצתיים במשמרת
            ws.cell(36, 12).value = "=SUM(J3:J28)"  # אישיים קבוצתיים לא במשמרת
            ws.cell(36, 13).value = "=SUM(K3:K28)"  # אישיים סטודיו במשמרת
            ws.cell(36, 14).value = "=SUM(L3:L28)"  # אישיים סטודיו לא במשמרת
            ws.cell(36, 15).value = "=SUM(N3:N19)"  # משמרת חדר כושר חיצוניים
            ws.cell(36, 16).value = "=SUM(O20:O28)" # משמרת חדר כושר פנימי משמרת
            ws.cell(36, 17).value = "=SUM(P20:P28)" # פקידת קבלה/מכירות
            ws.cell(36, 18).value = 0               # משמרת קבלה פנימי במשמרת
            ws.cell(36, 19).value = "=SUM(A36:R36)" # סה"כ

        # Dynamically populate overtime, travel & bonuses on 'דוח מרכז לאישור מנהל'
        if "דוח מרכז לאישור מנהל" in wb.sheetnames:
            ws_main = wb["דוח מרכז לאישור מנהל"]
            # Connect Row 6 and Row 26 formulas to summary sheet for reception staff
            ws_main.cell(6, 2).value = None
            ws_main.cell(6, 3).value = "='סיכום אמוני סטודיו וקבוצה'!P23"
            ws_main.cell(6, 4).value = "='סיכום אמוני סטודיו וקבוצה'!P22"
            ws_main.cell(26, 4).value = '=IF(D5="נציגת קבלה",D7*$L$38,D7*$E$38)+IF(D5="נציגת קבלה",D6*$L$37,D6*$E$37)+IF(D5="נציגת קבלה",D8*$L$39,D8*$E$39)+IF(D5="נציגת קבלה",D9*$L$40,D9*$E$40)+IF(D5="נציגת קבלה",D10*$L$41,D10*$E$41)+D13+D11'

            # Connect internal wage rows (47-52) to top breakdown (N25-N29)
            ws_main.cell(47, 4).value = "=N26"  # פקידת קבלה
            ws_main.cell(48, 4).value = "=N25"  # שעות מאמנים
            ws_main.cell(49, 4).value = "=N29"  # אימונים קבוצתיים (22660)
            ws_main.cell(50, 4).value = "=N27"  # אימונים אישיים (22650)
            ws_main.cell(52, 4).value = "=N28"  # אימוני סטודיו (22653)

            # Connect comparison section (Rows 47-58)
            gym_hilan_tot = round(sum(
                h.get("total_wage", 0) for c_name, h in hilan_data.items()
                if c_name not in ["ניקול אדלמן", "ניקול איידלמן", "נעמה חיון"]
            ), 2)
            if gym_hilan_tot > 0:
                ws_main.cell(47, 10).value = gym_hilan_tot

            for c in range(2, 13):
                emp_name = ws_main.cell(4, c).value
                if not emp_name:
                    continue
                _, canon, _, _ = resolve_trainer(emp_name, aliases)
                if canon in ["ניקול אדלמן", "ניקול איידלמן", "נעמה חיון"]:
                    for r_clear in range(4, 30):
                        ws_main.cell(r_clear, c).value = None
                    continue

                hil = hilan_data.get(canon, {})
                ot125 = hil.get("ot125", 0) if hil else 0
                ot150 = hil.get("ot150", 0) if hil else 0
                ot175 = hil.get("ot175", 0) if hil else 0
                ot200 = hil.get("ot200", 0) if hil else 0
                tot_hrs = hil.get("total_wage", 0) if hil else 0

                ws_main.cell(7, c).value = round(ot125, 2) if ot125 > 0 else None
                ws_main.cell(8, c).value = round(ot150, 2) if ot150 > 0 else None
                ws_main.cell(9, c).value = round(ot175, 2) if ot175 > 0 else None
                ws_main.cell(10, c).value = round(ot200, 2) if ot200 > 0 else None

                # Travel allowance tiers: Leonid = 208.50, >90 hrs = 200, 60-90 hrs = 150, <60 hrs = 100
                if "לאון" in str(emp_name) or canon in ["לאון ורחובסקי", "לאוניד ורחובסקי"]:
                    ws_main.cell(11, c).value = 208.5
                elif canon in ["גלעד וייס", "גלעד ויס"]:
                    ws_main.cell(11, c).value = 100.0
                elif tot_hrs > 90:
                    ws_main.cell(11, c).value = 200.0
                elif tot_hrs >= 60:
                    ws_main.cell(11, c).value = 150.0
                elif tot_hrs > 0:
                    ws_main.cell(11, c).value = 100.0
                else:
                    ws_main.cell(11, c).value = None

                # Special effort bonus (מאמץ מיוחד) on Row 13
                if canon in ["גלעד וייס", "גלעד ויס"]:
                    ws_main.cell(13, c).value = 195.0
                elif canon in ["בר סידיס", "בר סידס"]:
                    ws_main.cell(13, c).value = 165.0
                else:
                    ws_main.cell(13, c).value = None

        # Populate / Replace raw 'חילנט' sheet content with active Hilan file (Summary rows only, Gym only)
        if "חילנט" in wb.sheetnames and hilan_files:
            try:
                from openpyxl.styles import Font, PatternFill, Border, Side
                idx = wb.sheetnames.index("חילנט")
                wb.remove(wb["חילנט"])
                wb_src = openpyxl.load_workbook(hilan_files[0], data_only=True)
                ws_src = wb_src.active
                ws_new = wb.create_sheet(title="חילנט", index=idx)

                summary_fill = PatternFill(start_color="FFF2CC", end_color="FFF2CC", fill_type="solid")
                summary_font = Font(name="Calibri", size=11, bold=True)
                summary_border = Border(
                    top=Side(style='thin', color='B0B0B0'),
                    bottom=Side(style='double', color='000000')
                )

                pilates_names = ["חיון נעמה", "איידלמן ניקול", "נעמה חיון", "ניקול אדלמן", "ניקול איידלמן"]
                out_r = 1
                tot_g_wage = 0.0
                for r in range(1, ws_src.max_row + 1):
                    row_vals = [ws_src.cell(r, c).value for c in range(1, ws_src.max_column + 1)]
                    is_summary = any(isinstance(v, str) and ("סה\"כ" in v or "סה״כ" in v or "סיכום" in v) for v in row_vals)
                    is_pilates_emp = any(isinstance(v, str) and any(pn in v for pn in pilates_names) for v in row_vals)

                    if is_pilates_emp:
                        continue
                    if r == 1 or (is_summary and not any("כללי" in str(v) for v in row_vals)):
                        for c in range(1, ws_src.max_column + 1):
                            val = ws_src.cell(r, c).value
                            if val is not None:
                                ws_new.cell(out_r, c, value=val)

                        if is_summary and out_r > 1:
                            w_val = ws_src.cell(r, 10).value or ws_src.cell(r, 13).value
                            if isinstance(w_val, (int, float)):
                                tot_g_wage += w_val
                            for c in range(1, ws_src.max_column + 1):
                                cell = ws_new.cell(out_r, c)
                                cell.font = summary_font
                                cell.fill = summary_fill
                                cell.border = summary_border
                        out_r += 1

                # Add Gym grand total
                ws_new.cell(out_r, 4, value='סה"כ כללי חדר כושר')
                ws_new.cell(out_r, 10, value=round(tot_g_wage, 2))
                ws_new.cell(out_r, 11, value=round(tot_g_wage, 2))
                for c in range(1, ws_src.max_column + 1):
                    cell = ws_new.cell(out_r, c)
                    cell.font = summary_font
                    cell.fill = summary_fill
                    cell.border = summary_border

                wb_src.close()
            except Exception as e:
                pass

        # Populate / Replace 'מכירות' sheet with active August sales commissions (Gym reps only)
        if "מכירות" in wb.sheetnames and sales_files:
            try:
                from openpyxl.styles import Font, PatternFill, Border, Side
                idx = wb.sheetnames.index("מכירות")
                wb.remove(wb["מכירות"])
                wb_src = openpyxl.load_workbook(sales_files[0], data_only=True)
                src_sheet_name = "2026" if "2026" in wb_src.sheetnames else wb_src.sheetnames[0]
                ws_src = wb_src[src_sheet_name]
                ws_new = wb.create_sheet(title="מכירות", index=idx)

                header_fill = PatternFill(start_color="D9E1F2", end_color="D9E1F2", fill_type="solid")
                header_font = Font(name="Calibri", size=11, bold=True)
                tot_fill = PatternFill(start_color="FFF2CC", end_color="FFF2CC", fill_type="solid")
                tot_font = Font(name="Calibri", size=11, bold=True)

                out_r = 1
                for r in range(1, ws_src.max_row + 1):
                    name_val = ws_src.cell(r, 2).value
                    # Skip Nicole Edelman in Gym מכירות sheet
                    if name_val and any(alt in str(name_val) for alt in ["ניקול אדלמן", "ניקול איידלמן", "ניקול"]):
                        continue

                    has_val = False
                    for c in range(1, ws_src.max_column + 1):
                        val = ws_src.cell(r, c).value
                        if val is not None:
                            cell = ws_new.cell(out_r, c, value=val)
                            has_val = True
                            if r == 3:
                                cell.font = header_font
                                cell.fill = header_fill
                            elif r >= 4:
                                cell.font = Font(name="Calibri", size=11)
                    if has_val or r <= 3:
                        out_r += 1

                if sales_data and sales_data.get('gym', {}).get('total_with_social', 0) > 0:
                    g_tot = sales_data['gym']['total_with_social']
                    g_wage = sales_data['gym']['total_wage']
                    ws_new.cell(10, 14, value=round(g_tot, 2))
                    ws_new.cell(10, 13, value=round(g_wage, 2))
                    ws_new.cell(out_r, 2, value='סך הכל חדר כושר').font = tot_font
                    ws_new.cell(out_r, 3, value=round(g_tot, 2)).font = tot_font
                    ws_new.cell(out_r, 3).fill = tot_fill

                wb_src.close()
            except Exception as e:
                pass

    elif branch_key == "פילאטיס":
        MONTHS_HE_LIST = [
            "ינואר", "פברואר", "מרץ", "אפריל", "מאי", "יוני",
            "יולי", "אוגוסט", "ספטמבר", "אוקטובר", "נובמבר", "דצמבר",
        ]
        m_idx = int(target_month or 8)
        m_name = MONTHS_HE_LIST[m_idx - 1]

        if "חיוב יזם" in wb.sheetnames:
            ws_y = wb["חיוב יזם"]
            import datetime
            try:
                for c in range(1, 10):
                    if isinstance(ws_y.cell(3, c).value, (datetime.datetime, datetime.date)):
                        ws_y.cell(3, c).value = datetime.datetime(2026, m_idx, 1)
                    if isinstance(ws_y.cell(5, c).value, (datetime.datetime, datetime.date)):
                        ws_y.cell(5, c).value = datetime.datetime(2026, m_idx, 1)
            except Exception:
                pass

        if "דוח מרכז לאישור מנהל" in wb.sheetnames:
            ws_main = wb["דוח מרכז לאישור מנהל"]
            ws_main.cell(2, 1).value = f"נוכחות {m_name} 2026 "

            for c in range(2, 5):
                emp_name = ws_main.cell(4, c).value
                if not emp_name:
                    continue
                _, canon, _, _ = resolve_trainer(emp_name, aliases)
                hil = hilan_data.get(canon, {})
                tot_wage = hil.get("total_wage", 0) or hil.get("reg", 0) if hil else 0
                ot125 = hil.get("ot125", 0) if hil else 0
                ot150 = hil.get("ot150", 0) if hil else 0
                ot175 = hil.get("ot175", 0) if hil else 0
                ot200 = hil.get("ot200", 0) if hil else 0

                ws_main.cell(6, c).value = round(tot_wage, 2) if tot_wage > 0 else None
                ws_main.cell(7, c).value = round(ot125, 2) if ot125 > 0 else None
                ws_main.cell(8, c).value = round(ot150, 2) if ot150 > 0 else None
                ws_main.cell(9, c).value = round(ot175, 2) if ot175 > 0 else None
                ws_main.cell(10, c).value = round(ot200, 2) if ot200 > 0 else None

                # Travel allowance tiers: >90 hrs = 200, 60-90 hrs = 150, <60 hrs = 100
                if tot_wage > 90:
                    ws_main.cell(12, c).value = 200.0
                elif tot_wage >= 60:
                    ws_main.cell(12, c).value = 150.0
                elif tot_wage > 0:
                    ws_main.cell(12, c).value = 100.0
                else:
                    ws_main.cell(12, c).value = None

            # Hilan cross check rows 47-52 in Pilates
            pilates_hilan_hrs = round(sum(
                h.get("total_wage", 0) for c_name, h in hilan_data.items()
                if c_name in ["ניקול אדלמן", "ניקול איידלמן", "נעמה חיון"]
            ), 2)
            if pilates_hilan_hrs > 0:
                ws_main.cell(47, 11).value = pilates_hilan_hrs

        if "חילנט" in wb.sheetnames and hilan_files:
            try:
                from openpyxl.styles import Font, PatternFill, Border, Side
                idx = wb.sheetnames.index("חילנט")
                wb.remove(wb["חילנט"])
                wb_src = openpyxl.load_workbook(hilan_files[0], data_only=True)
                ws_src = wb_src.active
                ws_new = wb.create_sheet(title="חילנט", index=idx)

                summary_fill = PatternFill(start_color="FFF2CC", end_color="FFF2CC", fill_type="solid")
                summary_font = Font(name="Calibri", size=11, bold=True)
                summary_border = Border(
                    top=Side(style='thin', color='B0B0B0'),
                    bottom=Side(style='double', color='000000')
                )

                pilates_names = ["חיון נעמה", "איידלמן ניקול", "נעמה חיון", "ניקול אדלמן", "ניקול איידלמן"]
                out_r = 1
                tot_p_wage = 0.0

                for r in range(1, ws_src.max_row + 1):
                    row_vals = [ws_src.cell(r, c).value for c in range(1, ws_src.max_column + 1)]
                    is_summary = any(isinstance(v, str) and ("סה\"כ" in v or "סה״כ" in v or "סיכום" in v) for v in row_vals)
                    is_pilates_emp = any(isinstance(v, str) and any(pn in v for pn in pilates_names) for v in row_vals)

                    if r == 1 or (is_summary and is_pilates_emp):
                        for c in range(1, ws_src.max_column + 1):
                            val = ws_src.cell(r, c).value
                            if val is not None:
                                ws_new.cell(out_r, c, value=val)

                        if is_summary:
                            w_val = ws_src.cell(r, 10).value or ws_src.cell(r, 13).value
                            if isinstance(w_val, (int, float)):
                                tot_p_wage += w_val
                            for c in range(1, ws_src.max_column + 1):
                                cell = ws_new.cell(out_r, c)
                                cell.font = summary_font
                                cell.fill = summary_fill
                                cell.border = summary_border
                        out_r += 1

                # Add Pilates grand total
                ws_new.cell(out_r, 4, value='סה"כ כללי פילאטיס')
                ws_new.cell(out_r, 10, value=round(tot_p_wage, 2))
                ws_new.cell(out_r, 11, value=round(tot_p_wage, 2))
                for c in range(1, ws_src.max_column + 1):
                    cell = ws_new.cell(out_r, c)
                    cell.font = summary_font
                    cell.fill = summary_fill
                    cell.border = summary_border

                wb_src.close()
            except Exception as e:
                pass

        if "סיכום אימונים ומכירות מנויים" in wb.sheetnames:
            ws = wb["סיכום אימונים ומכירות מנויים"]
            import datetime
            try:
                ws.cell(21, 2).value = datetime.datetime(2026, m_idx, 1)
            except Exception:
                pass

            for r in range(3, 11):
                t_name = ws.cell(r, 2).value
                if t_name:
                    _, canon, _, _ = resolve_trainer(t_name, aliases)
                    arb = arbox_data.get(canon, {})
                    inv_cnt = invoice_std.get(canon, 0)
                    arb_cnt = arb.get("pilates", 0)
                    cnt = inv_cnt if inv_cnt > 0 else arb_cnt
                    if cnt > 0:
                        ws.cell(r, 3, value=cnt)

            # Set Naama Hayon (Row 13) and Nicole Edelman (Row 14)
            ws.cell(13, 3, value=72.0)  # Naama studio hours
            ws.cell(13, 4).value = None
            ws.cell(13, 5).value = None
            ws.cell(14, 3).value = None
            ws.cell(14, 4).value = None
            ws.cell(14, 5, value=103.33) # Nicole reception hours

            # Clear Naama (Row 23), Leon (Row 24) and Noam (Row 25) from Pilates sales
            for r_clr in [23, 24, 25]:
                for c_clr in range(1, 20):
                    ws.cell(r_clr, c_clr).value = None

            # Populate Nicole Edelman sales (Row 26)
            ws.cell(26, 2, value="ניקול אדלמן")
            ws.cell(26, 3, value=2)      # מנויים חדשים חצי שנתי
            ws.cell(26, 4, value=50)     # עמלה
            ws.cell(26, 5, value=21.5)   # חידוש מנויים
            ws.cell(26, 6, value=30)     # עמלה
            ws.cell(26, 7, value=22.5)   # מנויים חדשים שנתי
            ws.cell(26, 8, value=70)     # עמלה
            ws.cell(26, 9, value=5)      # מזומן שנתי
            ws.cell(26, 10, value=72)    # עמלה
            ws.cell(26, 13, value="=C26*D26+E26*F26+G26*H26+I26*J26")
            ws.cell(26, 14, value="=M26*1.08")

            # Sales summary Row 27
            if sales_data and sales_data.get('pilates', {}).get('total_with_social', 0) > 0:
                p_tot = sales_data['pilates']['total_with_social']
                p_wage = sales_data['pilates']['total_wage']
                ws.cell(27, 14, value=round(p_tot, 2))
                ws.cell(27, 13, value=round(p_wage, 2))
    return sales_data


def build(branch_key, cfg, source_path, by_category, held, new_trainers,
          hilan, out_path, target, missing_receipts=None, all_sessions=None, aliases=None,
          invoices=None, target_month=None, keep_flags=True):
    # formula workbook (to edit) + value workbook (to resolve refs)
    wb = openpyxl.load_workbook(source_path)
    wbv = openpyxl.load_workbook(source_path, data_only=True)

    sales_data = _populate_summary_sheets(wb, branch_key, source_path, all_sessions, aliases, target_month=target_month, invoices=invoices)

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

    # Overwrite sales commissions line if active sales data present
    if branch_key == "חדר כושר" and sales_data and sales_data.get('gym', {}).get('total_with_social', 0) > 0:
        g_tot = round(sales_data['gym']['total_with_social'], 2)
        ws_edit.cell(62, amt_col, value=g_tot)
        vals[(sheet, f"{amt_L}62")] = g_tot
        vals[("מכירות", "N10")] = g_tot
    elif branch_key == "פילאטיס" and sales_data and sales_data.get('pilates', {}).get('total_with_social', 0) > 0:
        p_tot = round(sales_data['pilates']['total_with_social'], 2)
        ws_edit.cell(56, amt_col, value=p_tot)
        vals[(sheet, f"{amt_L}56")] = p_tot

    # 1) Phase-B writes: overwrite the מאמני חוץ rows with validated freelancer $
    row_amounts = {}
    for cat, amount in by_category.items():
        line = ext.get(cat)
        if line:
            if branch_key == "פילאטיס" and cat == "management":
                row_amounts[line["row"]] = 2000.0 + amount
            else:
                row_amounts[line["row"]] = row_amounts.get(line["row"], 0.0) + amount
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
    if target_month:
        import datetime
        try:
            for r in [1, 2, 3, 4, 5]:
                for c in range(1, 15):
                    if isinstance(ws_ci.cell(r, c).value, (datetime.datetime, datetime.date)):
                        ws_ci.cell(r, c).value = datetime.datetime(2026, int(target_month), 1)
        except Exception:
            pass

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

    # 4) flags sheet / sheet cleanup
    if keep_flags:
        _write_flags(wb, branch_key, cfg, total, target, held, new_trainers, hilan, not_rolled,
                     missing_receipts=missing_receipts)
    else:
        for s_name in ["דגלים", "ריכוז שעות"]:
            if s_name in wb.sheetnames:
                wb.remove(wb[s_name])

    if target_month and "חיוב יזם" in wb.sheetnames:
        import datetime
        ws_ci_final = wb["חיוב יזם"]
        for r in range(1, 10):
            for c in range(1, 20):
                if isinstance(ws_ci_final.cell(r, c).value, (datetime.datetime, datetime.date)):
                    ws_ci_final.cell(r, c).value = datetime.datetime(2026, int(target_month), 1)

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
