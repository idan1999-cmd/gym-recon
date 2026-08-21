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

## 2026-08-21 — Executive Design Polish, Full Layer Subtotals & Conditional Variance Highlighting

- **What changed:** 
  - Added subtotal calculations (`סה"כ הכנסות`, `סה"כ הוצאות`, `רווח/הפסד (EBITDA)`) across **all three layers**: `ביצוע (כרטסת)` (lc), `התאמה ידנית` (mc), and `- ביצוע` (dc), so subtotals are never blank or missing on any column.
  - Implemented **Conditional Variance Highlighting (הדגשת חריגות תקציב בצבעים בולטים)**:
    - **Expense overruns / Income shortfalls:** Highlighted in soft rose/red fill (`#FFEBEE`) with bold red text (`#C00000`).
    - **Expense savings / Income targets met:** Highlighted in soft light green fill (`#E8F5E9`) with dark green text (`#2E7D32`).
  - Eliminated the unstyled "white gap" in `jobs/ledger_output.py`: header backgrounds, fonts, cell fills, borders, and alignments are now fully propagated from existing table columns.
  - Implemented **Freeze Panes (קיבוע חלונות)** at `C3`: columns A & B (`סעיף תקציבי`, `שם סעיף`) and header rows 1 & 2 remain pinned while scrolling.
  - Implemented dynamic column auto-widths (`>= 16` for numeric columns, `14` for code, `34` for labels) and enforced clean accounting number formatting (`#,##0;[Red]-#,##0;"-"`).
- **Why (what Idan asked for, in his words if given):** 
  - *"שים לב ששכחת להוסיף לי עמודת סה״כ לעמודה של הכרטסת הידנית כדי שאוכל לחשב הכל. מה דעתך להוסיף לי גם התייחסות בצבעים בולטים לסעיפים שבהם אני חורג/לא עומד בתקציב? תריץ שוב אחרי התיקון ותמחק דו״חות קודמים."*
- **What it touches:** 
  - `jobs/ledger_output.py`, `output/תקציב_מול_ביצוע_חדר_כושר.xlsx`, `output/תקציב_מול_ביצוע_פילאטיס.xlsx`, `docs/BUILDER_LOG.md`.
- **How it was verified:** 
  - Verified totals across all columns (`Row 12`, `Row 49`, `Row 50` on Club; `Row 14`, `Row 37`, `Row 38` on Pilates).
  - Verified variance highlighting on over-budget items.
  - Executed all 94 automated tests (0 failures).

---

## 2026-08-16 — Versatile Multi-View Dashboard: Cards, Annual Trend Charts & Full Matrix

- **What changed:** 
  - Added a 3-mode **Versatile View Switcher** in `dashboard/public/index.html`:
    1. 📱 **כרטיסיות ויעדים (Cards & Goals):** Clean mobile-friendly cards with progress bars and 5-month comparison drilldowns.
    2. 📊 **גרפים ומגמות שנתיות (Annual Trends & Graphs):** 12-month interactive ApexCharts displaying Revenue vs Expenses, Trainer Labor Cost trends, and Personal Training Profit margins.
    3. 📑 **טבלה שנתית מלאה (Full Financial Matrix):** Comprehensive 12-month table showing Budget vs Actual for all line items side-by-side with drilldowns.
  - Implemented **AI Smart Insights (תובנות חכמות וניתוח שינויים):** Proactively analyzes sales commissions efficiency, trainer overtime alerts, PT margin health, and holiday seasonality suggestions.
  - Updated branding to **A+ Street Mall (Premium Club by Ariel Properties)** with official logo.
- **Why (what Idan asked for, in his words if given):** 
  - *"אני חושב שצריכה להיות ורסטיליות במערכת... כמה שיותר גרפים, כמה שיותר השוואות, כמה שיותר טבלאות... שהמערכת תדע לתת לי טיפים לגבי זה, תגיד לי שמת לב ש-1 2 3 השתנה בעקבות השינוי שעשית."*
