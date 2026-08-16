# Builder Log — gym-recon

## How this project works in 2 minutes

`gym-recon` is the automated monthly finance and billing engine for **אריאל פיט & ספא בע"מ (A+ Street Mall)** (covering the Main Gym / Club and the Pilates Studio). 
Every month, the gym receives raw input files: an accounting general ledger (`כרטסת`), payroll reports from Hilan (`חילנט / פרויקטים ספא`), class schedules from Arbox, trainer freelance invoice PDFs, and supplier invoice PDFs. 
The system takes these raw inputs, performs automated OCR and three-way reconciliation (comparing invoice vs. schedule vs. agreed rate table), and deterministically produces the official financial deliverables:
1. **תקציב מול ביצוע (Budget vs. Actual):** Syncs real accounting ledger transactions into the official budget workbook without touching manual overrides or formulas.
2. **חיוב יזם & דוח מרכז לאישור מנהל (Trainer & Staff Billing):** Computes monthly charges for the property owner/developer across shifts, reception, personal training, studio classes, management fees, and sales commissions.
3. **ספקים לאישור מנהל (Supplier Payment Pack):** Matches supplier invoices against vendor terms (+30 / +60 days) and generates the manager approval workbook.
4. **דגלים (Audit & Flags):** Automatically flags rate mismatches, missing trainer receipts, unknown vendors, or hours variance so management can review exceptions without doing math by hand.

---

## 2026-08-16 — Baseline System Map, Self-Documentation System & Workflow Alignment

- **What changed:** 
  - Established persistent self-documentation rules in `AGENTS.md` and `CLAUDE.md`.
  - Created `docs/BUILDER_LOG.md` (this living diary) and `docs/SYSTEM_MAP.md` (the end-to-end architecture and relationship map).
  - Documented all current workflows (preflight, Gemini OCR, trainer billing, ledger sync, supplier pack, pipeline orchestrator) and spreadsheets.
  - Analyzed and mapped the operator's business rules for Club and Pilates billing (reception hours, instructor shifts, overtime tiers, travel allowance, Arbox cross-validation, and management fees).
- **Why (what Idan asked for, in his words if given):** 
  - *"Set up a self-updating documentation system. From this moment on, every change you make to this project must be documented in plain English, committed to git, and reflected in a living system map, so the owner always knows what exists, what changed, and how the pieces connect."*
  - *"Explain to me briefly, shortly, is it implemented that way in the system or not implemented that way in the system, and if we should make any changes or modifications as well."*
- **What it touches:** 
  - `AGENTS.md`, `CLAUDE.md`, `docs/BUILDER_LOG.md`, `docs/SYSTEM_MAP.md`.
- **How it was verified:** 
  - Full test suite execution: `pytest` passed (44 tests), `test_idan_fixes.py` passed (27 tests), `test_resilience.py` passed (11 tests), `test_acceptance.py` passed (54 tests).
  - Git status inspected and verified clean with zero secrets.
- **Watch out:** 
  - Several open questions and workflow nuances identified during operator alignment (such as the exact travel allowance rule, 8% National Insurance on sales commissions, and overtime calculations on reception/instructors) are marked with `CONFIRM WITH IDAN:` in `docs/SYSTEM_MAP.md`.
