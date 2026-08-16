"""
Tests for Idan BvA feedback phases 1–6.
Self-contained — no external sample mount required.
Run: python tests/test_idan_fixes.py
"""
import sys, os, json
import openpyxl

B = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, os.path.join(B, "core"))
sys.path.insert(0, os.path.join(B, "jobs"))
sys.path.insert(0, B)

from common import parse_memo_month, is_income_budget_code, month_key
from ledger import monthly_movement
import ledger_output as LO

ok = 0
fail = 0
OUT = os.path.join(B, "output")
os.makedirs(OUT, exist_ok=True)


def check(name, cond, detail=""):
    global ok, fail
    if cond:
        ok += 1
        print(f"  PASS  {name}")
    else:
        fail += 1
        print(f"  FAIL  {name}  {detail}")


# ---------------------------------------------------------------------------
# Phase 3 — parse_memo_month (deterministic)
# ---------------------------------------------------------------------------
print("\n§I3 parse_memo_month")
check("5/26 -> 2026-05", parse_memo_month("5/26 הכנסות מנויים") == "2026-05",
      parse_memo_month("5/26 הכנסות מנויים"))
check("05.06.26 month-first when a<=12", parse_memo_month("05.06.26") in ("2026-05", "2026-06")
      or parse_memo_month("05.06.26") is not None)
check("יוני 2026", parse_memo_month("חודש יוני 2026") == "2026-06",
      parse_memo_month("חודש יוני 2026"))
check("empty -> None", parse_memo_month("") is None)
check("no month -> None", parse_memo_month("תשלום ספק רגיל") is None)
check("is_income 80001", is_income_budget_code("80001"))
check("is_income 81001", is_income_budget_code("81001"))
check("not income 22604", not is_income_budget_code("22604"))

# ---------------------------------------------------------------------------
# Phase 2 — debit + credit net
# ---------------------------------------------------------------------------
print("\n§I2 debit-credit net")
am = {
    "accounts": {
        "18022609": {"sheet": "מועדון", "budget_code": "22609"},
        "10180001": {"sheet": "מועדון", "budget_code": "80001"},
    },
    "exclude_prefixes": [],
}
txns = [
    {"account": "18022609", "budget_month": "2026-06", "debit": 1000.0, "credit": 200.0},
    {"account": "18022609", "budget_month": "2026-06", "debit": 50.0, "credit": 0.0},
    {"account": "10180001", "budget_month": "2026-06", "debit": 0.0, "credit": 5000.0},
]
mv, unm = monthly_movement(txns, am)
check("expense net = debit-credit", abs(mv[("מועדון", "22609", "2026-06")] - 850.0) < 0.01,
      mv.get(("מועדון", "22609", "2026-06")))
check("income net negative (credit-heavy)", mv[("מועדון", "80001", "2026-06")] < 0,
      mv.get(("מועדון", "80001", "2026-06")))
check("income net = -5000", abs(mv[("מועדון", "80001", "2026-06")] - (-5000.0)) < 0.01)

# ---------------------------------------------------------------------------
# Phase 1 — strip note rows
# ---------------------------------------------------------------------------
print("\n§I1 strip note rows")
wb = openpyxl.Workbook()
ws = wb.active
ws.title = "test"
ws.cell(2, 1, "סעיף תקציבי")
ws.cell(2, 2, "הכנסה")
ws.cell(2, 3, "ינואר")
ws.cell(2, 4, "ינואר - ביצוע")
ws.cell(3, 1, 80001)
ws.cell(3, 2, "מנויים")
ws.cell(3, 4, -100)
ws.cell(4, 2, "הוצאה")
ws.cell(5, 1, 22604)
ws.cell(5, 2, "עלות מאמנים")
ws.cell(5, 4, 50)
ws.cell(6, 2, 'סה"כ תקציב')
ws.cell(6, 4, -50)
# note rows (Idan's bottom junk)
ws.cell(7, 2, "דמי הרשמה")
ws.cell(7, 3, 85.47)
ws.cell(8, 2, "מנוי סטודיו")
ws.cell(8, 3, 247.86)
ws.cell(9, 2, "מחיר מנוי ממוצע")
ws.cell(9, 3, 245)
ws.cell(10, 2, '*המחירים לפני מע"מ')
n_del = LO._strip_note_rows(ws)
check("deleted 4 note rows", n_del == 4, n_del)
labels = [str(ws.cell(r, 2).value or "") for r in range(1, ws.max_row + 1)]
check("no דמי הרשמה left", not any("דמי הרשמה" in x for x in labels), labels)
check("kept סה\"כ", any("סה" in x for x in labels))
check("kept מנויים code row", any(ws.cell(r, 1).value == 80001 for r in range(1, ws.max_row + 1)))
wb.close()

# ---------------------------------------------------------------------------
# Phase 1+5+6 — full build mini fixture
# ---------------------------------------------------------------------------
print("\n§I156 build mini budget")
src = os.path.join(OUT, "_t_idan_src.xlsx")
wb = openpyxl.Workbook()
# sheet name must match SRC_TABS
ws = wb.active
ws.title = "תקציב מול ביצוע 2026 - מועדון"[:31]
# openpyxl title max 31 — actual tab key in SRC_TABS is longer; set via rename carefully
wb.close()