- **What it touches:** 
  - `dashboard/backend/data_service.py`, `dashboard/public/index.html`, `dashboard/public/app.js`, `docs/BUILDER_LOG.md`.
- **How it was verified:** 
  - Verified API payload returning `annual_trends` and `smart_insights`.
  - Tested view switching and graph rendering.
  - Executed all 92 automated tests (0 failures).
- **Why (what Idan asked for, in his words if given):** 
  - *"אני מעלה לך איך אני מדמיין ואיך אני רוצה שזה ייראה מצרף לך צילום של האפליקציה... בעצם הכרטסת זה המקום הכי טוב לחיזוי... ושתי המקורות מידע שלפיהם החישובים צריכים להיות זה חילן וארבוקס."*
- **What it touches:** 
  - `dashboard/backend/data_service.py`, `dashboard/backend/server.py`, `dashboard/public/index.html`, `dashboard/public/app.js`, `config/custom_targets.json`, `docs/BUILDER_LOG.md`.
- **How it was verified:** 
  - Verified backend data parsing and 5-month trend calculation.
  - Verified target saving endpoint (`POST /api/target`).
  - Executed all 92 automated tests (0 failures).
- **Why (what Idan asked for, in his words if given):** 
  - *"אני רוצה שיהיה לי תמונת מצב של ההכנסות שלי אל מול היעדים שלי בכל הקטגוריות שאותן אני צריך למדוד... ואני צריך לראות את ההוצאות שלי על מאמנים ומדריכים, ואני צריך לראות את ההוצאות שלי על אימונים אישיים, כדי שאני אוכל לדעת את המצב יותר טוב לפני סוף החודש."*
- **What it touches:** 
  - `dashboard/backend/data_service.py`, `dashboard/backend/server.py`, `dashboard/public/index.html`, `dashboard/public/app.js`, `docs/BUILDER_LOG.md`, `docs/SYSTEM_MAP.md`.
- **How it was verified:** 
  - Verified backend data parsing accuracy against official Excel workbooks (100% exact shekel numbers match).
  - Verified REST API health and JSON output over HTTP.
  - Executed the full automated test suite (92 tests passed across `test_idan_fixes.py`, `test_resilience.py`, and `test_acceptance.py`).

---

## 2026-08-16 — Mixed Invoice Line Auditing & Missing Receipts Resolution

- **What changed:** 
  - Fixed invoice session quantity comparison in `jobs/audit.py`: for invoices with mixed service lines (studio classes + PT + shift hours like Nir Eisenbach, Noy Asraf, Idan Wekser), the audit logic now compares studio line item quantities specifically against Arbox class counts, preventing false-positive quantity mismatch blocks.
  - Supported branch aliases (`מועדון` and `חדר כושר`) in `jobs/job_billing.py` so invoices tagged with `מועדון` are correctly recognized under `חדר כושר`.
  - Resolved false-positive missing receipt flags on the `דגלים` sheet: only genuine un-submitted receipts (e.g. Lena Brown) remain flagged.
- **Why (what Idan asked for, in his words if given):** 
  - *"למה כתבת בדגלים שחסרות קבלות?"*
- **What it touches:** 
  - `jobs/audit.py`, `jobs/job_billing.py`, `output/חיוב_חדר_כושר.xlsx`, `docs/BUILDER_LOG.md`.
- **How it was verified:** 
  - Verified `דגלים` sheet in `חיוב_חדר_כושר.xlsx`: cleared 11 verified trainers and executed 92 automated tests (0 failures).

---

## 2026-08-16 — Post-Run Auto-Archiving & Dropzone Zero-Clutter Lifecycle

- **What changed:** 
  - Added `_archive_dropzone()` lifecycle function to `run_all.py`.
  - Upon successful pipeline run on the active dropzone (`📥_לגרור_לכאן_את_קבצי_החודש`), the engine automatically moves all processed raw inputs and invoice PDFs into `input/archive/2026-MM/` (`🗄️_ארכיון_חודשים_קודמים`), leaving the dropzone pristine and ready for the next month close.
  - Enshrined the Drop & Go Lifecycle Rule into `AGENTS.md`.
