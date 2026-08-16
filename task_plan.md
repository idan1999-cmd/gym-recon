# Task Plan: Fix Idan's 6 Budget-vs-Actual Issues

## Goal
Make `ledger_sync` produce manager-ready תקציב מול ביצוע that matches Idan's 6 feedback points, and stop Antigravity from freestyling Excel.

## Next Step
Implement Phase 1 (strip non-budget note rows) after plan approval is already given via "continue".

## Current Phase
Complete (phases 1–8); optional Phase 9 product doc

## Phases

### Phase 0: Baseline lock (done research)
- [x] Confirm Idan files in Downloads
- [x] Map each of 6 points to code
- [x] Confirm `גרסה 2` ≠ official engine output
- [x] Graphify project for future sessions
- **Status:** complete

### Phase 1: Strip non-budget / pricing note rows
- [ ] Identify note-label patterns (דמי הרשמה, מנוי סטודיו, מחיר ממוצע, etc.)
- [ ] In `jobs/ledger_output.py` after tab extract: drop rows with no numeric סעיף that match note labels
- [ ] Keep real rollup rows (סה"כ, הוצאה, רווח)
- [ ] Re-run ledger_sync on sample input; bottom of sheet has no orphan January notes
- **Status:** pending
- **Files:** `jobs/ledger_output.py`, `tests/test_acceptance.py` or new test
- **Validate:** open output xlsx → last data block is totals, not pricing notes

### Phase 2: Debit + credit same account (net correctness)
- [ ] Re-read `core/ledger.py` `monthly_movement` (already debit−credit)
- [ ] Find real June example from Idan's ledger where both sides exist on mapped budget accounts
- [ ] If split is month-bucketing only → fix via Phase 3
- [ ] If write path zeros one side → fix write path
- [ ] Add regression test: account with debit+credit same month → net = d−c
- **Status:** pending
- **Files:** `core/ledger.py`, `tests/test_resilience.py`
- **Validate:** unit test + one real account from כרטסת

### Phase 3: Month attribution (מאזן / ערך / הערות)
- [ ] Document current priority in code comments + SKILL.md
- [ ] Add `parse_memo_month(פרטים)` in `core/common.py` (regex `d/m`, `d.m`, `m/yy`)
- [ ] In `parse_ledger`: priority = תאריך למאזן → memo month if present → תאריך ערך
- [ ] Optional config flag `prefer_memo_month: true` in account_map or branches
- [ ] Audit entry `LEDGER_MONTH_FROM_MEMO` when memo wins
- [ ] Tests for יעלה-style and "5/26 הכנסות" memo cases
- **Status:** pending
- **Files:** `core/common.py`, `core/ledger.py`, `SKILL.md`, tests
- **Validate:** memo "5/26" + balance-date June → month 2026-05

### Phase 4: YTD budget vs actual (1 → current month)
- [ ] After month sync, add/update columns:
  - `סה"כ תקציב 1-N/26`
  - `סה"כ ביצוע 1-N/26`
  - `הפרש YTD` (or reuse ביצוע מול תקציב if layout allows)
- [ ] Per line: income and expense separately
- [ ] Dynamic N = target month number
- [ ] Do not overwrite manager manual adjustments for past months
- **Status:** pending
- **Files:** `jobs/ledger_output.py`, `tools/ledger_sync.py`
- **Validate:** YTD for 80001 equals sum of Jan–June display actuals

### Phase 5: Fix סה"כ הכנסות / הוצאות rollups
- [ ] Replace brittle blank-row heuristic with label + code-prefix rules
- [ ] Income sum = codes 80xxx/81xxx (and other income codes in map)
- [ ] Expense sum = expense codes between הוצאה header and grand total
- [ ] רווח/הפסד = income_total + expense_total (sign convention preserved)
- [ ] Tests for both club and pilates tabs
- **Status:** pending
- **Files:** `jobs/ledger_output.py`, tests
- **Validate:** rollup cells equal sum of constituent lines for June

### Phase 6: Enforce income negative / expense positive
- [ ] After write: income codes must be ≤ 0; expenses ≥ 0 (or document exceptions)
- [ ] If positive income found, flip sign + `SIGN_FLIPPED` audit
- [ ] Document in SKILL: boss convention = income negative
- [ ] Never rely on Antigravity freestyle for signs
- **Status:** pending
- **Files:** `jobs/ledger_output.py`, `SKILL.md`, tests
- **Validate:** mock positive income → output negative + flag

### Phase 7: Agent lockdown (Antigravity / OpenCode)
- [ ] Update `SKILL.md`: MUST call `tools/ledger_sync.py`; MUST NOT rebuild Excel by hand
- [ ] Update `friend_install/FRIEND_README.txt` + `CLAUDE.md`
- [ ] Add short `AGENTS.md` or section: money path = Python tools only
- [ ] Optional signature cell / footer: "written by gym-recon ledger_sync vX"
- [ ] Re-copy skill to `~/.agents/skills/gym-recon` and `~/.claude/skills/gym-recon`
- **Status:** pending
- **Files:** `SKILL.md`, `CLAUDE.md`, `friend_install/*`
- **Validate:** skill text contains explicit "do not freestyle Excel"

### Phase 8: End-to-end verify with Idan fixtures
- [ ] Copy latest `תקציב תזרים 2026 (2).xlsx` + `כרטסת` into `input/`
- [ ] Run `python tools/ledger_sync.py --input input --output output --month 6`
- [ ] Diff against `גרסה 2` conceptually (not cell-identical — layout differs)
- [ ] Checklist Idan's 6 points all addressed in official output
- [ ] Run `tests/test_acceptance.py` + `tests/test_resilience.py`
- **Status:** pending
- **Validate:** all tests green; manual open of output xlsx

### Phase 9: Product / retainer note (docs only)
- [ ] Write `docs/PRODUCT_RETAINER.md`: local skill → managed service → web upload
- [ ] Pricing sketch: monthly recon retainer vs SaaS later
- [ ] Hard rule: product still runs same Python tools (no agent freestyle)
- **Status:** pending
- **Files:** `docs/PRODUCT_RETAINER.md`

## Decisions Made
| Decision | Rationale |
|----------|-----------|
| Fix engine, not גרסה 2 | גרסה 2 is Antigravity freestyle; source of truth is ledger_sync |
| Memo month is opt-in priority after מאזן | Idan said notes are messy but real |
| YTD is new columns, not only 1-5 freeze | He wants current through target month |
| Agent lockdown is a deliverable | Prevents recurrence of freestyle bugs |

## Errors Encountered
| Error | Attempt | Resolution |
|-------|---------|------------|
| Plan write blocked in plan mode | 1 | Wait for build mode; write task_plan.md |
| Hebrew filenames garbled in PowerShell | 1 | Use Python listdir/openpyxl |

## Done when
1. All 6 Idan points fixed or explicitly deferred with reason
2. Tests pass
3. Skill forbids freestyle Excel
4. findings.md + progress.md updated
