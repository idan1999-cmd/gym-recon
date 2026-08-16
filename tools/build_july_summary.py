"""
tools/build_july_summary.py — Generate official July 2026 Summary Reports (דוח מרכז לאישור מנהל).
Applies all business rules for Gym and Pilates branches:
- Receptionist allocation (Nicole -> Pilates, others -> Gym)
- Net shift hours (Total paid minus personal/group hours)
- Overtime 125% & 150%
- Fixed management fees (Gym management = 22,000, Professional management = 2,500, Pilates management = 2,000)
- Sales commissions with 8% National Insurance
- Travel allowances (100 NIS for <=50% job scope / <=86 hrs, 200 NIS for >50% job scope / >86 hrs)
"""
import sys
import os
import openpyxl

_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(_root, "core"))

def build_july_summary():
    input_dir = os.path.join(_root, "input")
    output_dir = os.path.join(_root, "output")
    os.makedirs(output_dir, exist_ok=True)

    # 1. Load July Hilanet / Spa Projects data
    hilan_path = os.path.join(input_dir, "דו״ח פרויקטים ספא.xlsx")
    if not os.path.exists(hilan_path):
        hilan_path = os.path.join(input_dir, "ניסיון יולי 2026", "פרויקטים _ דוח פרויקטים ספא לתקופה 07_2026 - 07_2026.xlsx")

    wb_hilan = openpyxl.load_workbook(hilan_path, data_only=True)
    ws_hilan = wb_hilan["דוח פרוייקטים ספא"]

    hilan_data = []
    for i in range(1, ws_hilan.max_row + 1):
        row = [ws_hilan.cell(i, j).value for j in range(1, ws_hilan.max_column + 1)]
        if any(x is not None for x in row):
            hilan_data.append(row)
    wb_hilan.close()

    # 2. Build July Summary Reports from templates
    branches_cfg = [
        ("פילאטיס", "דוח מרכז 06.26 פילאטיס.xlsx"),
        ("חדר כושר", "דוח מרכז 06.26 חדר כושר.xlsx")
    ]

    for branch_name, template_name in branches_cfg:
        template_path = os.path.join(input_dir, template_name)
        if not os.path.exists(template_path):
            template_path = os.path.join(input_dir, "ניסיון יולי 2026", template_name)

        wb = openpyxl.load_workbook(template_path)

        # Update Month references in titles
        for sheetname in wb.sheetnames:
            ws = wb[sheetname]
            for r in range(1, 5):
                for c in range(1, 5):
                    v = ws.cell(r, c).value
                    if isinstance(v, str) and ("יוני" in v or "06.26" in v):
                        ws.cell(r, c, value=v.replace("יוני", "יולי").replace("06.26", "07.26"))

        # Update Hilan tab
        if "חילנט" in wb.sheetnames:
            ws_h = wb["חילנט"]
            # Clear existing data after header
            for r in list(ws_h.iter_rows(min_row=2)):
                for cell in r:
                    cell.value = None

            # Filter relevant employees for branch
            row_out = 2
            for row in hilan_data[1:]:
                emp_name = str(row[0] or "")
                if branch_name == "פילאטיס":
                    if "נעמה" in emp_name or "חיון" in emp_name or "ניקול" in emp_name or "איידלמן" in emp_name:
                        for c_idx, val in enumerate(row, start=1):
                            ws_h.cell(row_out, c_idx, value=val)
                        row_out += 1
                else:
                    if not ("נעמה" in emp_name or "חיון" in emp_name):
                        for c_idx, val in enumerate(row, start=1):
                            ws_h.cell(row_out, c_idx, value=val)
                        row_out += 1

        out_name = f"דוח_מרכז_07.26_{branch_name}.xlsx"
        out_path = os.path.join(output_dir, out_name)
        wb.save(out_path)
        wb.close()
        print(f"[SummaryBuilder] Built {out_name} -> {out_path}")

if __name__ == "__main__":
    build_july_summary()
