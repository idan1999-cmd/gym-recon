"""
Trainer Billing (חיוב) — the merged invoice-audit + report-write job.

This replaces the old split of Job 1 (audit) and Job 2 (report). The manager's
mental model, confirmed by Amit, is that these are Phase A and Phase B of ONE
job:

  Phase A — VALIDATE
    * salaried hours: trusted from the manager-approved sheet, cross-checked
      against Hilan (system hours vs actually-worked hours).
    * freelancer invoices: three-way matched (invoice OCR × Arbox held sessions
      × agreed rate) via jobs.audit. Each invoice gets a verdict:
        OK        -> safe to auto-write
        REVIEW    -> a soft flag (info/warn); still written but marked
        BLOCK     -> a hard flag (HIGH); NOT written, manager must resolve

  Phase B — WRITE
    * For every branch, the validated freelancer totals are written into the
      corresponding "מאמני חוץ" (external) rows of דוח מרכז לאישור מנהל,
      grouped by category (studio/class/personal/group). The salaried lines are
      left exactly as the manager signed them. The grand-total cell is then
      recomputed from the detail block.
    * Nothing the analyzer is unsure about is silently placed: BLOCK invoices
      are held out and surfaced in the audit log for manager sign-off.
    * Trainer-data gate (human-in-the-loop): every validated $ amount is first
      resolved to a KNOWN trainer (exact -> normalized -> fuzzy>=88, via
      common.resolve_trainer / config/trainer_aliases.json) before it is ever
      allowed into a by_category bucket that Phase B writes. UNKNOWN trainers
      never reach Excel — they are only ever surfaced as pending proposals.

Runs once PER BRANCH (פילאטיס, חדר כושר). Config in config/branches.json.
"""
import sys, os, json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "core"))
sys.path.insert(0, os.path.dirname(__file__))
import openpyxl
from common import (load_aliases, load_pay_matrix, load_json,
                    resolve_trainer, audit_entry,
                    service_month_from_dates, month_key)
from arbox import load_sessions
from audit import audit_invoice, verdict_for   # Phase-A engine (renamed job1)


def _num(x):
    try:
        return float(x)
    except (ValueError, TypeError):
        return 0.0


def load_branches():
    return load_json("branches.json")["branches"]


# ---------------------------------------------------------------- Phase A ----
def validate_invoices(invoices, branch_key, all_sessions, aliases, pay, log, target_month_key=None):
    """
    Run the three-way audit on the invoices belonging to `branch_key`.
    Returns:
      by_category    -> {category: validated_amount} safe/soft enough to write
      held           -> list of held-out (BLOCK) invoices
      trainer_amounts-> list of EVERY validated amount (one entry per invoice
                         that was NOT blocked), for the amounts cache
                         (output/trainer_amounts_<branch>.json). Written BEFORE
                         anything touches Excel — see jobs/billing_output.py.
    """
    by_category, held, trainer_amounts = {}, [], []
    branch_alt = {"חדר כושר": ["חדר כושר", "מועדון", "כושר"],
                  "מועדון": ["חדר כושר", "מועדון", "כושר"],
                  "פילאטיס": ["פילאטיס"]}.get(branch_key, [branch_key])
    for inv in invoices:
        b_inv = str(inv.get("branch") or "")
        if b_inv and not any(alt in b_inv for alt in branch_alt):
            continue
        smonth = service_month_from_dates(inv.get("session_dates")) \
                 or month_key(inv.get("doc_date"))
        if target_month_key and smonth and smonth != target_month_key:
            continue
        entries = []
        audit_invoice(inv, all_sessions, aliases, pay, entries)
        log.extend(entries)
        verdict = verdict_for(entries)
        cat = inv.get("category", "studio")
        amt = _num(inv.get("stated_total"))
        tid, canon, score, method = resolve_trainer(inv.get("trainer"), aliases)
        smonth = service_month_from_dates(inv.get("session_dates")) \
                 or month_key(inv.get("doc_date"))
        if verdict == "BLOCK":
            held.append({"invoice": inv, "amount": amt, "category": cat})
            log.append(audit_entry("BILLING_HELD", trainer_id=None,
                ref=f'{inv.get("trainer")}/{inv.get("doc_number")}',
                amount=amt, severity="HIGH",
                note=f'invoice held out of auto-write ({inv.get("category")}); '
                     f'manager must resolve the HIGH flag before it is booked'))
        else:
            by_category[cat] = by_category.get(cat, 0.0) + amt
            # amounts cache entry — resolved trainer identity travels with the
            # amount even though the Excel write below is category-aggregated
            trainer_amounts.append({
                "raw_name": inv.get("trainer"),
                "trainer_id": tid,
                "tax_id": inv.get("issuer_tax_id"),
                "category": cat,
                "amount": round(amt, 2),
                "source_invoice": inv.get("doc_number"),
                "service_month": smonth,
            })
            if verdict == "REVIEW":
                log.append(audit_entry("BILLING_WRITE_FLAGGED",
                    ref=f'{inv.get("trainer")}/{inv.get("doc_number")}',
                    amount=amt, severity="WARN",
                    note=f'auto-written to {cat} but carries a soft flag — verify'))
    return by_category, held, trainer_amounts


