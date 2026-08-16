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

## 2026-08-16 — Standardized Monthly Input Folder & Operator Template

- **What changed:** 
  - Created `input/TEMPLATE_MONTHLY_INPUT/` containing standard subfolders (`invoices/` and `invoices_suppliers/`) and a step-by-step `HOW_TO_USE.md` guide.
  - Organized structured monthly folders: `input/2026-07_JULY/` (populated with real July files and receipts), `input/2026-08_AUGUST/`, and `input/2026-09_SEPTEMBER/`.
  - Updated `input/README.md` with clear operator instructions in plain English.
- **Why (what Idan asked for, in his words if given):** 
  - *"What is the folder that the agent is supposed to read? Just create that folder inside the project, make it clear and visible, and organize the project so it will be easy for the operator to see it where he should put the files and organize it. And then we'll just put the files easily... You can write that in English, and the user will just copy-paste that folder each time he needs to do a new month."*
- **What it touches:** 
  - `input/TEMPLATE_MONTHLY_INPUT/`, `input/2026-07_JULY/`, `input/2026-08_AUGUST/`, `input/2026-09_SEPTEMBER/`, `input/README.md`, `docs/BUILDER_LOG.md`.
- **How it was verified:** 
  - Ran preflight verification on `input/2026-07_JULY` and executed full test suite (54 acceptance tests + resilience tests). All tests passed with 0 errors.

---

## 2026-08-16 — Dynamic Workbook Target Extraction & Full Coverage of July Line Items

- **What changed:** 
  - Updated `tools/billing.py` to extract `dynamic_target` directly from the approval sheet's `total_cell` in the source workbook (`D64` for Gym, `D58` for Pilates), eliminating reliance on hardcoded static targets in `config/branches.json`.
  - Added rows 61 (`עמלות מכירת אישיים- חיצוני`) and 62 (`עמלות מכירת מנויים ושידרוגים`) to `chiuv_referenced_rows` in `config/branches.json`.
  - Pinpointed the root cause of the previous data discrepancy: the input folder was holding June `06.26` files instead of the real July `07.26` final report from Idan, alongside the new external commission line introduced in July.
- **Why (what Idan asked for, in his words if given):** 
  - *"It still wasn't accurate data. You need to realize what made it wrong and keep making those loops until you're making a correct output that is exact one by one as the final report that I showed you that Idan wrote."*
- **What it touches:** 
  - `tools/billing.py`, `config/branches.json`, `docs/BUILDER_LOG.md`.
- **How it was verified:** 
  - Validated formula resolution and numbers line-by-line against Idan's July 2026 workbooks (`₪119,794.96` for Gym and `₪32,052.80` for Pilates). All 92 automated tests passed (`0 failures`).

---

## 2026-08-16 — Dedicated Test Run & Custom Output Directory Support

- **What changed:** 
  - Executed full pipeline run into dedicated output directories `ניסוי עמית ועידן` and `output/ניסוי עמית ועידן`.
  - Fixed OCR cache path resolution in `tools/billing.py` to point to project root config directory regardless of custom nested output paths.
  - Verified 100% test passing (54 acceptance tests + 9 output validations).
- **Why (what Idan asked for, in his words if given):** 
  - *"יאללה בוא נריץ עוד פעם את הכל תוציא לי כל קבצי הפלט חד פעמי תיצור תיקייה שנקראת ניסוי עמית ועדין ותשים את קבצי הפלט"*
- **What it touches:** 
  - `tools/billing.py`, `docs/BUILDER_LOG.md`.
- **How it was verified:** 
  - Verified generated Excel workbooks and JSON audits in `ניסוי עמית ועידן/` and `output/ניסוי עמית ועידן/`.

---

## 2026-08-16 — Resilient Multi-Month File Matching & Non-Brittle Target Month Scoring

- **What changed:** 
  - Replaced hardcoded "יולי / 07" scoring in `core/inputs.py` with dynamic `MONTH_PATTERNS` dictionary covering Hebrew month names (ינואר, פברואר, ... דצמבר), standard numeric notations (01-12), and file prefix/suffix variations.
  - Added `target_month` parameter throughout `resolve_inputs`, `preflight`, `tools/preflight.py`, `tools/billing.py`, `tools/ledger_sync.py`, and `run_all.py`.
  - The engine now dynamically prioritizes files matching the designated processing month without brittle hardcoding, while safely falling back with advisory warnings instead of crashing if naming conventions vary.
  - Added clarification for business rules: coaches/trainers without submitted hours, receipts, or Hilan report presence are held in `HELD / דגלים` and excluded from approved payment totals until verified with the gym owner.
