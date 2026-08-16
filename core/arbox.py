"""
Arbox sessions (דו"ח שיעורים) reader. Loads held sessions and lets Job 1
pull a trainer's sessions for a given SERVICE month (not doc date).

Column meaning resolved by HEADER NAME. The workbook ships several snapshot
tabs (14.6, 23.6, 7.7, 13.7); we default to the latest full tab and de-dupe
by (date,start,trainer,category) so overlapping snapshots don't double-count.
"""
import openpyxl
from common import normalize_name, month_key, resolve_trainer

H_DATE = "תאריך"
H_START = "שעת התחלה"
H_STATUS = "סטטוס"
H_TRAINER = "מאמנים"
H_SERVICE = "סוג שירות"
H_CLASS = "שיעור"
H_CATEGORY = "קטגוריה"
H_CHECKIN = "צ׳ק אין"
H_LATE_CANCEL = "ביטולים מאוחרים"
H_DURATION = "משך השיעור"
H_BRANCH = "סניף"

STATUS_HELD = "מתקיים"

# snapshot tabs only (skip סיכום / weekly-system / peri-fit sheets)
def _is_data_tab(name):
    n = name.strip()
    if n.startswith("סיכום"): return False
    if "מסוכמת" in n or "פרי פיט" in n: return False
    # tabs are like 14.6 / 7.7 / 13.7
    return any(ch.isdigit() for ch in n) and "." in n


def _num(x):
    try:
        return float(x)
    except (ValueError, TypeError):
        return 0.0


def load_sessions(path, aliases_cfg, prefer_tabs=None):
    """
    -> list of session dicts (held only), de-duplicated across snapshot tabs or CSV.
    Each: {date, start, trainer_raw, trainer_id, canonical, category, service,
           class_name, checkins, late_cancel, duration, branch, month, tab}
    """
    seen = {}

    if str(path).lower().endswith(".csv"):
        import csv
        encoding = "utf-8-sig"
        try:
            with open(path, encoding=encoding) as f:
                rows = list(csv.reader(f))
        except UnicodeDecodeError:
            with open(path, encoding="cp1255") as f:
                rows = list(csv.reader(f))

        tab_data = [("CSV", rows)]
    else:
        wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
        tabs = prefer_tabs or [s for s in wb.sheetnames if _is_data_tab(s)]
        tab_data = []
        for tab in tabs:
            ws = wb[tab]
            tab_data.append((tab, list(ws.iter_rows(values_only=True))))
        wb.close()

    for tab, rows in tab_data:
        if not rows:
            continue
        header = [str(c).strip() if c is not None else "" for c in rows[0]]
        def ci(name):
            return header.index(name) if name in header else None
        c = {k: ci(v) for k, v in {
            "date": H_DATE, "start": H_START, "status": H_STATUS,
            "trainer": H_TRAINER, "service": H_SERVICE, "class": H_CLASS,
            "category": H_CATEGORY, "checkin": H_CHECKIN,
            "late": H_LATE_CANCEL, "dur": H_DURATION, "branch": H_BRANCH,
        }.items()}
        def get(r, key):
            i = c[key]
            return r[i] if (i is not None and len(r) > i) else None
        for r in rows[1:]:
            status = str(get(r, "status") or "").strip()
            if status != STATUS_HELD:
                continue
            traw = get(r, "trainer")
            tid, canon, score, method = resolve_trainer(traw, aliases_cfg)
            mk = month_key(get(r, "date"))
            key = (str(get(r, "date")), str(get(r, "start")),
                   normalize_name(traw), str(get(r, "category")))
            if key in seen:
                continue
            seen[key] = {
                "date": get(r, "date"), "start": get(r, "start"),
                "trainer_raw": traw, "trainer_id": tid, "canonical": canon,
                "match_method": method, "match_score": score,
                "category": get(r, "category"), "service": get(r, "service"),
                "class_name": get(r, "class"),
                "checkins": _num(get(r, "checkin")),
                "late_cancel": _num(get(r, "late")),
                "duration": _num(get(r, "dur")),
                "branch": get(r, "branch"), "month": mk, "tab": tab,
            }
    return list(seen.values())


def sessions_for(sessions, trainer_id, month=None):
    """Filter held sessions for a trainer (+ optional service month)."""
    out = [s for s in sessions if s["trainer_id"] == trainer_id]
    if month:
        out = [s for s in out if s["month"] == month]
    return out


def unmapped_names(sessions):
    """Distinct raw names that failed to resolve -> for UNMAPPED_NAME audits."""
    u = {}
    for s in sessions:
        if s["trainer_id"] is None and s["match_method"] not in ("IGNORED", "EMPTY"):
            u.setdefault(s["trainer_raw"], 0)
            u[s["trainer_raw"]] += 1
    return u
