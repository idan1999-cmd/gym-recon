# Decisions

- 2026-07-29: Fix official `ledger_sync` engine, not Idan's `גרסה 2` Antigravity file.
- 2026-07-29: Month order: תאריך למאזן → memo (פרטים) → תאריך ערך.
- 2026-08-03: **Month order CHANGED (owner-approved): memo (פרטים) → תאריך למאזן → תאריך ערך.** Evidence: 105 rows lag +1 month under balance-first (₪28,651.65 on June). SUPERSEDES the 2026-07-29 decision above. Single authoritative rule lives in `core/ledger.py` `MONTH_PRIORITY` + `AGENTS.md` rule 3.
- 2026-07-29: Agent must call Python tools only; freestyle Excel is forbidden.
- 2026-07-31: Future manager Q&A (RAG-Anything-class) over recon files is **later only** — read-only chat on output/audit; never writes numbers or replaces ledger_sync.
- 2026-07-31: This product = official BvA + CLI billing for Idan; `club-finance-recon` = trainer recon/dashboard/drafts (sibling, not obsolete).
- 2026-07-31: Agent entry docs: `AGENTS.md` + `SCOPE.md` + `SKILL.md` — no freestyle money Excel.
- 2026-07-31: Product is agent judgment + deterministic money tools (not 100% scripted agent). Prefer improve engine over bypass.
- 2026-07-31: Protected knowledge files created — `docs/CLIENT_IDAN.md`, `docs/DATA_INVENTORY.md`, `docs/PRODUCT_STRATEGY.md`. Source of truth; append-only logs; agents must not rewrite.
- 2026-07-31: Strategy = service-first, SaaS-shaped. Customer does not run the agent. Web app parked until gym #2.
- 2026-07-31: OPEN — `התאמה ידנית` not found in client workbook (likely `ביאורים`); cadence is weekly not monthly; כרטסת tab choice is material (~₪240k). Ask Idan before code changes.
- 2026-08-03: Approval workbooks (`דוח מרכז לאישור מנהל`) are first-class gate inputs — validated (sheet name from `branches.json`), not just SHA-tracked.
- 2026-08-03: Input manifest keyed by absolute path, not basename — two files with the same name in different dirs must not collide.
- 2026-08-03: Unknown formulas are fail-fast (`UnknownFormulaError`), never written as 0; SUM ranges may carry a sheet qualifier (`'X'!F9:F14`).

