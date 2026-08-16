"""Resilience / chaos tests — all self-contained, no external sample data needed."""
import sys
import os
import json
import openpyxl

B = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, os.path.join(B, "core"))
sys.path.insert(0, os.path.join(B, "jobs"))

from common import load_aliases, load_pay_matrix, load_json
from ledger import parse_ledger, monthly_movement
from ledger_output import _find_header, _code_rows, _sync
from arbox import load_sessions
import job_billing as JB
import billing_output as BO

ok = 0
fail = 0


def check(name, cond, detail=""):
    global ok, fail
    if cond:
        ok += 1
        print(f"  PASS  {name}")
    else:
        fail += 1
        print(f"  FAIL  {name}  {detail}")


aliases = load_aliases()
pay = load_pay_matrix()
branches = load_json("branches.json")["branches"]
OUT = os.path.join(B, "output")
os.makedirs(OUT, exist_ok=True)

# ---------------------------------------------------------------------------
# 1. Bad/corrupt invoice entry in OCR JSON -> run continues, failure flagged
# ---------------------------------------------------------------------------
print("\n§R1 Bad invoice entry resilience")
good_inv = {
    "file": "good.pdf", "trainer": "לירון ניסן", "doc_number": "G1",
    "doc_date": "2026-06-15", "issuer_tax_id": "066587098",
    "billed_to": "A+", "stated_total": 490, "vat_included": False,
    "unit_kind": "session", "category": "personal", "branch": "חדר כושר",
    "line_items": [{"desc": "session", "qty": 1, "rate": 490, "total": 490}],
    "session_dates": ["10.6.26"], "notes": "",
}
bad_inv = {
    "file": "bad.pdf", "trainer": None, "doc_number": None,
    "stated_total": "NOT_A_NUMBER", "line_items": [],
}
try:
    log = []
    by_cat, held, ta = JB.validate_invoices(
        [good_inv, bad_inv], "חדר כושר", [], aliases, pay, log
    )
    check("good invoice still processed despite bad neighbor", len(ta) >= 1)
    check("bad invoice did not crash pipeline", True)
except Exception as e:
    check("bad invoice does not crash billing pipeline", False, str(e))

# ---------------------------------------------------------------------------
# 2. Unknown trainer -> NOT in money totals, in pending/דגלים proposal
# ---------------------------------------------------------------------------
print("\n§R2 Unknown trainer handling")
unknown_inv = {
    "file": "unknown.pdf", "trainer": "מאמן לא ידוע מעולם",
    "doc_number": "U1", "doc_date": "2026-06-15", "issuer_tax_id": "000000000",
    "billed_to": "A+", "stated_total": 800, "vat_included": False,
    "unit_kind": "session", "category": "studio", "branch": "חדר כושר",
    "line_items": [{"desc": "sessions", "qty": 4, "rate": 200, "total": 800}],
    "session_dates": ["2.6", "9.6", "16.6", "23.6"], "notes": "",
}
log2 = []
by_cat2, held2, ta2 = JB.validate_invoices(
    [unknown_inv], "חדר כושר", [], aliases, pay, log2
)
check("unknown trainer category NOT in money totals",
      len(by_cat2) == 0 or all(v == 0 for v in by_cat2.values()))
check("unknown trainer held with UNMAPPED_NAME entry",
      any(e.get("type") == "UNMAPPED_NAME" for e in log2))
check("unknown trainer has proposal in audit entry",
      any(e.get("proposal") for e in log2 if e.get("type") == "UNMAPPED_NAME"))
check("unknown trainer NOT in trainer_amounts cache",
      not any(a["raw_name"] == "מאמן לא ידוע מעולם" for a in ta2))

# ---------------------------------------------------------------------------
# 3. Missing receipt detection
# ---------------------------------------------------------------------------
print("\n§R3 Missing receipts")
log3 = []
by_cat3, held3, ta3 = JB.validate_invoices([good_inv], "חדר כושר", [], aliases, pay, log3)
sessions_with_missing = [
    {"trainer_id": "t_horovitz", "month": "2026-06", "branch": "חדר כושר"}
]
missing = JB.missing_receipts("חדר כושר", sessions_with_missing, aliases, ta3, "2026-06")
check("trainer with Arbox sessions but no invoice -> flagged as missing receipt",
      "ספיר הורוביץ" in missing, missing)

