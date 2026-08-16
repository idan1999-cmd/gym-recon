"""
Job 1 — invoice ingestion + three-way audit.

Three-way = (invoice OCR)  vs  (Arbox held sessions)  vs  (agreed pay_matrix).
Goal: catch over-billing / ghost sessions / rate drift / wrong service month.

Every finding is an audit_entry. Nothing is auto-approved; anomalies get
severity WARN/HIGH for the manager to sign off.
"""
import sys, os, json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "core"))
from common import (load_aliases, load_pay_matrix, resolve_trainer,
                    service_month_from_dates, month_key, audit_entry,
                    propose_new_trainer)
from arbox import load_sessions, sessions_for, unmapped_names

# tolerance: invoiced qty may differ from Arbox count by this many units
QTY_TOL = 0.5
# hours tolerance when unit_kind == hour (durations vary 60/75 min)
HOUR_TOL = 1.0


def _invoice_service_month(inv):
    """Service month = month most session_dates fall in, NOT doc date."""
    sm = service_month_from_dates(inv.get("session_dates"))
    return sm or month_key(inv.get("doc_date"))


def _expected_qty_from_arbox(sess, unit_kind):
    """Arbox-side expected units for the trainer/month."""
    if unit_kind == "hour":
        return round(sum(s["duration"] for s in sess) / 60.0, 2)
    return len(sess)  # session/class count


def _has_arbox_footprint(all_sessions, tid):
    """True if trainer has ANY held session in Arbox (any month)."""
    return any(s["trainer_id"] == tid for s in all_sessions)


def audit_invoice(inv, all_sessions, aliases_cfg, pay_matrix, log):
    ref = f'{inv.get("trainer")}/{inv.get("doc_number")}'
    # 1) resolve trainer
    tid, canon, score, method = resolve_trainer(inv.get("trainer"), aliases_cfg)
    smonth = _invoice_service_month(inv)
    if tid is None:
        proposal = propose_new_trainer(inv, aliases_cfg)
        e = audit_entry("UNMAPPED_NAME", ref=ref, month=smonth,
            actual=inv.get("trainer"), amount=inv.get("stated_total"),
            severity="HIGH",
            note=("new/unknown trainer — held for manager. " + proposal["action"]))
        e["proposal"] = proposal   # ready-to-approve directory entry
        log.append(e)
        return  # cannot three-way match without identity

    # 2) doc-date vs service-month sanity
    dmk = month_key(inv.get("doc_date"))
    if smonth and dmk and smonth != dmk:
        log.append(audit_entry("SERVICE_MONTH_SHIFT", trainer_id=tid, ref=ref,
            month=smonth, expected=smonth, actual=dmk, severity="INFO",
            note="invoice dated in different month than service — billed to service month"))

    # 3) Arbox held sessions for this trainer/service-month
    sess = sessions_for(all_sessions, tid, smonth)
    unit_kind = inv.get("unit_kind", "session")
    line_items = inv.get("line_items", [])
    inv_qty = sum((li.get("qty") or 0) for li in line_items)
    has_mixed = any(li.get("category") in ("personal", "club_hours") or "אישי" in li.get("desc", "") or "משמרת" in li.get("desc", "") for li in line_items)
    if has_mixed:
        studio_qty = sum((li.get("qty") or 0) for li in line_items if li.get("category") == "studio" or "סטודיו" in li.get("desc", "") or "חוג" in li.get("desc", "") or "אימון סטודיו" in li.get("desc", "") or "פילאטיס" in li.get("desc", ""))
        comp_qty = studio_qty if studio_qty > 0 else inv_qty
    else:
        comp_qty = inv_qty

    arbox_qty = _expected_qty_from_arbox(sess, unit_kind)

    tol = HOUR_TOL if unit_kind == "hour" else 2.0
    if not sess:
        if _has_arbox_footprint(all_sessions, tid):
            # trainer normally schedules in Arbox but 0 held this month -> real red flag
            log.append(audit_entry("GHOST_SESSION", trainer_id=tid, ref=ref,
                month=smonth, expected=0, actual=inv_qty, amount=inv.get("stated_total"),
                severity="HIGH",
                note=f"invoice bills {inv_qty} {unit_kind}(s) but Arbox shows 0 held sessions this month "
                     f"(trainer HAS Arbox history — verify sessions actually happened)"))
        else:
            # off-system trainer: no Arbox baseline exists -> can only check math/rate/month
            log.append(audit_entry("NO_ARBOX_BASELINE", trainer_id=tid, ref=ref,
                month=smonth, expected=None, actual=inv_qty, amount=inv.get("stated_total"),
                severity="INFO",
                note=f"trainer not tracked in Arbox; billed {inv_qty} {unit_kind}(s) "
                     f"cannot be three-way matched — needs manager attestation"))
    elif abs(comp_qty - arbox_qty) > tol:
        sev = "WARN" if has_mixed else ("HIGH" if comp_qty > arbox_qty else "WARN")
        log.append(audit_entry("INVOICE_QTY_MISMATCH", trainer_id=tid, ref=ref,
            month=smonth, expected=arbox_qty, actual=comp_qty,
            amount=inv.get("stated_total"), severity=sev,
            note=f"invoiced {comp_qty} studio vs Arbox {arbox_qty} {unit_kind}(s) (tol {tol})"))
    else:
        log.append(audit_entry("INVOICE_MATCH", trainer_id=tid, ref=ref,
            month=smonth, expected=arbox_qty, actual=comp_qty,
            amount=inv.get("stated_total"), severity="INFO",
            note=f"qty ok ({comp_qty}≈{arbox_qty} {unit_kind})"))

    # 4) rate check: compare against the trainer's CONTRACT rate when known.
    #    Freelancer per-session rates live in aliases (contract_rate), NOT in the
    #    category session_rates table. Only flag when invoiced rate EXCEEDS the
    #    agreed contract rate (over-billing); unknown contract -> silent (needs setup).
    contract = None
    for t in aliases_cfg["trainers"]:
        if t["trainer_id"] == tid:
            contract = t.get("contract_rate")
            break
    for li in inv.get("line_items", []):
        r = li.get("rate")
        if r is None:
            continue
        if contract is None:
            log.append(audit_entry("RATE_UNSET", trainer_id=tid, ref=ref,
                month=smonth, actual=r, severity="INFO",
                note=f"no contract_rate on file for trainer — recording invoiced rate {r}; set to enable over-billing check"))
        elif r > contract + 0.01:
            log.append(audit_entry("RATE_OVER", trainer_id=tid, ref=ref,
                month=smonth, expected=contract, actual=r, severity="HIGH",
                note=f"invoiced rate {r} exceeds agreed contract rate {contract}"))

    # 5) arithmetic: qty*rate == line total; sum lines == stated_total
    computed = 0.0
    for li in inv.get("line_items", []):
        q, r, t = li.get("qty"), li.get("rate"), li.get("total")
        if q is not None and r is not None and t is not None:
            if abs(q * r - t) > 0.5:
                log.append(audit_entry("LINE_MATH_ERROR", trainer_id=tid, ref=ref,
                    month=smonth, expected=q * r, actual=t, severity="WARN",
                    note=f"{q}×{r}={q*r} but line total={t}"))
        computed += (t or 0)
    stated = inv.get("stated_total")
    if stated is not None and abs(computed - stated) > 0.5:
        log.append(audit_entry("TOTAL_MISMATCH", trainer_id=tid, ref=ref,
            month=smonth, expected=computed, actual=stated, severity="WARN",
            note=f"line sum {computed} != stated total {stated}"))


