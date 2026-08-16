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

def resolve_inputs(input_dir):
    def _score_path(p):


        score = 0
        p_norm = _norm(p)
        if "יולי" in p_norm or "07" in p_norm or "07_2026" in p_norm:
            score += 10
        if "קבלות" in p_norm:
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
        # 4) arbox (דו"ח שיעורים) — works with .xlsx or .csv
        if "שיעור" in base or _has_sheet_signature(p, need_headers=["מאמנים", "סטטוס", "שעת התחלה"]):
            if not roles["arbox"]:
                roles["arbox"] = p
            continue
        # 5) spa/hilanet project report
        if "פרויקטים" in base or "ספא" in base or "חילנט" in base:
            if not roles["hilanet"]:
                roles["hilanet"] = p
            continue
        roles["notes"].append(f"unrecognized file ignored: {base}")


    # Fallback: if no dedicated ledger file is supplied, budget workbook acts as ledger source
    if not roles["ledger"] and roles["budget"]:
        roles["ledger"] = roles["budget"]

    return roles

def preflight(input_dir, need=("budget", "arbox")):
    """Human-readable readiness check. Returns (ok, report_lines, roles)."""
    roles = resolve_inputs(input_dir)
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
    for n in roles["notes"]:
        lines.append(f"  … {n}")
    return ok, lines, roles

