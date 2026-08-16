# Detailed Step-by-Step Plan — Idan Budget-vs-Actual Fixes

**Project:** `C:\Users\Amit\Documents\gym-recon`  
**Source of truth for money math:** Python tools (openpyxl), never Antigravity freestyle Excel.  
**Tracking files:** `task_plan.md`, `findings.md`, `progress.md`

---

## Context (1 minute)

Idan only used **תקציב מול ביצוע**. The file he sent (`תקציב מול ביצוע גרסה 2.xlsx`) was built by **Antigravity**, not by:

```text
python tools/ledger_sync.py --input ./input --output ./output --month 6
```

Our engine already keeps **income negative**. His draft flipped income to **positive**. Several other issues are real engine gaps (notes, YTD, rollups, memo month).

---

## Order of work (do one phase, then verify)

```text
Phase 1 strip notes
  → Phase 2 debit/credit net test
  → Phase 3 memo month
  → Phase 5 rollups (before YTD so YTD can use correct totals)
  → Phase 4 YTD columns
  → Phase 6 sign enforcement
  → Phase 7 agent lockdown + skill reinstall
  → Phase 8 full run on his תקציב תזרים + כרטסת
  → Phase 9 product/retainer doc (optional)
```

---

## Phase 1 — Strip pricing / note rows

**User pain:** “Weird January numbers at the bottom.”

### Steps
1. Open `jobs/ledger_output.py` → `build()` / `_extract_tab()`.
2. After worksheet extract, walk rows from bottom or top:
   - Keep if col A is a numeric budget code.
   - Keep if col B is a structural label: `הוצאה`, `הכנסה`, `סה"כ`, `רווח`, etc.
   - **Delete** (or clear) rows matching note patterns, e.g.:
     - דמי הרשמה, מנוי פרימיום, מנוי סטודיו, מנוי חדר כושר, מנוי נוער, מנוי חיילים
     - מחיר מנוי, שירותים נוספים, כרטיסות, `*המחירים לפני מע"מ`
3. Do **not** delete rows that have a real `סעיף` in col A.
4. Add a unit test that builds from a mini fixture with one note row → note row absent in output.

### Verify
```powershell
cd C:\Users\Amit\Documents\gym-recon
python tools/ledger_sync.py --input .\input --output .\output --month 6
# Open output\תקציב_מול_ביצוע_*.xlsx — bottom should not be pricing notes
```

### Done when
No orphan January-only note block under the P&L totals.

---

## Phase 2 — Debit + credit same סעיף

**User pain:** “Same line had charge and credit; only credit showed.”

### Steps
1. Confirm formula in `core/ledger.py` `monthly_movement`:
   - `out[key] += debit - credit` (already correct).
2. Pick one real June account from `כרטסת` with both debit and credit (mapped, not 25x bank clearing).
3. Print engine net vs manual Excel net for that account.
4. If month split is the issue → Phase 3 is the real fix.
5. If write path zeros ledger column wrongly → fix `_sync` zeroing logic (it zeros all code rows then writes movement — OK if movement is complete).
6. Test:
   ```python
   txns = [
     {"account": "18022609", "budget_month": "2026-06", "debit": 1000, "credit": 200},
   ]
   # expect net 800 on mapped budget code
   ```

### Verify
Regression test green + one real ledger account matches.

### Done when
Documented proof net = d−c; any remaining gap is month attribution (Phase 3).

---

## Phase 3 — Month field + memo (הערות)

**User pain:** “מאזן or ערך? Can it use notes?”

### Current behavior
1. `תאריך למאזן`
2. else `תאריך ערך`
3. else other cells  
**Never** `פרטים`.

### Steps
1. In `core/common.py` add `parse_memo_month(text) -> "YYYY-MM" | None`:
   - Patterns: `5/26`, `05/2026`, `5.26`, `יוני 2026` (optional later).
2. In `parse_ledger` row loop, read memo column (`פרטים` if present).
3. Priority (recommended default):
   1. `תאריך למאזן` if present
   2. else memo month if present  
   3. else `תאריך ערך`  
   **Ask Idan once:** if both מאזן and memo disagree, which wins? Plan default = **מאזן wins**, memo only fills gaps — safer. Optional flag `prefer_memo_over_balance_date=true` if he insists.
4. When memo used: `audit_log` type `LEDGER_MONTH_FROM_MEMO`.
5. Document in `SKILL.md` under ledger rules.
6. Tests: balance empty + memo `5/26` → 2026-05; balance June + memo May → stays June (if default).

### Verify
```powershell
python -c "from common import parse_memo_month; print(parse_memo_month('5/26 הכנסות מנויים'))"
python tests/test_resilience.py
```

### Done when
Memo month implemented, audited, tested; SKILL documents priority.

---

## Phase 4 — YTD (start of year → current month)

**User pain:** “Need budget vs actual from year start to now, income and expense, per line.”

### Steps
1. In `ledger_output.build`, after target-month two-layer sync:
   - For each code row, sum display actuals for months 1..N (N = `--month`).
   - Sum budget columns for 1..N.