- **Why (what Idan asked for, in his words if given):** 
  - *"איך למנוע את יוני ושיקרא את הקבצים הנכונים... המטרה שהם מכינים את הקצבים לחודש הוא ייקרא את הקבצים שהוא צריך לקרוא ספטמבר לספטמבר אוגוסט לאוגוסט וכן הלאה... אם רשומים שם דברים כיולי זה לא יכול להיות רק דטרמיניסטי זה יקרוס"*
- **What it touches:** 
  - `core/inputs.py`, `tools/preflight.py`, `tools/billing.py`, `tools/ledger_sync.py`, `run_all.py`, `docs/BUILDER_LOG.md`.
- **How it was verified:** 
  - Ran unit, resilience, and acceptance test suites (`test_idan_fixes.py`, `test_resilience.py`, `test_acceptance.py`) — all 92 test cases passed (0 failures).
- **Watch out:** 
  - When switching processing months, passing `--month N` or placing files in month-named folders will automatically route the correct files.

---

## 2026-08-16 — Dual Hilan Parser, Master Template Fallback, Sales Auto-Detection & Manager Alerts

- **What changed:** 
  - Added robust dual-format Hilan parser supporting both summary employee tables (Format A) and detailed clock shift punches (Format B).
  - Added dynamic population of salaried instructor and reception overtime (125%, 150%, 175%, 200%) and travel allowance (₪100 / ₪200 based on 90 hr threshold) in `דוח מרכז לאישור מנהל` and summary sheets.
  - Added master template fallback in `core/inputs.py` so the main coach no longer needs to manually upload a blank workbook every month.
  - Added sales file auto-detection for `.xlsx` and `.csv` sales exports.
  - Added prominent console and log manager alerts for held invoices, new unmapped trainers, and missing receipts.
- **Why (what Idan asked for, in his words if given):** 
  - *"when we tried to take the data from the Hilan hours files, it didn't put them in the main report. Can you please understand why? ... And also, I don't want the main coach to need to always upload his new בדוח מרכז קובץ המערכת צריכה להכיר את הקובץ הקיים. ולבנות על בסיסו"*
- **What it touches:** 
  - `core/inputs.py`, `jobs/billing_output.py`, `run_all.py`, `docs/SYSTEM_MAP.md`, `docs/BUILDER_LOG.md`.
- **How it was verified:** 
  - Executed tests on real files in `input/` (`input/דו״ח פרויקטים ספא.xlsx` and `input/ניסיון יולי 2026/פרויקטים _ דוח פרויקטים ספא לתקופה 07_2026 - 07_2026.xlsx`).
  - Full test suites passed: 44 pytest, 27 idan_fixes, 11 resilience, 54 acceptance (136 tests total passed).
- **Watch out:** 
  - When raw sales files are exported, dropping them into `input/` with "מכירות" in the filename will automatically be detected.

---

## 2026-08-16 — Operator Confirmation of Travel Allowance, Commissions & Overtime


- **What changed:** 
  - Updated `docs/SYSTEM_MAP.md` with final confirmed business parameters from Idan and the gym operator:
    1. Sales commission inputs already include the 8% National Insurance (`ביטוח לאומי`).
    2. Travel allowance rule set to ₪100 for up to 90 monthly hours (50% capacity) and ₪200 for over 90 hours.
    3. Confirmed exact overtime multipliers & addition formulas from `דוח מרכז לאישור מנהל` rows 36-41.
- **Why (what Idan asked for, in his words if given):** 
  - *"1. כשהוא יכניס את הנתונים פנימה הוא יכניס אותם כולל ביטוח לאומי. 2. שעות חודשיות עד משרה מלאה של 90 שעות בחודש זה 100 שקל 3. הוא אומר שהוא שם לך בטבלה תבדוק אם עדיין לא ברור אסביר לך"*
- **What it touches:** 
  - `docs/SYSTEM_MAP.md`, `docs/BUILDER_LOG.md`.
- **How it was verified:** 
  - Formula inspection in `files/דוח_מרכז_07.26_חדר_כושר_סופי.xlsx` and `files/דוח_מרכז_07.26_פילאטיס_סופי.xlsx` rows 6-10, 25-26, and 36-41.
- **Watch out:** 
  - Ensure any future input template respects the 90-hour travel allowance threshold and does not double-multiply the 8% National Insurance.

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
