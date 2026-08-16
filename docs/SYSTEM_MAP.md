# System Map — gym-recon

## Overview

`gym-recon` is the central financial calculation and auditing engine for **אריאל פיט & ספא (A+ Street Mall)**. It automates three main monthly operations:
1. **Developer / Entrepreneur Billing (`חיוב יזם`):** Calculates how much to charge the building developer for gym and pilates operations based on employee payroll (Hilan), freelance trainer invoices, fixed management fees, and sales commissions.
2. **Budget vs. Actual Reconciliation (`תקציב מול ביצוע`):** Syncs real general ledger (`כרטסת`) account transactions into the official budget workbook while safeguarding manual adjustments (`התאמה ידנית / ביאורים`).
3. **Supplier Payment Approval (`ספקים לאישור מנהל`):** Verifies vendor invoices and sorts approved payments into net +30 and net +60 payment cycles.

```text
MONTHLY INPUTS DROP (input/)
   ├── Invoices (PDFs of Freelancers & Suppliers)
   ├── Hilan Payroll (פרויקטים ספא / חילנט .xlsx)
   ├── Arbox Held Classes Export (.csv / .xlsx)
   ├── General Ledger (כרטסת .xlsx)
   └── Sales Report (מכירות .xlsx)
         │
         ▼
[1. PREFLIGHT & OCR WORKFLOWS]
   ├── tools/preflight.py (checks all required input files exist)
   └── tools/ocr_gemini.py (extracts text, tax ID, amounts, dates from PDFs)
         │
         ▼
[2. CORE PROCESSING ENGINES]
   ├── tools/billing.py / jobs/job_billing.py (Trainer & Staff Billing Engine)
   │     ├── Cross-validates Freelancer Invoices vs Arbox Sessions vs Pay Matrix
   │     ├── Computes Salaried Instructor & Receptionist Shift + Overtime Hours from Hilan
   │     ├── Adds Fixed Management Fees + Sales Commissions
   │     └── Produces: output/חיוב_חדר_כושר_<month>.xlsx & output/חיוב_פילאטיס_<month>.xlsx
   │
   ├── tools/ledger_sync.py / jobs/job3_ledger_sync.py (Budget vs Actual Sync)
   │     ├── Maps ledger debit/credit per account & memo month
   │     ├── Overwrites 'ביצוע (כרטסת)' column while protecting manual notes
   │     └── Produces: output/תקציב_מול_ביצוע_<month>.xlsx
   │
   └── tools/suppliers.py / jobs/job_supplier_payments.py (Supplier Engine)
         ├── Categorizes vendor invoices into +30 and +60 payment terms
         └── Produces: output/ספקים_לאישור_מנהל.xlsx
         │
         ▼
[3. AUDIT, FLAGS & VALIDATION]
   ├── tools/validate.py (checks output deliverables integrity)
   └── output/runs/<run_id>/ (stores manifest, SHA256 hashes, and execution logs)
```

---

## Workflows

### 1. Preflight Validation
- **Where it lives:** `tools/preflight.py`
- **Trigger:** Terminal command or automatically as the first step of `run_all.py`.
- **What it reads:** The `./input` folder.
- **What it writes:** Console status output and preflight check results.
- **Depends on:** Raw input files dropped into `./input`.
- **Breaks if:** Critical input files are missing or filenames cannot be parsed.

---

### 2. Gemini Invoice OCR
- **Where it lives:** `tools/ocr_gemini.py`, `core/ocr.py`
- **Trigger:** Terminal command (`python tools/ocr_gemini.py`) or pipeline run.
- **What it reads:** PDF invoice files in `./input/invoices` or `./input/suppliers`.
- **What it writes:** Cache file `config/invoices_ocr.json` (contains structured vendor name, tax ID, doc number, doc date, session dates, quantities, rates, and total amounts).
- **Depends on:** `GEMINI_API_KEY` environment variable and network access.
- **Breaks if:** Gemini API is unreachable or PDF scan quality is illegible.

---