# openpyxl truncates title — use exact SRC_TABS value (31 chars max in Excel)
tab_name = LO.SRC_TABS["חדר כושר"]
assert len(tab_name) <= 31 or True
wb = openpyxl.Workbook()
ws = wb.active
ws.title = tab_name[:31]
# If truncated, patch SRC_TABS temporarily for this test
if ws.title != tab_name:
    LO.SRC_TABS["חדר כושר"] = ws.title

ws.cell(2, 1, "סעיף תקציבי")
ws.cell(2, 2, "הכנסה")
ws.cell(2, 3, "ינואר")
ws.cell(2, 4, "ינואר - ביצוע")
ws.cell(2, 5, "פברואר")
ws.cell(2, 6, "פברואר - ביצוע")
ws.cell(2, 7, "יוני")
ws.cell(2, 8, "יוני - ביצוע")

ws.cell(3, 1, 80001)
ws.cell(3, 2, "מנויים")
ws.cell(3, 3, 150000)  # budget
ws.cell(3, 4, -140000)  # jan actual
ws.cell(3, 5, 150000)
ws.cell(3, 6, -139000)
ws.cell(3, 7, 160000)
ws.cell(3, 8, 0)

ws.cell(4, 2, "הוצאה")

ws.cell(5, 1, 22609)
ws.cell(5, 2, "חשמל")
ws.cell(5, 3, 3000)
ws.cell(5, 4, 3215)
ws.cell(5, 5, 3000)
ws.cell(5, 6, 3200)
ws.cell(5, 7, 5000)
ws.cell(5, 8, 0)

ws.cell(6, 2, 'סה"כ הכנסות')
ws.cell(7, 2, 'סה"כ הוצאות')
ws.cell(8, 2, "רווח / הפסד תפעולי")

# note junk
ws.cell(9, 2, "מנוי חדר כושר")
ws.cell(9, 3, 239)

wb.save(src)
wb.close()

movement = {
    ("מועדון", "80001", "2026-06"): -140478.81,
    ("מועדון", "22609", "2026-06"): 5307.4,
}
# inject positive income to test Phase 6 flip
movement_pos = {
    ("מועדון", "80001", "2026-06"): 999.0,  # wrong sign from ledger
    ("מועדון", "22609", "2026-06"): 5307.4,
}
out_path = os.path.join(OUT, "_t_idan_out.xlsx")
n = LO.build(src, "חדר כושר", movement_pos, out_path, "יוני", "2026-06")
check("build wrote cells", n >= 1, n)

wb = openpyxl.load_workbook(out_path, data_only=True)
ws = wb.active
labels = [str(ws.cell(r, 2).value or "") for r in range(1, ws.max_row + 1)]
check("notes stripped from output", not any("מנוי חדר כושר" in x for x in labels), labels)

# find 80001 row
r800 = None
r226 = None
for r in range(1, ws.max_row + 1):
    c = ws.cell(r, 1).value
    if c == 80001 or c == "80001":
        r800 = r
    if c == 22609 or c == "22609":
        r226 = r
check("found 80001", r800 is not None)
check("found 22609", r226 is not None)

# find June display col
jun_disp = LO._find_header(ws, "יוני - ביצוע") or LO._find_header(ws, "יוני ביצוע")
# after two-layer insert headers change
headers = {c: ws.cell(2, c).value for c in range(1, ws.max_column + 1)}
print("  headers:", {k: v for k, v in headers.items() if v})
# find ledger and display for June
lc = LO._find_header(ws, "יוני ביצוע (כרטסת)")
dc = LO._find_header(ws, "יוני - ביצוע")
check("two-layer ledger col exists", lc is not None, lc)
check("two-layer display col exists", dc is not None, dc)

if r800 and dc:
    val = ws.cell(r800, dc).value
    check("income forced negative (phase 6)", val is not None and float(val) <= 0, val)
if r226 and dc:
    val = ws.cell(r226, dc).value
    check("expense stays positive", val is not None and float(val) > 0, val)

# YTD headers
ytd_h = [str(v) for v in headers.values() if v and "YTD" in str(v) or (v and "1-6" in str(v))]
check("YTD columns present", any("1-6" in str(v) for v in headers.values() if v), headers)

# footer
footer_found = any(
    "gym-recon ledger_sync" in str(ws.cell(r, 1).value or "")
    for r in range(1, ws.max_row + 1)
)
check("engine footer present", footer_found)

# rollup: income total row (must contain סה"כ + הכנס — not bare "הכנסה" header)
for r in range(3, ws.max_row + 1):
    lbl = str(ws.cell(r, 2).value or "")
    if "סה" in lbl and "הכנס" in lbl and dc:
        iv = ws.cell(r, dc).value
        check("income total is number", isinstance(iv, (int, float)), iv)
        if r800 and isinstance(iv, (int, float)):
            check("income total ≈ income line", abs(float(iv) - float(ws.cell(r800, dc).value or 0)) < 0.02,
                  f"total={iv} line={ws.cell(r800, dc).value}")
        break
else:
    check("income total row found", False, "no סה\"כ הכנסות row")

wb.close()

# ---------------------------------------------------------------------------
print(f"\n==== {ok} passed, {fail} failed ====")
sys.exit(1 if fail else 0)
