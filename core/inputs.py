"""
Noise-tolerant input reader. The manager drops files into input/ (loosely named,
possibly with extra unrelated files) and this module figures out which file
plays which role — by filename hints first, then by inspecting sheet contents.

Roles resolved:
  ledger            כרטסת            (has a מט. header + חובה/זכות columns)
  budget            תקציב מול ביצוע  (tabs מועדון + פילאטיס)
  arbox             דו"ח שיעורים     (snapshot tabs, סטטוס/מאמנים columns)
  approval[branch]  דוח מרכז ...      (tab 'דוח מרכז לאישור מנהל'), split by branch
  invoices_dir      folder of PDFs   (or an invoices_ocr.json)

Nothing is matched by exact filename; a renamed file still resolves as long as
its content signature is intact. Unrecognized files are ignored (with a note).
"""
import os, glob, unicodedata

def _norm(s):
    return unicodedata.normalize("NFKC", str(s or "")).replace("״", '"').replace("׳", "'")

def _has_sheet_signature(path, need_tabs=None, need_headers=None):
    """Cheap content probe: returns True if any tab name / header cell matches."""
    try:
        import openpyxl
        wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    except Exception:
        return False
    try:
        names = [_norm(n) for n in wb.sheetnames]
        if need_tabs and any(any(t in n for t in need_tabs) for n in names):
            return True
        if need_headers:
            for n in wb.sheetnames[:6]:
                ws = wb[n]
                for i, row in enumerate(ws.iter_rows(values_only=True)):
                    if i > 8:
                        break
                    cells = " ".join(_norm(c) for c in row if c is not None)
                    if any(h in cells for h in need_headers):
                        return True
        return False
    finally:
        wb.close()

def _branch_of(path):
    n = _norm(os.path.basename(path))
    if "פילאטיס" in n or "פילטיס" in n:
        return "פילאטיס"
    if "חדר כושר" in n or "מועדון" in n or "כושר" in n:
        return "חדר כושר"
    return None

# Dynamic month patterns supporting Hebrew month names, digits, and file naming conventions
MONTH_PATTERNS = {
    1: ["ינואר", "01.", "01_", "01/", "1.26", "01.26", "01_2026", "1_2026", "jan"],
    2: ["פברואר", "02.", "02_", "02/", "2.26", "02.26", "02_2026", "2_2026", "feb"],
    3: ["מרץ", "03.", "03_", "03/", "3.26", "03.26", "03_2026", "3_2026", "mar"],
    4: ["אפריל", "04.", "04_", "04/", "4.26", "04.26", "04_2026", "4_2026", "apr"],
    5: ["מאי", "05.", "05_", "05/", "5.26", "05.26", "05_2026", "5_2026", "may"],
    6: ["יוני", "06.", "06_", "06/", "6.26", "06.26", "06_2026", "6_2026", "jun"],
    7: ["יולי", "07.", "07_", "07/", "7.26", "07.26", "07_2026", "7_2026", "jul"],
    8: ["אוגוסט", "08.", "08_", "08/", "8.26", "08.26", "08_2026", "8_2026", "aug"],
    9: ["ספטמבר", "09.", "09_", "09/", "9.26", "09.26", "09_2026", "9_2026", "sep"],
    10: ["אוקטובר", "10.", "10_", "10/", "10.26", "10_2026", "oct"],
    11: ["נובמבר", "11.", "11_", "11/", "11.26", "11_2026", "nov"],
    12: ["דצמבר", "12.", "12_", "12/", "12.26", "12_2026", "dec"],
}