def run(invoices_json, sessions_path, out_json=None):
    aliases = load_aliases()
    pay = load_pay_matrix()
    with open(invoices_json, encoding="utf-8") as f:
        invoices = json.load(f)["invoices"]
    sessions = load_sessions(sessions_path, aliases)

    log = []
    for inv in invoices:
        audit_invoice(inv, sessions, aliases, pay, log)

    # roster-level unmapped names (ghost-trainer detection in Arbox itself)
    for raw, n in unmapped_names(sessions).items():
        log.append(audit_entry("UNMAPPED_NAME", ref="arbox_roster",
            actual=raw, amount=n, severity="INFO",
            note=f"{n} Arbox sessions under unresolved name — promote to alias table"))

    if out_json:
        with open(out_json, "w", encoding="utf-8") as f:
            json.dump(log, f, ensure_ascii=False, indent=2)
    return log


if __name__ == "__main__":
    base = os.path.join(os.path.dirname(__file__), "..")
    log = run(
        os.path.join(base, "config", "invoices_ocr.json"),
        "/sessions/beautiful-fervent-goldberg/mnt/קבצים ווקסר/דו״ח שיעורים.xlsx",
        os.path.join(base, "output", "job1_audit_log.json"),
    )
    inv_flags = [e for e in log if e["ref"] != "arbox_roster"]
    for e in inv_flags:
        print(f'[{e["severity"]:4}] {e["type"]:20} {e["ref"]:35} {e["note"]}')
    print(f'\n{len(inv_flags)} invoice findings, {len(log)-len(inv_flags)} roster notes')


# --------------------------------------------------------------- verdict -----
# Classify a set of audit entries produced for a SINGLE invoice into a write
# decision. HIGH severity on a substantive anomaly blocks auto-write; soft
# flags allow the write but mark it for the manager's eye.
_BLOCK_TYPES = {"UNMAPPED_NAME", "GHOST_SESSION", "RATE_OVER", "INVOICE_QTY_MISMATCH"}
_REVIEW_TYPES = {"NO_ARBOX_BASELINE", "RATE_UNSET", "SERVICE_MONTH_SHIFT",
                 "LINE_MATH_ERROR", "TOTAL_MISMATCH"}

def verdict_for(entries):
    """-> 'BLOCK' | 'REVIEW' | 'OK' for one invoice's audit entries."""
    v = "OK"
    for e in entries:
        t, sev = e.get("type"), e.get("severity")
        if t in _BLOCK_TYPES and sev == "HIGH":
            return "BLOCK"
        if t in _REVIEW_TYPES or sev in ("WARN", "HIGH"):
            v = "REVIEW"
    return v