### 3. Trainer & Staff Billing Engine (`חיוב יזם`)
- **Where it lives:** `tools/billing.py`, `jobs/job_billing.py`, `jobs/billing_output.py`, `jobs/audit.py`
- **Trigger:** `python tools/billing.py --input ./input --output ./output --month N` or `run_all.py`.
- **What it reads:** 
  - OCR invoices: `config/invoices_ocr.json`
  - Arbox sessions: `./input/arbox.csv` (or `.xlsx`)
  - Hilan payroll: `./input/**/פרויקטים*.xlsx`
  - Monthly template/source workbook: `./input/דוח_מרכז_*.xlsx` (or `./files/`)
  - Config tables: `config/pay_matrix.json`, `config/branches.json`, `config/trainer_aliases.json`
- **What it writes:** 
  - `output/חיוב_חדר_כושר_<month>.xlsx`
  - `output/חיוב_פילאטיס_<month>.xlsx`
  - `output/trainer_amounts_<branch>.json`
- **Depends on:** Correct trainer alias mapping, pay matrix rates, and matching Hilan/Arbox inputs.
- **Breaks if:** Formula structure in `דוח מרכז לאישור מנהל` is unrecognized or an unknown trainer rate cannot be resolved.

---

### 4. Ledger Sync Engine (`תקציב מול ביצוע`)
- **Where it lives:** `tools/ledger_sync.py`, `jobs/job3_ledger_sync.py`, `jobs/ledger_output.py`, `core/ledger.py`
- **Trigger:** `python tools/ledger_sync.py --input ./input --output ./output --month N` or `run_all.py`.
- **What it reads:**
  - Accounting ledger: `./input/כרטסת.xlsx`
  - Budget template: `./input/תקציב*.xlsx`
  - Account mapping: `config/account_map.json`
- **What it writes:** `output/תקציב_מול_ביצוע_<month>.xlsx`
- **Depends on:** Valid ledger sheet snapshot and recognized account numbers (180xxx for Club, 181xxx for Pilates).
- **Breaks if:** Ambiguous snapshot tab in `כרטסת.xlsx` without explicit selection.

---

### 5. Supplier Payment Approval Engine (`ספקים לאישור מנהל`)
- **Where it lives:** `tools/suppliers.py`, `jobs/job_supplier_payments.py`, `jobs/supplier_output.py`
- **Trigger:** `python tools/suppliers.py --input ./input --output ./output --month N` or `run_all.py`.
- **What it reads:** Supplier invoices via OCR (`config/invoices_ocr.json`), `config/supplier_whitelist.json`, and account map.
- **What it writes:** `output/ספקים_לאישור_מנהל.xlsx` (tabs: +30, +60, דגלים) and `output/supplier_summary.json`.
- **Depends on:** Whitelist supplier configurations for terms (+30 vs +60).
- **Breaks if:** Supplier name is completely unmapped and cannot be categorized.

---

### 6. Full Pipeline Orchestrator & Audit
- **Where it lives:** `run_all.py`, `jobs/audit.py`, `core/manifest_tracking.py`
- **Trigger:** `python run_all.py --input ./input --output ./output --month N`
- **What it reads:** All inputs, config files, and outputs.
- **What it writes:** `output/runs/<run_id>/manifest.json`, `report_status.json`, `run.log`, and creates/removes `output/RUN_INVALID.txt`.
- **Depends on:** Successful execution of Billing, Ledger Sync, and Supplier jobs.
- **Breaks if:** Hard validation failure occurs (e.g. money totals mismatch or corrupted formulas).

---

## Spreadsheets

### 1. Workbooks: `חיוב_חדר_כושר_<month>.xlsx` & `חיוב_פילאטיס_<month>.xlsx`
- **Purpose:** Official monthly charge sheets delivered to the developer/owner and internal manager sign-off.
- **Tabs:**
  - `חיוב יזם`: Summary table summarizing all billing items to the developer (numbers resolved from formulas).
  - `דוח מרכז לאישור מנהל`: Detailed manager approval sheet broken down by salaried employees, external instructors, reception, management fees, and overtime.
  - `סיכום אמוני סטודיו וקבוצה` (Gym) / `סיכום אימונים ומכירות מנויים` (Pilates): Trainer-by-trainer session counts and wage summaries populated from Arbox & Hilan.
  - `חילנט`: Raw monthly payroll export lines for cross-checking.
  - `ריכוז שעות`: Detailed shift-by-shift clock-in/out records.
  - `מכירות`: Monthly sales commission totals.
  - `דגלים`: Automated audit exception sheet highlighting variances, unmapped names, or held invoices.
