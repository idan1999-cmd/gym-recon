"""
core/validation.py — Robust validation controls for the gym-recon pipeline.

Four gates, each returning a list of error strings (empty = pass)
and raising nothing unless there is a hard programming error:

  validate_input_file(path, format)      — file exists, correct extension, not empty
  validate_workbook(path, required_sheets) — required sheets/columns present, not empty
  validate_integrity(rows, critical_cols)  — no NaN, valid dates, numeric amounts
  validate_output(wb)                     — required sheets present, no leaked formulas

Design:
  * Pure functions, no I/O side effects except reading the given path.
  * On validation failure the caller is expected to log the error and exit code 1.
  * We do NOT silently coerce money here — a failed gate must stop the pipeline
    (the caller decides the exit code).

Business rule kept intact: income <= 0, expenses >= 0 are enforced on WRITE in
ledger_output; we only detect structural/data problems at read/write time here.
"""
import os
import math
import re
import openpyxl
from datetime import datetime


class ValidationError(Exception):
    """Raised when a validation gate fails. message = human-readable error."""


def validate_input_file(path, formats=(".xlsx", ".xls", ".csv", ".pdf", ".json")):
    """
    Input gate: file exists, has an allowed extension, and is not empty.
    Returns list of error strings (empty = ok).
    """
    errors = []
    if not path:
        errors.append("no input path given")
        return errors
    if not os.path.exists(path):
        errors.append(f"input file does not exist: {path}")
        return errors
    ext = os.path.splitext(path)[1].lower()
    if ext not in formats:
        errors.append(f"unexpected file type '{ext}' for {path} (allowed: {formats})")
        return errors
    if os.path.getsize(path) == 0:
        errors.append(f"input file is empty (0 bytes): {path}")
    return errors


def validate_workbook(path, required_sheets=None, required_header_cells=None):
    """
    Workbook gate: the file opens, required sheet tabs exist, and each required
    sheet is non-empty. Optionally verify a header cell pattern is present in any
    sheet (e.g. the כרטסת 'מט.' ledger header).
    Returns list of error strings (empty = ok).
    Raises ValidationError only on structural/open failures that can't be
    represented as a string list.
    """
    if path.endswith((".csv", ".CSV")):
        errors = validate_input_file(path, (".csv", ".CSV"))
        if errors:
            return errors
        if os.path.getsize(path) == 0:
            return [f"csv file is empty: {path}"]
        return []
    errors = validate_input_file(path, (".xlsx", ".xls"))
    if errors:
        return errors
    try:
        wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    except Exception as e:  # noqa: BLE001 — a bad file must be caught, not crash
        return [f"cannot open workbook {path}: {e}"]

    try:
        names = wb.sheetnames
        if not names:
            return [f"workbook has no sheets: {path}"]
        for need in required_sheets or []:
            if need not in names:
                errors.append(f"missing required sheet '{need}' in {path}")
        # non-empty check on each required sheet
        for need in required_sheets or []:
            if need not in names:
                continue
            ws = wb[need]
            try:
                empty = True
                for row in ws.iter_rows(values_only=True, max_row=2):
                    if any(v is not None for v in row):
                        empty = False
                        break
                if empty:
                    errors.append(f"sheet '{need}' in {path} is empty")
            except Exception as e:  # noqa: BLE001
                errors.append(f"cannot read sheet '{need}' in {path}: {e}")
        # header-cell signature over any sheet (used to confirm ledger type).
        # Scan the WHOLE of the earliest sheet(s) — the ledger 'מט.' header can sit
        # many rows down after title rows, so we must not cap at row 8.
        if required_header_cells:
            found_header = False
            scanned = 0
            for n in names:
                scanned += 1
                ws = wb[n]
                for i, row in enumerate(ws.iter_rows(values_only=True)):
                    joined = " ".join(str(c) for c in row if c is not None)
                    if any(cell in joined for cell in required_header_cells):
                        found_header = True
                        break
                if found_header:
                    break
                if scanned >= 6:  # only bound the number of sheets, not rows
                    break
            if not found_header:
                errors.append(f"none of the header cells {required_header_cells} found in {path}")
        return errors
    finally:
        wb.close()


def _is_nan(v):
    try:
        if isinstance(v, float) and math.isnan(v):
            return True
        if isinstance(v, str) and v.strip().lower() in ("nan", "none", "null"):
            return True
    except Exception:  # noqa: BLE001
        pass
    return False


def validate_integrity(rows, critical_cols, date_col=None, amount_col=None):
    """
    Data-integrity gate over an in-memory list of rows (each a dict or tuple).
    - no NaN / missing critical columns
    - date_col (index): every non-empty cell parses as a real date
    - amount_col (index): every non-empty cell is numeric
    Returns list of error strings (empty = ok).
    """
    errors = []
    for i, row in enumerate(rows):
        try:
            items = list(row.items()) if isinstance(row, dict) else list(enumerate(row))
        except Exception:  # noqa: BLE001
            errors.append(f"row {i}: unreadable structure {type(row).__name__}")
            continue
        d = dict(items)
        for col in critical_cols:
            v = d.get(col)
            if v is None or (isinstance(v, str) and not v.strip()) or _is_nan(v):
                errors.append(f"row {i}: critical column '{col}' is empty/NaN")
        if amount_col is not None:
            v = d.get(amount_col)
            if v is not None and not isinstance(v, (int, float)) and not _is_nan(v):
                try:
                    float(v)
                except (ValueError, TypeError):
                    errors.append(f"row {i}: amount column '{amount_col}' is not numeric: {v!r}")
        if date_col is not None:
            v = d.get(date_col)
            if v is not None and not _is_nan(v) and not isinstance(v, datetime):
                # accept Israeli ledger formats (dd/mm/yyyy, dd.mm.yy, etc.)
                from common import parse_date_any
                if parse_date_any(v) is None:
                    errors.append(f"row {i}: date column '{date_col}' not a parseable date: {v!r}")
    return errors


# Formula leak check: any cell starting with '=' left in the final report.
_LEAK_RE = re.compile(r"^\s*=")


def validate_output(wb, required_sheets=None):
    """
    Output gate over an OPEN openpyxl workbook (caller owns open/close).
    - required sheets present
    - no leaked formulas (cells whose value starts with '=')
    Returns list of error strings (empty = ok).
    """
    errors = []
    for need in required_sheets or []:
        if need not in wb.sheetnames:
            errors.append(f"output sheet missing: '{need}'")
    leaked = 0
    for name in wb.sheetnames:
        ws = wb[name]
        for row in ws.iter_rows():
            for cell in row:
                if isinstance(cell.value, str) and _LEAK_RE.match(cell.value):
                    leaked += 1
                    if leaked <= 25:
                        errors.append(f"leaked formula in {name}!{cell.coordinate}: {cell.value[:60]}")
    return errors