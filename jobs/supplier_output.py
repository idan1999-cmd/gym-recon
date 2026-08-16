"""
Supplier Output Builder — creates the workbook ספקים_לאישור_מנהל.xlsx with:

  +30 sheet:    ספקי שירות +30     — suppliers with +30 day payment terms
  +60 sheet:    ספקי ציבור +60     — suppliers with +60 day payment terms
  Flags sheet:  דגלים ספקים       — unknown suppliers / VAT mismatches

Design:
  * openpyxl ONLY (no OfficeCLI).
  * Right-to-left layout for Hebrew readers.
  * Column אושר לתשלום (צהוב) with empty checkboxes highlighted in yellow.
  * Status column for each line: OK or HOLD_NEW_SUPPLIER.
  * Summary line at bottom of each payment sheet with grand total.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "core"))
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
from datetime import datetime

MONTHS_HE = [
    "ינואר", "פברואר", "מרץ", "אפריל", "מאי", "יוני",
    "יולי", "אוגוסט", "ספטמבר", "אוקטובר", "נובמבר", "דצמבר",
]

# Styles
HDR_FONT = Font(bold=True, color="FFFFFF", size=11)
HDR_FILL = PatternFill("solid", fgColor="2F5597")
HDR_ALIGN = Alignment(horizontal="center", vertical="center", wrap_text=True)

YELLOW_FILL = PatternFill("solid", fgColor="FFFF00")
WARN_FILL = PatternFill("solid", fgColor="FCE4D6")
HOLD_FILL = PatternFill("solid", fgColor="FFCCCC")
GREEN_FILL = PatternFill("solid", fgColor="C6EFCE")

THIN_BORDER = Border(
    left=Side(style="thin"),
    right=Side(style="thin"),
    top=Side(style="thin"),
    bottom=Side(style="thin"),
)

TOTAL_FONT = Font(bold=True, size=11)
STATUS_FONT = Font(bold=True)

# Column layout (1-indexed)
COL_SUPPLIER = 1    # ספק
COL_GL_CODE = 2     # קוד חשבון
COL_INV_NUM = 3     # חשבונית #
COL_DATE = 4        # תאריך
COL_DESC = 5        # תיאור
COL_TOTAL = 6       # סכום כולל
COL_VAT = 7         # מע"מ
COL_TERMS = 8       # תנאי תשלום
COL_STATUS = 9      # סטטוס
COL_APPROVED = 10   # אושר לתשלום (צהוב)

HEADERS_30 = [
    "ספק", "קוד חשבון", "חשבונית #", "תאריך", "תיאור",
    "סכום כולל", "מע\"מ", "תנאי תשלום", "סטטוס", "אושר לתשלום (צהוב)"
]

HEADERS_FLAGS = [
    "ספק", "ח.פ / ת.ז", "חשבונית #", "תאריך", "סכום כולל",
    "מע\"מ", "תיאור", "סטטוס", "הערה"
]


def _style_header(ws, row, ncols, headers):
    """Apply header styling."""
    for i, h in enumerate(headers, 1):
        c = ws.cell(row, i, h)
        c.font = HDR_FONT
        c.fill = HDR_FILL
        c.alignment = HDR_ALIGN
        c.border = THIN_BORDER


def _auto_width(ws, ncols, max_rows=30):
    """Set approximate column widths."""
    widths = {
        COL_SUPPLIER: 22, COL_GL_CODE: 14, COL_INV_NUM: 14, COL_DATE: 13,
        COL_DESC: 30, COL_TOTAL: 14, COL_VAT: 12, COL_TERMS: 14,
        COL_STATUS: 16, COL_APPROVED: 18,
    }
    for col, w in widths.items():
        if col <= ncols:
            ws.column_dimensions[get_column_letter(col)].width = w


def _write_detail_rows(ws, start_row, payments):
    """Write payment detail rows with data and styling."""
    r = start_row
    for p in payments:
        ws.cell(r, COL_SUPPLIER, p.get("supplier_name", ""))
        ws.cell(r, COL_GL_CODE, p.get("account_code", ""))
        ws.cell(r, COL_INV_NUM, p.get("doc_number", ""))
        ws.cell(r, COL_DATE, p.get("doc_date", ""))
        ws.cell(r, COL_DESC, p.get("line_description", ""))
        ws.cell(r, COL_TOTAL, p.get("total_amount", 0))
        ws.cell(r, COL_VAT, p.get("vat_amount", 0))
        ws.cell(r, COL_TERMS, p.get("payment_terms_hint", "+30"))
        # Status
        status = p.get("status", "OK")
        sc = ws.cell(r, COL_STATUS, status)
        if status == "HOLD_NEW_SUPPLIER":
            sc.fill = HOLD_FILL
            sc.font = STATUS_FONT
        else:
            sc.fill = GREEN_FILL
        # Approved checkbox cell — yellow highlighted empty cell
        ac = ws.cell(r, COL_APPROVED, "")
        ac.fill = YELLOW_FILL
        ac.border = THIN_BORDER
        # Apply borders to all cells
        for c in range(1, COL_APPROVED + 1):
            ws.cell(r, c).border = THIN_BORDER
        # Format total as currency-like number
        ws.cell(r, COL_TOTAL).number_format = '#,##0.00'
        ws.cell(r, COL_VAT).number_format = '#,##0.00'
        r += 1
    return r


def _write_summary(ws, row, total, label="סה\"כ"):
    """Write a summary row with bold total."""
    ws.cell(row, COL_SUPPLIER, label).font = TOTAL_FONT
    ws.cell(row, COL_TOTAL, total).font = TOTAL_FONT
    ws.cell(row, COL_TOTAL).number_format = '#,##0.00'
    for c in range(1, COL_APPROVED + 1):
        ws.cell(row, c).border = THIN_BORDER
    return row + 2


def build(payments_30, payments_60, held, totals, out_path, month=None):
    """
    Build the supplier approval workbook.

    Parameters:
      payments_30 : list of matched +30 day payment dicts
      payments_60 : list of matched +60 day payment dicts
      held        : list of unknown/flagged supplier dicts
      totals      : dict with total_30, total_60, n_held
      out_path    : output file path
      month       : month number (1-12), for title
    """
    wb = openpyxl.Workbook()

    month_he = MONTHS_HE[month - 1] if month and 1 <= month <= 12 else ""

    # --- Sheet 1: +30 day suppliers ---
    ws30 = wb.active
    ws30.title = "ספקי שירות +30"
    ws30.sheet_view.rightToLeft = True

    title = f"ספקים לאישור מנהל — {'+30 ימים' if not month_he else f'{month_he} +30 ימים'}"
    ws30.cell(1, 1, title).font = Font(bold=True, size=14)
    ws30.merge_cells(start_row=1, start_column=1, end_row=1, end_column=COL_APPROVED)

    _style_header(ws30, 3, COL_APPROVED, HEADERS_30)
    _auto_width(ws30, COL_APPROVED)
    next_row = _write_detail_rows(ws30, 4, payments_30)
    _write_summary(ws30, next_row, totals["total_30"], f"סה\"כ לתשלום +30")

    # --- Sheet 2: +60 day suppliers ---
    ws60 = wb.create_sheet("ספקי ציבור +60")
    ws60.sheet_view.rightToLeft = True

    title60 = f"ספקים לאישור מנהל — {'+60 ימים' if not month_he else f'{month_he} +60 ימים'}"
    ws60.cell(1, 1, title60).font = Font(bold=True, size=14)
    ws60.merge_cells(start_row=1, start_column=1, end_row=1, end_column=COL_APPROVED)

    _style_header(ws60, 3, COL_APPROVED, HEADERS_30)
    _auto_width(ws60, COL_APPROVED)
    next_row60 = _write_detail_rows(ws60, 4, payments_60)
    _write_summary(ws60, next_row60, totals["total_60"], f"סה\"כ לתשלום +60")

    # --- Sheet 3: Flags ---
    ws_flags = wb.create_sheet("דגלים ספקים")
    ws_flags.sheet_view.rightToLeft = True

    ws_flags.cell(1, 1, f"דגלים לתשומת לב המנהל — ספקים לא מזוהים / חריגים").font = Font(bold=True, size=13)
    ws_flags.merge_cells(start_row=1, start_column=1, end_row=1, end_column=9)

    _style_header(ws_flags, 3, 9, HEADERS_FLAGS)

    widths_flags = {1: 22, 2: 14, 3: 14, 4: 13, 5: 14, 6: 12, 7: 30, 8: 16, 9: 30}
    for col, w in widths_flags.items():
        ws_flags.column_dimensions[get_column_letter(col)].width = w

    r = 4
    if held:
        for h in held:
            ws_flags.cell(r, 1, h.get("supplier_name", ""))
            ws_flags.cell(r, 2, h.get("tax_id", ""))
            ws_flags.cell(r, 3, h.get("doc_number", ""))
            ws_flags.cell(r, 4, h.get("doc_date", ""))
            ws_flags.cell(r, 5, h.get("total_amount", 0))
            ws_flags.cell(r, 6, h.get("vat_amount", 0))
            ws_flags.cell(r, 7, h.get("line_description", ""))
            ws_flags.cell(r, 8, h.get("status", ""))
            ws_flags.cell(r, 9, f"Supplier not found in whitelist — add to config/supplier_whitelist.json")
            for c in range(1, 10):
                ws_flags.cell(r, c).fill = WARN_FILL
                ws_flags.cell(r, c).border = THIN_BORDER
            ws_flags.cell(r, 5).number_format = '#,##0.00'
            r += 1
    else:
        ws_flags.cell(r, 1, "אין דגלים — כל הספקים מזוהים").font = Font(bold=True, color="006600")
        ws_flags.cell(r, 1).fill = GREEN_FILL
        ws_flags.merge_cells(start_row=r, start_column=1, end_row=r, end_column=9)

    # Summary info at bottom of flags
    r += 2
    ws_flags.cell(r, 1, f"סה\"כ +30 ימים:").font = TOTAL_FONT
    ws_flags.cell(r, 2, totals["total_30"]).font = TOTAL_FONT
    ws_flags.cell(r, 2).number_format = '#,##0.00'
    r += 1
    ws_flags.cell(r, 1, f"סה\"כ +60 ימים:").font = TOTAL_FONT
    ws_flags.cell(r, 2, totals["total_60"]).font = TOTAL_FONT
    ws_flags.cell(r, 2).number_format = '#,##0.00'
    r += 1
    ws_flags.cell(r, 1, f"סה\"כ כללי:").font = Font(bold=True, size=12)
    ws_flags.cell(r, 2, totals["total_30"] + totals["total_60"]).font = Font(bold=True, size=12)
    ws_flags.cell(r, 2).number_format = '#,##0.00'
    r += 1
    ws_flags.cell(r, 1, f"ספקים חדשים לאישור:").font = TOTAL_FONT
    ws_flags.cell(r, 2, totals["n_held"]).font = TOTAL_FONT

    os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
    wb.save(out_path)
    wb.close()

    return {"ok": True, "path": out_path}