- **Key Columns:**
  - *Inputs (from raw files/manager):* Clock hours in Hilan, session counts in Arbox, sales commission raw data.
  - *Outputs (filled by engine):* Freelancer amounts (`מאמני חוץ`), calculated employer costs, overtime surcharges, resolved summary totals in `חיוב יזם`.

---

### 2. Workbook: `תקציב_מול_ביצוע_<month>.xlsx`
- **Purpose:** Budget vs. actual tracking for the gym and pilates operations.
- **Tabs:**
  - `תקציב חדר כושר` / `תקציב פילאטיס`
- **Key Columns:**
  - `סעיף תקציבי` / `שם סעיף` (Account Code / Name)
  - `תקציב [חודש]` (Budgeted figure)
  - `[חודש] ביצוע (כרטסת)` (Actual ledger transactions — **overwritten each run by engine**)
  - `[חודש] התאמה ידנית / ביאורים` (Manual explanations — **never touched by engine**)
  - `[חודש] - ביצוע` (Sum of ledger actual + manual adjustment)
  - `סה"כ תקציב YTD`, `סה"כ ביצוע YTD`, `הפרש YTD`

---

### 3. Workbook: `ספקים_לאישור_מנהל.xlsx`
- **Purpose:** Summary of all monthly third-party supplier bills for management approval.
- **Tabs:**
  - `שוטף + 30`: Vendors on net 30 payment terms (e.g. monthly operational utilities, rent, cleaning).
  - `שוטף + 60`: Vendors on net 60 payment terms.
  - `דגלים`: Unrecognized suppliers or missing invoice details.