2. Write/update headers:
   - `סה"כ תקציב 1-N/26`
   - `סה"כ ביצוע 1-N/26`
   - `הפרש YTD` or fill existing `ביצוע מול תקציב` only if template expects it.
3. Prefer **reusing existing YTD columns** if present in template (`1-5/26`) and **extend to N** rather than inventing a second layout.
4. Income lines stay negative in YTD sum; expenses positive.
5. Do not overwrite `התאמה ידנית` for any month.

### Verify
Pick code 80001: YTD actual = Jan+…+June display values.

### Done when
Both club and pilates sheets have correct YTD for target month.

---

## Phase 5 — Fix סה"כ הכנסות / סה"כ הוצאות

**User pain:** “Totals don’t sum the right data.”

### Steps
1. Replace `_find_rollup_rows` heuristics with:
   - Find row labels containing `סה"כ הכנסות`, `סה"כ הוצאות`, `רווח` / `הפסד`.
   - Or compute purely in Python and write those cells by label search.
2. Income total = sum of rows with codes in income set (80xxx, 81xxx, … from account_map or prefix).
3. Expense total = sum of expense code rows.
4. Operating P&L = income_total + expense_total (with signs).
5. Apply to target month display column **and** YTD columns if present.
6. Tests for club + pilates fixtures.

### Verify
```text
סה"כ הכנסות == sum(income lines)
סה"כ הוצאות == sum(expense lines)
```

### Done when
Manual Excel SUM matches engine totals for June.

---

## Phase 6 — Sign convention (boss)

**User pain:** “Income negative, expenses positive.”

### Steps
1. After writing actuals, for each income code row: if value > 0 → flip to −value, log `SIGN_FLIPPED`.
2. Optional: expense if value < 0 and not a credit-normal account → flag for review (don’t auto-flip blindly).
3. Assert in validate tool: income sample codes ≤ 0.
4. Document in SKILL + FRIEND_README.

### Verify
Inject positive income mock → output negative.

### Done when
Engine always ships boss convention; independent of Antigravity.

---

## Phase 7 — Agent lockdown

**User pain / your product risk:** Agent rebuilds Excel → bugs.

### Steps
1. Edit `SKILL.md` hard rules:
   - For תקציב מול ביצוע: **only** `python tools/ledger_sync.py …`
   - Forbidden: openpyxl hand-build, “create new sheet from scratch”, reinventing columns.
2. Same in `CLAUDE.md` + `friend_install/FRIEND_README.txt`.
3. Add footer note on output sheet: `written by gym-recon ledger_sync`.
4. Copy skill:
   ```powershell
   Copy-Item SKILL.md $env:USERPROFILE\.agents\skills\gym-recon\SKILL.md -Force
   Copy-Item SKILL.md $env:USERPROFILE\.claude\skills\gym-recon\SKILL.md -Force
   ```
5. Tell Idan: after update, always open **`output\תקציב_מול_ביצוע_*.xlsx`**, not agent-invented names.

### Done when
Skill text is unambiguous; friend pack updated.

---

## Phase 8 — E2E with his files

### Steps
1. Copy into `input/`:
   - `תקציב תזרים 2026 (2).xlsx` (rename/keep; preflight resolves by content)
   - Latest `כרטסת.xlsx`
2. Run:
   ```powershell
   python tools/preflight.py --input .\input
   python tools/ledger_sync.py --input .\input --output .\output --month 6
   python tools/validate.py --output .\output
   python tests\test_acceptance.py
   python tests\test_resilience.py
   ```
3. Manually open output and walk Idan’s checklist 1–6.
4. Update `progress.md` with PASS/FAIL per point.

### Done when
You can send him the official output + short Hebrew explanation of what changed.

---

## Phase 9 — Retainer / product (docs)

### Steps
1. Write `docs/PRODUCT_RETAINER.md`:
   - Tier A: you run monthly recon for him (ops retainer)
   - Tier B: friend_install + support SLA
   - Tier C: web upload (same Python backend)
2. Rule: every tier runs **same tools**; agent only orchestrates.

---

## Risk / do-not-break

| Rule | Why |
|------|-----|
| Never write `התאמה ידנית` | Overwrite safety |
| openpyxl only | Product policy |
| Hebrew keys exact | Matching |
| Reuse `jobs/` + `core/` | Don’t rewrite money engine |

---

## Suggested reply to Idan (after fixes)

Hebrew short:
- עובדים על קובץ המנוע הרשמי (`תקציב_מול_ביצוע_…`), לא על גרסה שהסוכן בנה ידנית.
- סימני הכנסה שליליים לפי בקשת הבוס.
- חודש: מאזן, ואם חסר — מהערות; שתי שכבות ביצוע נשמרות.
- YTD + תיקוני סה"כ + ניקוי שורות הערות בתחתית.

---

## How to resume next session

```powershell
cd C:\Users\Amit\Documents\gym-recon
```

Then: “continue task_plan Phase 1” — agent should read `task_plan.md` + `findings.md` + query graphify first.
