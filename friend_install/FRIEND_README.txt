Gym Recon — Friend Install (Windows)

ONE-TIME SETUP
1) Install Python 3.10+ and add to PATH
2) Right-click install.ps1 -> Run with PowerShell
   (or: powershell -ExecutionPolicy Bypass -File install.ps1)
3) Set GEMINI_API_KEY environment variable for automatic OCR:
   - Search "Environment Variables" in Windows
   - Add User variable: GEMINI_API_KEY = your-key
   - Without this key, OCR must be done manually

EVERY MONTH
1) Put source files in the input\ folder:
   - ledger (כרטסת) .xlsx or .csv
   - budget (תקציב מול ביצוע) .xlsx
   - Arbox (דו"ח שיעורים) .xlsx
   - approval report (דוח מרכז לאישור מנהל) per branch .xlsx
   - invoice files in input\invoices\ folder (optional)
2) Double-click run_month.bat
3) Enter month number when prompted (or Enter for previous month)
4) Open output\ folder, read sheet "דגלים" first (all flags)
5) Check workflow files in output\:
   - תקציב_מול_ביצוע_* — budget vs actual per branch
   - חיוב_* — billing workbook per branch

NOTES
- Do NOT edit columns named "התאמה ידנית" in budget files
- Unknown trainers are held out of numbers on purpose (see דגלים)
- Uses openpyxl only — no OfficeCLI required
- All Python tools are in tools\ folder
- For help: python tools\preflight.py --help
- Budget vs actual MUST come from: python tools\ledger_sync.py
  Do NOT let an AI agent rebuild the Excel by hand (wrong signs/totals).
- Official outputs: output\תקציב_מול_ביצוע_*.xlsx (footer: gym-recon ledger_sync)
- Income = negative numbers; expenses = positive (boss rule)