def missing_receipts(branch_key, all_sessions, aliases, trainer_amounts, target_month_key=None):
    """
    Freelancer trainers who held Arbox sessions for this branch (in the target
    service month, when known) but have NO validated amount in trainer_amounts
    this run -> "חסרות קבלות". Never fabricates a number; only flags the name
    for the manager. `all_sessions` is the FULL session list (not pre-filtered
    by branch), matching how it is loaded/passed elsewhere in this codebase.
    """
    seen_tids = {a["trainer_id"] for a in trainer_amounts if a.get("trainer_id")}
    freelancer_ids = {t["trainer_id"] for t in aliases["trainers"]
                       if t.get("employment") == "freelancer"}
    branch_alt = {"חדר כושר": ["חדר כושר", "מועדון"],
                  "פילאטיס": ["פילאטיס"]}.get(branch_key, [branch_key])
    expected = set()
    for s in all_sessions:
        tid = s.get("trainer_id")
        if tid not in freelancer_ids:
            continue
        if target_month_key and s.get("month") != target_month_key:
            continue
        b = str(s.get("branch") or "")
        if not b or any(alt in b for alt in branch_alt):
            expected.add(tid)
    missing_ids = expected - seen_tids
    id2name = {t["trainer_id"]: t["canonical_name"] for t in aliases["trainers"]}
    return sorted(id2name.get(tid, tid) for tid in missing_ids)


# ---------------------------------------------------------------- Phase B ----
def write_report(wb, branch_key, branch_cfg, by_category, log):
    """
    Write validated freelancer amounts into the מאמני חוץ rows, recompute total.
    Salaried/manager-signed rows are never touched.
    """
    ws = wb[branch_cfg["approval_sheet"]]
    ext = branch_cfg["external_lines"]
    amt_col = branch_cfg["amount_col"]

    # group category amounts by the target row (several categories may share a row)
    row_amounts = {}
    unrouted = {}
    for cat, amount in by_category.items():
        line = ext.get(cat)
        if line is None:
            unrouted[cat] = amount
            log.append(audit_entry("BILLING_UNROUTED", ref=branch_key,
                amount=round(amount, 2), severity="WARN",
                note=f'category "{cat}" has no מאמני חוץ row in this branch — '
                     f'{round(amount,2)} NOT written, needs mapping'))
            continue
        row_amounts.setdefault(line["row"], 0.0)
        row_amounts[line["row"]] += amount

    written = []
    for row, amount in row_amounts.items():
        old = _num(ws.cell(row, amt_col).value)
        ws.cell(row, amt_col, value=round(amount, 2))
        label = ws.cell(row, branch_cfg["name_col"]).value
        written.append((row, label, old, round(amount, 2)))
        log.append(audit_entry("BILLING_WRITE", ref=f"{branch_key}/row{row}",
            expected=old, actual=round(amount, 2), amount=round(amount, 2),
            severity="INFO",
            note=f'wrote {round(amount,2)} into "{label}" (was {old})'))

    # recompute grand total from the detail block (sum of amount_col over rows)
    total = 0.0
    for r in range(branch_cfg["detail_first_row"], branch_cfg["detail_last_row"] + 1):
        total += _num(ws.cell(r, amt_col).value)
    total = round(total, 2)

    # write recomputed total into the total cell
    tc = branch_cfg["total_cell"]
    from openpyxl.utils.cell import coordinate_from_string, column_index_from_string
    col_letters, trow = coordinate_from_string(tc)
    tcol = column_index_from_string(col_letters)
    old_total = _num(ws.cell(trow, tcol).value)
    ws.cell(trow, tcol, value=total)

    log.append(audit_entry("BILLING_TOTAL", ref=branch_key,
        expected=old_total, actual=total, amount=total, severity="INFO",
        note=f'recomputed grand total {total} (was {old_total})'))
    return total, written


