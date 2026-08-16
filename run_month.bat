@echo off
REM ============================================================
REM  LEGACY wrapper. Do NOT extend this file.
REM
REM  Owner decision G (2026-08): the AGENT is the product. The
REM  primary path is an agent calling run_pipeline() (or
REM  `python run_all.py`). This .bat is kept only so old muscle
REM  memory still works — it forwards straight to run_all.py.
REM ============================================================
setlocal
cd /d "%~dp0"
python run_all.py --input ./input --output ./output --month %1
set EXIT_CODE=%ERRORLEVEL%
echo.
echo [LEGACY run_month.bat] forwarded to run_all.py — exit %EXIT_CODE%
if not "%EXIT_CODE%"=="0" (
  echo.
  echo ************************************************************
  echo  RUN IS INVALID. See output\RUN_INVALID.txt and the per-run
  echo  audit dir under output\runs\ for details.
  echo ************************************************************
)
exit /b %EXIT_CODE%
