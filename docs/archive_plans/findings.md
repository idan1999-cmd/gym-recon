# Findings — Idan Feedback (Budget vs Actual)

## Goal of research
Explain Idan's 6 points and map each to gym-recon code / Antigravity behavior.

## Files examined

### From Downloads (Idan / recent)
| File | Size | Role |
|------|------|------|
| `תקציב מול ביצוע גרסה 2.xlsx` | ~27KB | **His Antigravity output** — 2 sheets מועדון + פילאטיס; layout תקציב/ביצוע/הפרש per month; **income positive** |
| `תקציב תזרים 2026 (1).xlsx` / `(2).xlsx` | ~180KB | Current source budget workbook (he says this is the up-to-date one) |
| `DRAFT_תקציב_מול_ביצוע_2026-06.xlsx` (+1) | ~135KB | **Not** real BvA rebuild — same multi-tab cashflow/suppliers structure as source budget dump |
| `כרטסת.xlsx` / `כרטסת עמית.xlsx` | ~344KB | Ledger source (tabs 7.6, 29.6, 6.7, 13.7) |

### Official engine
| File | Role |
|------|------|
| `output/תקציב_מול_ביצוע_חדר_כושר.xlsx` | Engine Job 3 club output — two-layer June; **income negative** |
| `output/תקציב_מול_ביצוע_פילאטיס.xlsx` | Engine Job 3 pilates |
| `jobs/ledger_output.py` | Extract tab + two-layer + rollups |
| `core/ledger.py` | Parse ledger; `movement = debit − credit` |
| `core/common.py` | `month_key` from dates only (no memo) |

## Critical finding
**Idan did not ship our engine file.**  
`גרסה 2` is a freestyle Antigravity rebuild. Compare Jan 80001:
- Source / engine: **−140370.5**
- גרסה 2: **+140370.35**

Boss wants income **negative** — our engine already does that; his draft inverted it.

## Point-by-point

### 1. Strange January numbers at bottom
- Source tab includes **pricing / note rows** without budget codes (דמי הרשמה, מנוי סטודיו, מחיר ממוצע…).
- `_extract_tab` copies **entire** sheet; only coded rows get ledger writes.
- Notes keep partial/old January-looking values → "where did January come from?"
- **Fix:** strip note rows after extract (Phase 1).

### 2. Debit + credit same section; only credit visible?
- Code nets correctly: `Σ debit − Σ credit` per account per month (`ledger.py`).
- Likely causes:
  a) Debit and credit land in **different months** (date fields), so one month shows only one side.
  b) Mapped expense lines show **0** in June when no `180…` movement that month (looks empty, not "credit only").
  c) Antigravity sheet may have mis-aggregated.
- Need one concrete סעיף example from him if still wrong after memo-month fix.
- **Fix:** Phase 2 + 3 + regression test.

### 3. Date field: מאזן vs ערך vs notes
- Current: **`תאריך למאזן` first**, else **`תאריך ערך`**, else scan cells (`parse_ledger`).
- **`פרטים` memo is ignored.**
- Handoff already noted memos like `"5/26 הכנסות מנויים"`.
- **Fix:** optional memo month parse with audit (Phase 3).

### 4. Missing YTD (start of year → current)
- Sheet has frozen **`סה"כ … 1-5/26`** style columns from template.
- Engine only **overwrites target month** two-layer block; does not recompute live YTD through current month.
- **Fix:** compute YTD columns for months 1..N (Phase 4).

### 5. Total income / expense rows wrong
- `_fill_rollup_totals` / `_find_rollup_rows` use **layout heuristics** (blank code + numeric ref row, label סה"כ).
- Value-based writes (not Excel formulas) → easy to drift when layout differs.
- Engine June grand can look wrong relative to line sum.
- **Fix:** code-prefix + explicit labels (Phase 5).

### 6. Income negative / expense positive
- Boss preference = **engine design already**.
- גרסה 2 flipped income to positive.
- **Fix:** enforce sign in engine + agent lockdown (Phases 6–7).

## Antigravity / product
- Amit's email sold: install Antigravity + clone repo + talk to agent.
- Without hard skill rules, agent **rebuilds Excel** instead of calling `tools/ledger_sync.py`.
- Retainer path: same Python tools behind skill → later web upload API; never freestyle money Excel.

## Graphify
- Built at `graphify-out/`: 497 nodes, 651 edges, 41 communities.
- Next session: `cd` to project then `graphify query` first.

## Open questions for Idan (if needed)
1. One example line for point 2 (account code + expected debit/credit/net).
2. Confirm: memo month should **override** מאזן when both present, or only when מאזן empty?
3. YTD through which month now (June only vs rolling previous calendar month)?