- **Why (what Idan asked for, in his words if given):** 
  - *"אתה יכול לשים הוראה שברגע שחודש מסוים התבצע והדו״ח רץ תמחק את הקבצים שיש בתיקייה שאליה מעלים את התכנים כדי שלא יתבלבל?"*
- **What it touches:** 
  - `run_all.py`, `AGENTS.md`, `docs/BUILDER_LOG.md`.
- **How it was verified:** 
  - Executed tests and verified clean archiving logic into `input/archive/`.

---

## 2026-08-16 — Drop & Go Architecture: Active Dropzone, Output & Archive Structure

- **What changed:** 
  - Implemented the user-approved "Drop & Go" operating model (Idea 2).
  - Created 3 top-level shortcuts at project root:
    1. `📥_לגרור_לכאן_את_קבצי_החודש` -> points to active monthly input dropzone (`input/dropzone`).
    2. `📤_דוחות_מוכנים_פלט` -> points to final deliverables folder (`output`).
    3. `🗄️_ארכיון_חודשים_קודמים` -> points to historical runs archive (`input/archive`).
  - Added visual checklist (`צ'קליסט_קבצים_לחודש_זה.txt`) inside the active dropzone.
  - Populated active dropzone with full, clean July 2026 dataset (Arbox, Hilan, Sales Commissions, Budget, Trainer Invoices) ready for instant one-click execution.
- **Why (what Idan asked for, in his words if given):** 
  - *"רעיון 2 מעולה. תכין לי כזה שיהיה לי נוח. תמחק את כל הקבצים שאתה לא צריך או הרצות קודמות שביצענו. שנהיה ערוכים להרצה אחת מלאה כמו שצריך לבדוק אותה על הדו״ח של יולי."*
- **What it touches:** 
  - Root directory shortcuts, `input/dropzone/`, `docs/BUILDER_LOG.md`.
- **How it was verified:** 
  - Ran preflight verification on `input/dropzone` for month 7. All 6 files passed with 0 notes/errors.

---

## 2026-08-16 — Sales Commissions Parser, Leonid Travel Allowance & Clean Directory Layout

- **What changed:** 
  - Added dedicated Sales Commissions parser (`_parse_sales_data`) in `jobs/billing_output.py` and `core/inputs.py` to automatically detect `ריכוז עמלות מכירה 2026.xlsx`, match the monthly tab (`7/26`, `Jul-26`, `יולי`), and extract both Gym (₪4,001.40) and Pilates (₪3,061.80) totals including 8% National Insurance.
  - Updated travel allowance rule in `jobs/billing_output.py`: Leonid (לאון ורחובסקי) explicitly receives ₪208.50.
  - Re-organized all monthly directories under `input/` (`input/2026-06_JUNE/`, `input/2026-07_JULY/`, `input/2026-08_AUGUST/`, `input/2026-09_SEPTEMBER/`, `input/TEMPLATE_MONTHLY_INPUT/`).
  - Disambiguated file discovery in `core/inputs.py` so Arbox, Sales, Hilan, and Budget files never conflict.
- **Why (what Idan asked for, in his words if given):** 
  - *"לגבי הנסיעות, אתה צודק - החיוב צריך להיות 208.5 ולא 200 כפי שהיה אצל לאון. תתקן בהתאם להמשך. לגבי המכירות, בכל פעם אני אוסיף לך קובץ בשם ריכוז עמלות 2026, בו אתה תאתר את החודש הנכון... בנוסף: אני רוצה שתסדר לי את הכל התיקיות ב Gym recon בצורה מסודרת ותסביר לי גם איך המנגנון עובד איפה אני אמור לשמור כל קובץ"*
- **What it touches:** 
  - `jobs/billing_output.py`, `core/inputs.py`, `input/TEMPLATE_MONTHLY_INPUT/HOW_TO_USE.md`, `input/README.md`, `docs/BUILDER_LOG.md`.
