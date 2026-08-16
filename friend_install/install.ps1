$ErrorActionPreference = "Stop"
$Root = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $Root
Write-Host "Project root: $Root"

# Python dependencies (openpyxl only — no OfficeCLI, no pandas required)
python -m pip install openpyxl google-generativeai --quiet

# Optional: manual OCR via Gemini (skip if no key)
$key = [Environment]::GetEnvironmentVariable("GEMINI_API_KEY", "User")
if (-not $key) {
    Write-Host ""
    Write-Host "=== GEMINI_API_KEY not set ==="
    Write-Host "OCR requires a Gemini API key. To set one:"
    Write-Host "  [Environment]::SetEnvironmentVariable('GEMINI_API_KEY', 'your-key-here', 'User')"
    Write-Host "Then restart PowerShell. Without it, you must OCR invoices manually."
    Write-Host "==============================="
    Write-Host ""
}

# Claude skill
$skillDir = Join-Path $env:USERPROFILE ".claude\skills\gym-recon"
New-Item -ItemType Directory -Force -Path $skillDir | Out-Null
Copy-Item (Join-Path $Root "SKILL.md") (Join-Path $skillDir "SKILL.md") -Force

# Agents skill
$agentsDir = Join-Path $env:USERPROFILE ".agents\skills\gym-recon"
New-Item -ItemType Directory -Force -Path $agentsDir | Out-Null
Copy-Item (Join-Path $Root "SKILL.md") (Join-Path $agentsDir "SKILL.md") -Force

Write-Host "DONE. Put monthly files in input\ then double-click run_month.bat"