def resolve_inputs(input_dir, target_month=None):
    def _score_path(p):
        score = 0
        p_norm = _norm(p).lower()
        if target_month and target_month in MONTH_PATTERNS:
            target_kw = MONTH_PATTERNS[target_month]
            if any(k in p_norm for k in target_kw):
                score += 20
        if "קבלות" in p_norm or "invoices" in p_norm:
            score += 5
        return score

    xlsx = [p for p in glob.glob(os.path.join(input_dir, "**", "*.xls*"), recursive=True)]
    csvs = [p for p in glob.glob(os.path.join(input_dir, "**", "*.csv"), recursive=True)]
    all_sheet_files = xlsx + csvs
    all_sheet_files = sorted(all_sheet_files, key=_score_path, reverse=True)


    roles = {"ledger": None, "budget": None, "arbox": None, "hilanet": None,
             "approval": {}, "invoices_dir": None, "invoices_ocr": None,
             "notes": []}


    all_pdf_dirs = [d.rstrip(os.sep) for d in glob.glob(os.path.join(input_dir, "**", ""), recursive=True)
                    if glob.glob(os.path.join(d, "*.pdf"))]
    if all_pdf_dirs:
        all_pdf_dirs.sort(key=_score_path, reverse=True)
        roles["invoices_dir"] = all_pdf_dirs[0]

    for j in glob.glob(os.path.join(input_dir, "**", "*.json"), recursive=True):
        if "invoice" in _norm(os.path.basename(j)).lower():
            roles["invoices_ocr"] = j

    for p in all_sheet_files:
        base = _norm(os.path.basename(p))
        # 1) approval report (branch-specific) — strongest signal: the tab name
        if p.endswith((".xlsx", ".xls")) and ("דוח מרכז" in base or _has_sheet_signature(p, need_tabs=["דוח מרכז לאישור מנהל"])):
            br = _branch_of(p)
            if br:
                if br not in roles["approval"]:
                    roles["approval"][br] = p
            else:
                roles["notes"].append(f"approval report with unknown branch: {base}")
            continue
        # 2) budget (תקציב מול ביצוע) — two branch tabs
        if p.endswith((".xlsx", ".xls")) and ("תקציב" in base or _has_sheet_signature(p, need_tabs=["תקציב מול ביצוע"])):
            if not roles["budget"]:
                roles["budget"] = p
            continue
        # 3) ledger (כרטסת) — מט. header + חובה/זכות
        if p.endswith((".xlsx", ".xls")) and ("כרטסת" in base or _has_sheet_signature(p, need_headers=["חובה", "זכות", "מאזן"])):
            if not roles["ledger"]:
                roles["ledger"] = p
            continue
        # 4) sales report / commissions (ריכוז עמלות / מכירות)
        if ("עמלות" in base or "מכירות" in base or "sales" in base.lower()) and not ("דוח מרכז" in base or "תקציב" in base):
            if not roles.get("sales"):
                roles["sales"] = p
            continue
        # 5) arbox (דו"ח שיעורים) — works with .xlsx or .csv (has lesson/status/date info)
        if ("שיעור" in base or "שיעורים" in base or _has_sheet_signature(p, need_headers=["סטטוס", "שעת התחלה"])) and not ("עמלות" in base or "דוח מרכז" in base):
            if not roles["arbox"]:
                roles["arbox"] = p
            continue
        # 6) spa/hilanet project report
        if "פרויקטים" in base or "ספא" in base or "חילנט" in base or "שעות" in base:
            if not roles["hilanet"]:
                roles["hilanet"] = p
            continue
        roles["notes"].append(f"unrecognized file ignored: {base}")

    # Template fallback: if approval sheet for a branch is not in input/, fallback to master templates in files/
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    files_dir = os.path.join(project_root, "files")
    for br in ("חדר כושר", "פילאטיס"):
        if br not in roles["approval"] and os.path.exists(files_dir):
            matches = [
                os.path.join(files_dir, f) for f in os.listdir(files_dir)
                if f.endswith(".xlsx") and "דוח_מרכז" in f and _branch_of(f) == br
            ]
            if matches:
                matches.sort(reverse=True)
                roles["approval"][br] = matches[0]
                roles["notes"].append(f"using master template for {br}: {os.path.basename(matches[0])}")

    # Fallback: if no dedicated ledger file is supplied, budget workbook acts as ledger source
    if not roles["ledger"] and roles["budget"]:
        roles["ledger"] = roles["budget"]

    return roles

def preflight(input_dir, need=("budget", "arbox"), target_month=None):
    """Human-readable readiness check. Returns (ok, report_lines, roles)."""
    roles = resolve_inputs(input_dir, target_month=target_month)
    lines, ok = [], True
    label = {"ledger": "כרטסת (ledger/תקציב)", "budget": "תקציב מול ביצוע (budget)",
             "arbox": 'דו"ח שיעורים (Arbox)'}
    for r in need:
        if roles.get(r):
            lines.append(f"  ✓ {label.get(r, r):28} {os.path.basename(roles[r])}")
        else:
            ok = False
            lines.append(f"  ✗ {label.get(r, r):28} MISSING")
    for br in ("פילאטיס", "חדר כושר"):
        p = roles["approval"].get(br)
        mark = "✓" if p else "·"
        lines.append(f"  {mark} דוח מרכז {br:10} {os.path.basename(p) if p else '(none — salaried-only branch or skip)'}")
    inv = roles["invoices_dir"] or roles["invoices_ocr"]
    lines.append(f"  {'✓' if inv else '·'} invoices{'':20} {os.path.basename(inv) if inv else '(none)'}")
    if roles.get("sales"):
        lines.append(f"  ✓ דוח מכירות{'':17} {os.path.basename(roles['sales'])}")
    for n in roles["notes"]:
        lines.append(f"  … {n}")
    return ok, lines, roles