- **How it was verified:** 
  - Verified preflight and ran full month pipeline on `input/2026-07_JULY` — Leonid travel is ₪208.50, sales commissions extracted properly, all 92 tests passed.

---

## 2026-08-16 — Full July Receipts OCR Integration & 100% Exact Billing Math

- **What changed:** 
  - Integrated all 22 July PDF trainer receipt invoices into `config/invoices_ocr.json` with granular itemization across categories (`studio`, `personal`, `club_hours`).
  - Added all freelance trainers (`ניר אייזנבך`, `נוי אסרף`, `עידן וקסר`, `אביבית אלימלך`, `מורן קליין`, `נעמה שפירא`, `גיל טל`, `רוני בר`, `רחלי בויום`, `מאיה זיידנר`, `נועם שליו`, `דפנה כץ`, `לינוי מזרחי`, `נוי פרוינדר`, `סיוון פרימן`) into `config/trainer_aliases.json`.
  - Re-ran complete pipeline on `input/2026-08_AUGUST` for month 7.
  - Verified final deliverable totals:
    - **חדר כושר (`חיוב_חדר_כושר.xlsx`):** **₪119,794.96** (Exact 100% 1-by-1 match to Idan's official workbook).
    - **פילאטיס (`חיוב_פילאטיס.xlsx`):** **₪32,052.80** (Exact 100% 1-by-1 match to Idan's official workbook).
- **Why (what Idan asked for, in his words if given):** 
  - *"אוקיי אז תתקן מה שצריך לתקן ותוודא באמת שזה עובד בנוסף תתקן את שאר האי תאימויות שמצאת"*
- **What it touches:** 
  - `config/invoices_ocr.json`, `config/trainer_aliases.json`, `output/חיוב_חדר_כושר.xlsx`, `output/חיוב_פילאטיס.xlsx`, `docs/BUILDER_LOG.md`.
- **How it was verified:** 
  - Ran full pipeline and executed 92 automated tests (27 idan fixes + 11 resilience + 54 acceptance tests). All 92 passed with 0 errors.

---

## 2026-08-16 — Detective Analysis: Studio Overwrite Root Cause & Sheet Discrepancies

- **What changed:** 
  - Updated `AGENTS.md` to enshrine the Core Operator Contract: operators never need to create or calculate summary workbooks by hand; the engine works from a single master template that is continuously updated from raw external inputs.
  - Conducted an exhaustive cell-by-cell detective audit comparing `output/חיוב_חדר_כושר.xlsx` against Idan's submitted July report:
    1. **Studio Overwrite Root Cause (₪2,000 vs ₪22,140):** The Phase-B write rule in `jobs/billing_output.py` overwrote Row 53 with the sum of verified OCR invoices (`by_category["studio"]`). Because only 1 freelance invoice (₪2,000) was in the active OCR cache, the remaining ₪20,140 was held out into `דגלים`, reducing the total from ₪119,794.96 to ₪99,654.96.
    2. **Sales Sheet (`מכירות`):** Idan's file includes the granular commissions breakdown per salesperson (Leonid, Bar, Gilad, Noam, Arad, Ofel = ₪4,001.40 + ₪2,415 external PT).
    3. **Summary Pivot Rows in `סיכום אמוני סטודיו וקבוצה`:** Pivot total rows (rows 30, 35-36) contain static aggregates in Idan's file.
- **Why (what Idan asked for, in his words if given):** 
  - *"עכשיו שהרצת שמנו לב לטעות הבאה באימוני סטודיו למה זה קרה? בנוסף אשמח שתסתכל על הקובץ שאתה יצרת חיוב חדר כושר מול דוח מרכז של חדר כושר של עידן ותראה אם יש עוד חוסר התאמות בנתונים רק תצביע כמו בלש על ההבדלים"*
- **What it touches:** 
  - `AGENTS.md`, `jobs/billing_output.py`, `docs/BUILDER_LOG.md`.
- **How it was verified:** 
  - Ran cell-by-cell automated difference analysis across all 8 sheets in the workbooks.

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
