# 📥 Input Directory — Gym Recon

This directory contains the monthly input folders for Ariel Fit & Spa (A+ Street Mall).

---

## 🗂️ Recommended Folder Layout

```text
input/
├── TEMPLATE_MONTHLY_INPUT/       <-- Copy this folder for every new month!
│   ├── invoices/                 <-- Put trainer receipts (קבלות) here
│   ├── invoices_suppliers/       <-- Put supplier invoices (חשבוניות ספקים) here
│   └── HOW_TO_USE.md
│
├── 2026-07_JULY/                 <-- July 2026 active run folder
│   ├── דוח מרכז 07.26 חדר כושר.xlsx
│   ├── דוח מרכז 07.26 פילאטיס.xlsx
│   ├── דוח שיעורים.csv
│   ├── פרויקטים _ דוח פרויקטים ספא לתקופה 07_2026 - 07_2026.xlsx
│   ├── תקציב תזרים 2026.xlsx
│   └── invoices/                 <-- July freelancer receipt PDFs
│
├── 2026-08_AUGUST/               <-- August 2026 folder (ready for files)
│   ├── invoices/
│   └── invoices_suppliers/
│
└── 2026-09_SEPTEMBER/            <-- September 2026 folder (ready for files)
    ├── invoices/
    └── invoices_suppliers/
```

---

## ⚡ Quick Start for Operators

1. Copy `TEMPLATE_MONTHLY_INPUT` and name it with your month (e.g. `2026-08_AUGUST`).
2. Drop the **5 monthly Excel/CSV files** into that folder.
3. Drop the **receipt PDFs** into the `invoices/` subfolder.
4. Run:
   ```bash
   python run_all.py --input ./input/2026-08_AUGUST --output ./output --month 8
   ```