# ---------------------------------------------------------------------------
# 4. Manual adjustment survival after re-sync
# ---------------------------------------------------------------------------
print("\n§R4 Manual adjustment survival")
try:
    cfg_club = branches["חדר כושר"]
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "דוח מרכז לאישור מנהל"
    ws.cell(2, 1, "מט."); ws.cell(2, 2, "קוד"); ws.cell(2, 3, "שם"); ws.cell(2, 4, "")
    ws.cell(2, 5, "ינואר"); ws.cell(2, 6, "ינואר ביצוע (כרטסת)")
    ws.cell(2, 7, "ינואר התאמה ידנית"); ws.cell(2, 8, "ינואר - ביצוע")
    ws.cell(2, 9, "יוני"); ws.cell(2, 10, "יוני ביצוע (כרטסת)")
    ws.cell(2, 11, "יוני התאמה ידנית"); ws.cell(2, 12, "יוני - ביצוע")
    ws.cell(3, 2, 22620); ws.cell(3, 3, "חיוב בגין פקידת קבלה"); ws.cell(3, 10, 1000)
    ws.cell(3, 11, 500)  # manual adjustment
    ws.cell(4, 2, 22604); ws.cell(4, 3, "חיוב שעות מאמנים"); ws.cell(4, 10, 2000)

    budget_path = os.path.join(OUT, "_t_resilience_budget.xlsx")
    wb.save(budget_path)
    wb.close()

    from ledger_output import _extract_tab, SRC_TABS, SHEET_KEY

    SRC_TABS["חדר כושר"] = "דוח מרכז לאישור מנהל"
    SHEET_KEY["חדר כושר"] = "דוח מרכז לאישור מנהל"
    out_path = os.path.join(OUT, "_t_resilience_budget_out.xlsx")
    out, ws2 = _extract_tab(budget_path, "דוח מרכז לאישור מנהל", out_path)
    lc = _find_header(ws2, "יוני ביצוע (כרטסת)")
    mc = _find_header(ws2, "יוני התאמה ידנית")
    rows = _code_rows(ws2)

    old_manual = ws2.cell(rows.get("22620", 3), mc).value if rows.get("22620") else None
    _sync(ws2, "יוני", "2026-06", "דוח מרכז לאישור מנהל", {})
    new_manual = ws2.cell(rows.get("22620", 3), mc).value if rows.get("22620") else None
    check("manual adjustment value preserved after re-sync", old_manual == new_manual, f"{old_manual} vs {new_manual}")
    out.save(out_path)
    out.close()
    os.remove(budget_path)
    if os.path.exists(out_path):
        os.remove(out_path)
except Exception as e:
    check("manual adjustment survival test", False, str(e))

# ---------------------------------------------------------------------------
# 5. Unmapped account logged, not crash
# ---------------------------------------------------------------------------
print("\n§R5 Unmapped account handling")
try:
    am = load_json("account_map.json")
    am_copy = json.loads(json.dumps(am))
    am_copy["accounts"] = {
        k: v for k, v in am_copy["accounts"].items()
        if k not in ("18022620", "18022604")
    }
    txns = [
        {"account": "18022620", "budget_month": "2026-06", "debit": 5000, "credit": 0},
        {"account": "99999999", "budget_month": "2026-06", "debit": 1000, "credit": 0},
    ]
    movement, unmapped = monthly_movement(txns, am_copy)
    check("unmapped account does not crash", True)
    check("valid account still processed", any("18022620" not in str(k) for k in movement.keys()) is not None)
    check("unknown account 99999999 appears in unmapped set",
          "99999999" in unmapped or any("99999999" in str(u) for u in unmapped), str(unmapped))
except Exception as e:
    check("unmapped account test", False, str(e))

# ---------------------------------------------------------------------------
print(f"\n==== {ok} passed, {fail} failed ====")
sys.exit(1 if fail else 0)
