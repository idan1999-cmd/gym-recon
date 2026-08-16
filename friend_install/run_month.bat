@echo off
cd /d %~dp0\..
if not "%~1"=="" goto :run_with_arg

REM No argument — prompt for month, default to previous month
for /f %%i in ('powershell -NoProfile -Command "(Get-Date).AddMonths(-1).Month"') do set prev_month=%%i
set /p month=Enter month number 1-12 (default=%prev_month%): 
if "%month%"=="" set month=%prev_month%
goto :run

:run_with_arg
set month=%1

:run
echo ========================================
echo Gym Recon — Month %month%
echo ========================================

REM Step 1: Preflight
python tools\preflight.py --input .\input
if errorlevel 1 (
    echo.
    echo ERROR: Preflight failed — check input\ folder has required files.
    pause
    exit /b 1
)
echo.

REM Step 2: OCR invoices (if any)
if exist .\input\invoices\*.pdf (
    python tools\ocr_gemini.py --invoices .\input\invoices --output .\config\invoices_ocr.json
    if errorlevel 1 (
        echo WARNING: OCR had errors — check config\invoices_ocr.json
    )
) else (
    echo [OCR] No invoices folder found — skipping OCR step.
)
echo.

REM Step 3: Billing
python tools\billing.py --input .\input --output .\output --month %month%
if errorlevel 1 (
    echo.
    echo ERROR: Billing step failed.
    pause
    exit /b 1
)
echo.

REM Step 4: Ledger Sync
python tools\ledger_sync.py --input .\input --output .\output --month %month%
if errorlevel 1 (
    echo.
    echo ERROR: Ledger sync step failed.
    pause
    exit /b 1
)
echo.

REM Step 5: Supplier invoices
if exist .\config\suppliers_ocr.json (
    python tools\suppliers.py --input .\input --output .\output --month %month%
    if errorlevel 1 (
        echo WARNING: Supplier step had errors — check output\ספקים_לאישור_מנהל.xlsx
    )
) else (
    if exist .\input\invoices_suppliers\*.pdf (
        echo [Suppliers] Supplier invoices found but no OCR cache — run OCR first or create config\suppliers_ocr.json
        python tools\suppliers.py --input .\input --output .\output --month %month%
    ) else (
        echo [Suppliers] No supplier invoices — skipping.
    )
)
echo.

REM Step 6: Validate
python tools\validate.py --output .\output
echo.

echo ========================================
echo DONE. Open output\ folder and check sheets דגלים / דגלים ספקים first.
echo ========================================
pause