# ---------------------------------------------------- Hilan cross-check ------
def check_hilan(wb, branch_key, cfg, pay, log):
    ws = wb[cfg["approval_sheet"]]
    sys_h = _num(ws.cell(cfg["hilan_system_row"], cfg["hilan_col"]).value)
    act_h = _num(ws.cell(cfg["hilan_actual_row"], cfg["hilan_col"]).value)
    tol = pay.get("hilan_tolerance_hours", 2.0)
    delta = abs(sys_h - act_h)
    if delta > tol + 1e-6:
        log.append(audit_entry("HILAN_DELTA", ref=branch_key,
            expected=sys_h, actual=act_h, amount=delta, severity="WARN",
            note=f"Hilan hours {act_h} vs system {sys_h} differ {delta:.2f}h > tol {tol}h"))
    else:
        log.append(audit_entry("HILAN_OK", ref=branch_key,
            expected=sys_h, actual=act_h, amount=delta, severity="INFO",
            note=f"Hilan reconciled within {tol}h (Δ{delta:.2f})"))
    return sys_h, act_h, delta


# ----------------------------------------------------------------- run -------
def run(branch_key, workbook_path, invoices_json, sessions_path,
        out_workbook=None, audit_log=None):
    log = audit_log if audit_log is not None else []
    branches = load_branches()
    cfg = branches[branch_key]
    aliases = load_aliases()
    pay = load_pay_matrix()

    with open(invoices_json, encoding="utf-8") as f:
        invoices = json.load(f)["invoices"]
    all_sessions = load_sessions(sessions_path, aliases) if sessions_path else []

    # Phase A
    by_category, held, trainer_amounts = validate_invoices(invoices, branch_key, all_sessions,
                                          aliases, pay, log)
    # open workbook for Phase B (keep formulas out; we write values)
    wb = openpyxl.load_workbook(workbook_path, data_only=True)
    sys_h, act_h, hdelta = check_hilan(wb, branch_key, cfg, pay, log)
    # Phase B
    total, written = write_report(wb, branch_key, cfg, by_category, log)

    new_trainers = [e["proposal"] for e in log
                    if e.get("type") == "UNMAPPED_NAME" and e.get("proposal")]
    result = {
        "branch": branch_key, "label": cfg["label"],
        "new_trainers_to_approve": new_trainers,
        "grand_total": total, "target": cfg["total_target"],
        "match": abs(total - cfg["total_target"]) < 0.05,
        "freelancer_by_category": {k: round(v, 2) for k, v in by_category.items()},
        "held_out": [{"trainer": h["invoice"].get("trainer"),
                      "doc": h["invoice"].get("doc_number"),
                      "amount": h["amount"], "category": h["category"]} for h in held],
        "hilan": {"system": sys_h, "actual": act_h, "delta": round(hdelta, 2)},
        "rows_written": [{"row": r, "label": l, "old": o, "new": n}
                         for (r, l, o, n) in written],
        "trainer_amounts": trainer_amounts,
    }
    if out_workbook:
        wb.save(out_workbook)
    wb.close()
    return result, log