- **Key Columns:**
  - `שם ספק` (Supplier Name), `ח.פ / ע.מ` (Tax ID), `חשבונית` (Invoice #), `תאריך` (Date), `סכום לתשלום` (Amount), `אושר לתשלום (צהוב)` (Approval Checkbox cell).

---

## Relationships & Data Flow

| Source / Step | Trigger / Action | Target Workflow | Destination Output / Tab |
| :--- | :--- | :--- | :--- |
| `input/invoices/*.pdf` | OCR scan | `tools/ocr_gemini.py` | `config/invoices_ocr.json` |
| `config/invoices_ocr.json` + `input/arbox.csv` + `pay_matrix.json` | 3-way match & audit | `jobs/job_billing.py` | `output/trainer_amounts_<branch>.json` |
| `input/**/פרויקטים*.xlsx` (Hilan) + `input/arbox.csv` | Populate session & wage data | `jobs/billing_output.py` | `סיכום אמוני סטודיו וקבוצה` / `סיכום אימונים` |
| Validated Freelancer Totals + Hilan Shift Hours | Write detail rows & recompute grand total | `jobs/billing_output.py` | `דוח מרכז לאישור מנהל` |
| `דוח מרכז לאישור מנהל` | Freeze formulas to numbers | `jobs/billing_output.py` | `חיוב יזם` |
| `input/כרטסת.xlsx` + `account_map.json` | Ledger net debit-credit parse | `jobs/job3_ledger_sync.py` | `תקציב_מול_ביצוע_<month>.xlsx` (`ביצוע כרטסת`) |
| `config/invoices_ocr.json` + `supplier_whitelist.json` | Terms matching (+30/+60) | `jobs/job_supplier_payments.py` | `ספקים_לאישור_מנהל.xlsx` |

---

## Business Rules Comparison & "CONFIRM WITH IDAN"

Below is the side-by-side comparison between the gym operator's instructions and the current codebase implementation:

### 1. Developer Billing Line Items (`חיוב יזם`)
- **Receptionist Hours (`פקידת קבלה`):**
  - *Operator rule:* Based on Hilan clock hours for all reception staff, except Nicole Edelman (`ניקול אדלמן`) who belongs to Pilates. Rate: ₪70/hr regular, +₪17.50 (125%), +₪35.00 (150%), +₪52.50 (175%), +₪70.00 (200%).
  - *Current implementation:* Exact rate table matches in `config/pay_matrix.json`. Nicole is mapped to Pilates reception in `config/trainer_aliases.json`.
  - **CONFIRM WITH IDAN:** Are overtime increments added on top of the base ₪70 (e.g. 125% = ₪70 + ₪17.50 = ₪87.50, or paid as overtime differential hours)? *(In the sheet, the rate table lists base ₪70 and separate additive overtime columns 18.75/37.50 or 17.50/35.00).*

- **Instructor Shift Hours (`שעות מאמנים - משמרת`):**
  - *Operator rule:* Distinction between salaried (Hilan) and freelancers (invoices). Salaried rates: ₪75/hr regular, +₪18.75 (125%), +₪37.50 (150%), +₪56.25 (175%), +₪75.00 (200%).
  - *Current implementation:* Rates are in `config/pay_matrix.json`. Freelance invoices are routed to `מאמני חוץ` rows.

- **Deduction of Personal/Group Sessions from Shift Hours:**
  - *Operator rule:* In Hilan, "סה״כ שעות לשכר" includes personal training and group training hours. Therefore, shift hours must subtract personal/group hours so there is no double-counting.
  - *Current implementation:* Handled in the Excel template formulas (`שעות עבודה בפועל = סה"כ שעות פחות אימונים אישיים`).
  - **CONFIRM WITH IDAN:** Should the Python billing engine verify and enforce this subtraction automatically if the template formulas are missing or modified?

- **Travel Allowance (`תשלום נסיעות`):**
  - *Operator rule:* 50% job capacity and below = ₪100 fixed; above 50% capacity = ₪200 fixed.
  - *Current implementation:* In July 2026 Pilates report (`דוח מרכז פילאטיס`), row 12 has ₪208.50.
  - **CONFIRM WITH IDAN:** How is the "50% capacity" defined in practice? Is it based on a fixed hour threshold (e.g., up to 91 hours = ₪100, over 91 hours = ₪200), or based on the job percentage field in Hilan?

- **Dual Role (Receptionist + Fitness Instructor):**
  - *Operator rule:* Hours must be strictly separated between reception (₪70) and fitness instruction (₪75) according to Hilan project codes / invoice items without duplicate hours.
  - *Current implementation:* Hilan project codes separate reception from fitness instruction.

- **Fixed Management Fees:**
  - *Professional Management (`ניהול מקצועי`):* ₪2,500 fixed per month. *(Matches code & sheet row 60)*.
  - *Gym Management (`ניהול חדר כושר`):* ₪22,000 fixed per month. *(In older sheets this was split as ₪20,000 + ₪2,000; operator confirmed ₪22,000 total)*.

- **Session Rates Charged to Developer:**
  - *Small Studio Class (`אימון סטודיו קטן`):* ₪180. *(Matches `config/pay_matrix.json`)*.
  - *Pilates Studio Class (`סטודיו פילאטיס קטן`):* ₪185. *(Matches `config/pay_matrix.json`)*.
  - *Personal Training (`אימון אישי`):* ₪115. *(Matches `config/pay_matrix.json`)*.

- **Sales & Upgrade Commissions (`עמלות מכירת מנויים ושידרוגים`):**
  - *Operator rule:* Total sales commissions taken from Sales Report **plus 8% National Insurance (`ביטוח לאומי`)**.
  - *Current implementation:* Currently reads direct from `מכירות!M11`.
  - **CONFIRM WITH IDAN:** Does the sales sheet `מכירות!M11` already include the +8% National Insurance, or should the engine add `* 1.08` to the raw commissions sum?

- **Pilates Specific Staffing:**
  - *Operator rule:* Naama Hayun (`נעמה חיון`) is the only salaried pilates instructor; Nicole Edelman (`ניקול אדלמן`) is the pilates receptionist; all other instructors are freelancers.
  - *Current implementation:* Aligned in `config/trainer_aliases.json` and `config/branches.json`.
