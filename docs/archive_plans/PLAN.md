# Gym-Recon — Improvement Plan (paste this into a NEW Claude session)

You are continuing a built project: a **Gym Financial Reconciliation & Invoice-Ingestion Engine**
for אריאל פיט & ספא בע"מ (gym=חדר כושר / Pilates=פילאטיס). The full code lives in the project
folder `gym_recon_v2/` (has SKILL.md + CLAUDE.md — READ CLAUDE.md FIRST, it explains everything).
Do NOT rebuild from scratch. Only implement the two changes below, then re-run and verify.

## Context you need (all in CLAUDE.md, summarized)
- Two jobs: (1) Trainer Billing → workbook per branch with sheets חיוב יזם / דוח מרכז לאישור מנהל /
  חילנט / ריכוז שעות + a דגלים flags sheet. (2) Ledger Sync: כרטסת → תקציב מול ביצוע, two-layer
  overwrite-safe, values not formulas.
- Budget file per branch: `תקציב_מול_ביצוע_חדר_כושר.xlsx`, `תקציב_מול_ביצוע_פילאטיס.xlsx`.
- FILE TOOLS CANNOT REACH /tmp — use bash heredoc for /tmp; project folder is reachable normally.
- Run: `python3 run_all.py --input input --output output --month 2026-06`
- Verify: `python3 tests/test_acceptance.py` (must stay green), plus the new checks below.

---

## CHANGE 1 — Fix the broken June total formula (BOTH budget files)

### Bug (confirmed)
When Ledger Sync writes June, it splits June into 3 columns:
N=`יוני ביצוע (כרטסת)`, O=`יוני התאמה ידנית`, P=`יוני - ביצוע` (display).
Per-line P cells are filled, BUT the three roll-up cells in column P are EMPTY, so the
bottom line shows blank. Original template had these for every prior month (cols D,F,H,J,L).

### Fix — in the display column P for the June block, write (matching template pattern):
- Income subtotal row 10:  `P10 = =SUM(P5:P9)`
- Expense total   row 47:  `P47 = =SUM(P12:P46)`
- Grand total     row 48:  `P48 = =P47+P10`
- Variance cell (ביצוע מול תקציב, col Z): ensure `Z47 = =Y47 - X47` style still resolves for June
  if a June-variance column exists; if the sheet's variance references the single ביצוע column,
  point it at P.
Row indices above are for חדר כושר. For פילאטיס the layout differs — DON'T hardcode; detect the
rows dynamically: income rows = contiguous income block under the income header; expense block =
rows between the הוצאה header and the הוצאות/סה"כ total; find the total rows by the Hebrew labels
`הוצאות` and `סה"כ`. Read branches.json — it already stores per-branch total_cell/detail rows;
reuse that instead of guessing.

### Important
- Write these as REAL formulas (=SUM...) OR as computed VALUES — user viewers don't all compute,
  so prefer: write the formula AND set the cached value (openpyxl can't compute; instead compute
  the number in python and write it as a value, matching how the rest of the sheet is already
  value-based). Keep consistent with existing cells: the sheet is currently value-based, so write
  P10/P47/P48 as NUMERIC VALUES computed in python (sum of the P column ranges). This is the safe
  choice — no blank cells in non-computing viewers.
- Keep red-negative / green-variance formatting already applied.
- Re-run and assert P48 (both files) is non-empty and equals P47+P10.

---

## CHANGE 2 — Trainer-data gate for דוח מרכז לאישור מנהל (human-in-the-loop)

Goal: preserve the existing sheet format and all OTHER trainers' rows; only inject validated
trainers; gate unknowns and missing-receipts for the manager. User's exact intent:
"save amounts to a file → check if we already have data on that trainer → if not, manager reads the
PDF and adds the trainer, THEN it goes into Excel → if no receipt found, just mark/notify."

### Implement this pipeline (in jobs/billing_output.py + jobs/job_billing.py):

1. **Amounts cache first.** Before touching Excel, write ALL validated amounts to
   `output/trainer_amounts_<branch>.json`: list of
   {raw_name, trainer_id|null, tax_id, category, amount, source_invoice, service_month}.

2. **Known vs unknown.** For each amount, resolve via trainer_aliases.json
   (exact→normalized→fuzzy≥88):
   - KNOWN → inject the amount into that trainer's EXISTING row in דוח מרכז, in place.
     Do not clear or reformat any other row (KEEP format, inject only mine).
   - UNKNOWN → do NOT write to Excel. Add to `pending_trainers` with the fuzzy best-guess +
     proposal (name, tax id, branch, category, rate). Surface in דגלים under
     "מאמנים לא מזוהים — נדרש אישור ידני (קרא PDF והוסף למאגר)".

3. **Missing receipt.** If a trainer is EXPECTED (has a row / prior amount) but no invoice was
   found this run → don't fabricate. Mark in דגלים under "חסרות קבלות" with the trainer name.

4. **Re-run only injects newly-confirmed trainers.** Once the manager adds an unknown trainer to
   trainer_aliases.json, the next run auto-injects them (no code change needed — resolution now
   succeeds).

### Acceptance checks to add to tests/test_acceptance.py
- §7 trainer gate: a known trainer's amount lands in their existing row; row count of דוח מרכז
  unchanged (no rows added/removed); an unknown trainer is NOT written to Excel but appears in
  pending_trainers with a proposal; a trainer with a row but no invoice appears in "חסרות קבלות".
- trainer_amounts_<branch>.json exists and contains every validated amount.

---

## Deliverables
1. Both budget files with working June totals (P10/P47/P48 filled).
2. Both billing workbooks with the trainer-gate behavior + new דגלים sections.
3. trainer_amounts_<branch>.json per branch.
4. All acceptance tests green (existing 16 + new §7).
Stage to the project output/ folder and present the files. Talk to me in English to save tokens.

## Gotchas (learned, don't repeat)
- /tmp is invisible to Read/Write/Edit — use bash heredoc there.
- חיוב יזם is a formula VIEW over דוח מרכז — resolve to VALUES so cells aren't blank.
- Compute totals from a value-snapshot BEFORE trimming helper tabs (deleted tabs → formula refs
  become 0 and corrupt the total).
- Income is negative in the ledger. 180+code=Club, 181+code=Pilates.
- New/unknown trainer = HOLD, never silently placed.
