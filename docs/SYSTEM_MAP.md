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
   ├── Arbox Memberships Report (דו״ח מנויים .xlsx)
   ├── General Ledger (כרטסת .xlsx)
   └── Sales Report (מכירות 2026 .xlsx)
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
         │
         ▼
[4. INTERACTIVE EXECUTIVE DASHBOARD & MEMBERSHIP MONITOR]
   ├── dashboard/backend/data_service.py (aggregates BvA, billing, trainer stats, Arbox memberships & sales cancellations)
   ├── dashboard/backend/server.py (local HTTP REST API server on port 3000)
   └── dashboard/public/ (modern Hebrew RTL executive web UI with cards, charts, 12-month matrix & memberships module)
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
  - Hilan payroll: `./input/**/פרויקטים*.xlsx` (supports both detailed shift punches format and summarized employee table format)
  - Sales report: `./input/*מכירות*` (auto-detected `.xlsx` or `.csv`)
  - Monthly template/source workbook: `./input/דוח_מרכז_*.xlsx` (with automatic fallback to master templates under `./files/`, so the main coach never needs to manually create a new file every month)
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

## Business Rules & Operational Law (Confirmed by Idan & Gym Operator)

Below is the verified specification for the monthly billing calculations:

### 1. Receptionist Hours (`פקידת קבלה`)
- **Rule:** Calculated from Hilan clock hours for all reception staff, except Nicole Edelman (`ניקול אדלמן`) who is assigned to Pilates.
- **Rates:**
  - Base regular hour: ₪70.00
  - Overtime increments: 125% = +₪17.50/hr, 150% = +₪35.00/hr, 175% = +₪52.50/hr, 200% = +₪70.00/hr.
- **Calculation:** Shift total = `(Regular Hrs × ₪70) + (125% Hrs × ₪17.50) + (150% Hrs × ₪35.00) + (175% Hrs × ₪52.50) + (200% Hrs × ₪70.00)`.

### 2. Instructor Shift Hours (`שעות מאמנים - משמרת`)
- **Rule:** Distinction between salaried employees (Hilan payroll) and freelancers (invoices).
- **Salaried Rates:**
  - Base regular hour: ₪75.00
  - Overtime increments: 125% = +₪18.75/hr, 150% = +₪37.50/hr, 175% = +₪56.25/hr, 200% = +₪75.00/hr.
- **Freelancers:** Billed according to submitted invoice totals and placed in `מאמני חוץ` lines in `דוח מרכז לאישור מנהל`.

### 3. Deduction of Personal/Group Sessions from Shift Hours
- **Rule:** In Hilan, "סה״כ שעות לשכר" includes personal training and group training hours. Actual shift hours are calculated by subtracting personal/group training hours to prevent double billing.

### 4. Travel Allowance (`תשלום נסיעות לשכירים`)
- **Rule:**
  - Salaried employees working under 60 hours monthly: **₪100.00**
  - Salaried employees working 60–90 hours monthly: **₪150.00** (e.g. Bar Sidis, Niv Ben Haim, Opel Meyoni, Naama Hayon)
  - Salaried employees working over 90 hours monthly: **₪200.00** (e.g. Arad Kotzer, Nicole Edelman)
  - Leonid Verkhovsky (`לאוניד ורחובסקי`): **₪208.50** (fixed contract).
- **Single Travel Principle:** An employee with a dual role (e.g. Leon) receives travel allowance **once only** (under reception column D, never duplicated under instructor column K).

### 5. Dual Role (Receptionist + Fitness Instructor)
- **Rule:** Hours are strictly separated by project codes in Hilan (reception at ₪70 vs gym instruction at ₪75) without duplicate hours. Leon's remaining shift hours after personal/studio sessions are split 50% Gym instructor (Col O) and 50% Receptionist (Col P). Reception hours in `דוח מרכז` link dynamically via `='סיכום אמוני סטודיו וקבוצה'!P22`.

### 6. Salaried vs Freelance Class Groupings
- **Rule:** Salaried instructors' group classes belong **strictly under line 22660** (`אימונים קבוצתיים` - Row 49).
- Line 22653 (`אימוני סטודיו` - Row 52) for salaried staff is **₪0.00** (zeroed).
- Line 22653 (`שיעורי סטודיו מאמני חוץ` - Row 53) is reserved **strictly for external freelance invoices**.

### 7. Inactive Employee Clean Sweep
- **Rule:** When an employee terminates employment (e.g. Orly Baumel), all rows, lookup tables, and formulas referencing them across all sheets are purged to eliminate `#N/A` errors.

### 8. Mixed Freelance Invoice Routing
- **Rule:** Invoices with multiple services (e.g. Ido Gliko, Noy Asraf, Idan Wekser, Nir Eisenbach) are broken down per line item into their specific budget codes (shift hours -> 22604, PT -> 22650, studio -> 22653, management -> 22601/22655, sales commissions -> 22650 Row 61).

### 9. Hours Comparison Table Alignment
- **Rule:** All values in the `השוואת שעות עבודה` table in `דוח מרכז` are aligned strictly in column J (Col 10) in a single unified column without horizontal staggering into column K.

### 10. Pilates Specific Staffing
- **Rule:** Naama Hayun (`נעמה חיון`) is the sole salaried pilates instructor; Nicole Edelman (`ניקול אדלמן`) is the pilates receptionist; all other instructors are freelancers.


