"""
Thin bridge to OfficeCLI.
All functions raise RuntimeError on non-zero exit unless documented otherwise.

Usage:
    from core.officecli_bridge import available, validate
    if available():
        validate("path/to/file.xlsx")

Policy v1: OfficeCLI is post-run validate only. Never write money cells.
"""
import subprocess
import sys
import json
import os

OFFICECLI_CMD = "officecli"


def _officecli_path() -> str:
    """Resolve the officecli executable path, or return bare name."""
    return "officecli"


def run(args: list[str]) -> dict | str:
    """
    Run `officecli` with the given args plus --json.
    Returns parsed JSON dict if possible, else raw stdout string.
    Raises RuntimeError on non-zero exit.
    """
    cmd = [_officecli_path()] + args
    # Add --json if not already present and not a flag-only command
    if "--json" not in args and "--version" not in args:
        cmd.append("--json")
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=60,
        )
    except FileNotFoundError:
        raise RuntimeError("officecli not found on PATH")
    except subprocess.TimeoutExpired:
        raise RuntimeError("officecli timed out")
    if result.returncode != 0:
        stderr = result.stderr.strip() or "(no stderr)"
        raise RuntimeError(f"officecli exited {result.returncode}: {stderr}")
    out = result.stdout.strip()
    if not out:
        return ""
    # Try to parse JSON
    try:
        return json.loads(out)
    except (json.JSONDecodeError, ValueError):
        pass
    return out


def available() -> bool:
    """Return True if officecli is on PATH and responsive."""
    try:
        result = subprocess.run(
            [_officecli_path(), "--version"],
            capture_output=True,
            text=True,
            timeout=15,
        )
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
        return False


def validate(path: str) -> dict | str:
    """Validate an Excel file. Returns JSON result or raw string."""
    abs_path = os.path.abspath(path)
    return run(["validate", abs_path])


def view_issues(path: str) -> dict | str:
    """View validation issues for an Excel file."""
    abs_path = os.path.abspath(path)
    return run(["view", abs_path, "issues"])


def _quote_sheet(sheet: str) -> str:
    """Quote a sheet name for an OfficeCLI path if it contains special chars."""
    # Sheet names with spaces, Hebrew, or special chars need quoting
    if any(c in sheet for c in " /\\[]"):
        return f"'{sheet}'"
    return sheet


def get_cell(path: str, sheet: str, cell: str) -> dict | str:
    """Get cell value from an Excel file."""
    abs_path = os.path.abspath(path)
    sheet_q = _quote_sheet(sheet)
    return run(["get", abs_path, f"/{sheet_q}/{cell}"])


def set_value(path: str, sheet: str, cell: str, value: str) -> dict | str:
    """Set a cell value in an Excel file."""
    abs_path = os.path.abspath(path)
    sheet_q = _quote_sheet(sheet)
    return run(["set", abs_path, f"/{sheet_q}/{cell}", "--prop", f"value={value}"])


def batch_set(path: str, items: list[tuple[str, str, str]]) -> list[dict | str]:
    """
    Batch set multiple cells. Each item is (sheet, cell, value).
    Falls back to looping set_value.
    """
    results = []
    for sheet, cell, value in items:
        results.append(set_value(path, sheet, cell, value))
    return results


def save_close(path: str) -> None:
    """Save and close an Excel file opened by OfficeCLI. Ignore if not open."""
    abs_path = os.path.abspath(path)
    for cmd in ["save", "close"]:
        try:
            subprocess.run(
                [_officecli_path(), cmd, abs_path],
                capture_output=True,
                text=True,
                timeout=30,
            )
        except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
            pass
