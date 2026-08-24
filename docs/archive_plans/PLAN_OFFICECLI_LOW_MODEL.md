# PLAN_OFFICECLI_LOW_MODEL.md

# gym-recon promote + skill install + OfficeCLI validate-only (low-model safe)

**Goal (v1):** Secure project path, register skill, friend 1-click run.  
OfficeCLI is **post-run validate only**. openpyxl remains the **only** Excel writer.

---

## STATUS (updated after DeepSeek partial run)

| Phase | Status | Evidence |
|-------|--------|----------|
| **0 Promote** | **DONE** | `C:\Users\Amit\Documents\gym-recon` has `run_all.py`, `core/`, `jobs/`, `config/`, etc. |
| **1 Skill install** | **DONE** | `~\.claude\skills\gym-recon\SKILL.md` and `~\.agents\skills\gym-recon\SKILL.md` exist + project root footer |
| **2 OfficeCLI install** | NOT STARTED | |
| **3 Bridge validate-only** | NOT STARTED | no `core/officecli_bridge.py` |
| **4A postcheck** | NOT STARTED | optional |
| **4B OfficeCLI writes** | **CANCELLED for v1** | do not implement |
| **5 Friend pack** | NOT STARTED | no `friend_install\` |
| **6 Docs paths** | PARTIAL | project exists; CLAUDE.md may still need install-paths section |

**Next for executor:** start at **Phase 5**, then **2**, then **3**, then **6**. Skip 0, 1, 4B.

---

## Paths

```
SOURCE (archive only — already copied) =
C:\Users\Amit\AppData\Local\Packages\Claude_pzs8sxrjxfjjc\LocalCache\Roaming\Claude\local-agent-mode-sessions\817ec14a-78a0-422d-8484-88324e7dd4eb\4fc43137-b9e4-4dd9-b4e9-fd00188475f4\local_29084a3a-c2f9-4368-8b45-3c9551fdd2ed\outputs\gym_recon_v2

TARGET = C:\Users\Amit\Documents\gym-recon
```

---

## Policy update (from review — mandatory)

1. **openpyxl** = sole writer for billing + ledger (do not replace `billing_output.py` / `ledger_output.py` with OfficeCLI sets).
2. **OfficeCLI v1** = optional install + post-run `validate` / `view issues` only. Never money-cell writes.
3. **Phase 4B CANCELLED** until human re-approves.
4. **Friend bat** must work on double-click: prompt for month or default previous month (no required CLI arg).
5. Do **NOT** change pay matrix, aliases, OCR, three-way match, unknown-trainer HOLD, or `התאמה ידנית` columns.

---

## Rules for the executor model

1. One phase at a time. VERIFY after each. Stop on VERIFY fail.
2. Prefer new files over rewrites.
3. Do not re-do Phase 0 or 1 unless VERIFY fails.
4. Windows PowerShell / cmd.
5. If OfficeCLI missing after Phase 2: set note `OFFICECLI=0`, still finish Phase 5 + 6; Phase 3 must no-op gracefully.

---

## Phase 0 — Promote (DONE — only re-run if missing)

Copy SOURCE → TARGET if `TARGET\run_all.py` missing.

### VERIFY 0

```powershell
Test-Path C:\Users\Amit\Documents\gym-recon\run_all.py
Test-Path C:\Users\Amit\Documents\gym-recon\jobs\billing_output.py
Test-Path C:\Users\Amit\Documents\gym-recon\config\branches.json
```

---

## Phase 1 — Skill install (DONE — only re-run if missing)

Skills at:

- `%USERPROFILE%\.claude\skills\gym-recon\SKILL.md`
- `%USERPROFILE%\.agents\skills\gym-recon\SKILL.md`

Footer should include project root `C:\Users\Amit\Documents\gym-recon`.

**Also fix (if still wrong):** Excel preference line must say **validate only**, not "read/write":

```markdown
## Excel tool preference (v1)
Prefer openpyxl for all Excel writes (existing code).
If `officecli` is on PATH, use it only for post-run validate / issues / optional preview.
Never write cells with OfficeCLI in v1.
Never write cells in columns labeled התאמה ידנית.
```

### VERIFY 1

```powershell
Test-Path C:\Users\Amit\.claude\skills\gym-recon\SKILL.md
Test-Path C:\Users\Amit\.agents\skills\gym-recon\SKILL.md
Select-String -Path C:\Users\Amit\.claude\skills\gym-recon\SKILL.md -Pattern "Documents\\gym-recon"
```

Optional cleanup: fix broken markdown fences in skill footer if present (`` `bash `` / stray backticks).

---

## Phase 5 — Friend install pack (DO NEXT)

Create: `C:\Users\Amit\Documents\gym-recon\friend_install\`

### 1) `install.ps1`

```powershell
$ErrorActionPreference = "Stop"
$Root = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $Root
Write-Host "Project root: $Root"
Write-Host "Installing OfficeCLI (optional validate tool)..."
try {
  irm https://d.officecli.ai/install.ps1 | iex
  officecli --version
} catch {
  Write-Host "OfficeCLI install failed or skipped: $_"
  Write-Host "Continuing — openpyxl path still works."
}
python -m pip install openpyxl pandas --quiet
foreach ($base in @(
  (Join-Path $env:USERPROFILE ".claude\skills\gym-recon"),
  (Join-Path $env:USERPROFILE ".agents\skills\gym-recon")
)) {
  New-Item -ItemType Directory -Force -Path $base | Out-Null
  Copy-Item (Join-Path $Root "SKILL.md") (Join-Path $base "SKILL.md") -Force
}
Write-Host "DONE. Put monthly files in input\ then double-click run_month.bat"
```

### 2) `run_month.bat` (double-click friendly)

```bat
@echo off
setlocal
cd /d %~dp0\..
set MONTH=%~1
if "%MONTH%"=="" (
  set /p MONTH=Enter month number 1-12 [or press Enter for previous month]: 
)
if "%MONTH%"=="" (
  for /f %%i in ('powershell -NoProfile -Command "(Get-Date).AddMonths(-1).Month"') do set MONTH=%%i
)
echo Running month %MONTH% ...
python run_all.py --input .\input --output .\output --month %MONTH%
if errorlevel 1 (
  echo FAILED
  pause
  exit /b 1
)
echo Done. Check output\ and sheet דגלים
pause
```

### 3) `FRIEND_README.txt`

```text
Gym recon — friend PC (Windows)

ONE-TIME
1) Install Python 3.10+ (check "Add to PATH")
2) Run: powershell -ExecutionPolicy Bypass -File install.ps1

EVERY MONTH
1) Put source files in input\
2) Double-click run_month.bat
3) Type month number 1-12 (or Enter = previous month)
4) Open output\ and read sheet דגלים first

NOTES
- Do not edit budget columns named התאמה ידנית
- Unknown trainers are held out of numbers on purpose
- Claude skill path (optional): say "run monthly recon" with gym-recon skill installed
```

### VERIFY 5

```powershell
Test-Path C:\Users\Amit\Documents\gym-recon\friend_install\install.ps1
Test-Path C:\Users\Amit\Documents\gym-recon\friend_install\run_month.bat
Test-Path C:\Users\Amit\Documents\gym-recon\friend_install\FRIEND_README.txt
```

---

## Phase 2 — Install OfficeCLI on this machine (optional but recommended)

```powershell
irm https://d.officecli.ai/install.ps1 | iex
officecli --version
```

MCP optional: `officecli mcp claude` then `officecli mcp list`.

### VERIFY 2

`officecli --version` prints a version. If fail → note `OFFICECLI=0`, continue.

Smoke (optional):

```powershell
cd C:\Users\Amit\Documents\gym-recon
officecli create _smoke.xlsx
officecli set _smoke.xlsx /Sheet1/A1 --prop value="ok"
officecli validate _smoke.xlsx
del _smoke.xlsx
```

---

## Phase 3 — Bridge: validate only (no write helpers required for money)

**New file only:** `core\officecli_bridge.py`

Implement:

- `available() -> bool`
- `run(args) -> parsed json or text`
- `validate(path)`
- `view_issues(path)` optional

**Do NOT implement set_value / batch_set for production money path.**

### Wire `run_all.py` at end only

```python
try:
    from officecli_bridge import available, validate
    if available():
        import glob
        for p in glob.glob(os.path.join(args.output, "*.xlsx")):
            try:
                validate(p)
                print("[officecli] validate ok", os.path.basename(p))
            except Exception as e:
                print("[officecli] validate warn", os.path.basename(p), e)
except Exception as e:
    print("[officecli] skipped", e)
```

Must never crash the monthly run if OfficeCLI missing.

### VERIFY 3

```powershell
cd C:\Users\Amit\Documents\gym-recon
python -c "from core.officecli_bridge import available; print(available())"
```

No crash. True or False both OK.

---

## Phase 4 — Excel writes via OfficeCLI

### 4A — optional postcheck script

`jobs/officecli_postcheck.py` may list output xlsx and call validate. No cell overwrites.

### 4B — CANCELLED

Do not replace openpyxl writers. Do not officecli-set amounts into `דוח מרכז` / budget.

---

## Phase 6 — Docs

Append to `CLAUDE.md` if missing:

```markdown
## Install paths
- Project: C:\Users\Amit\Documents\gym-recon
- Claude skill: ~/.claude/skills/gym-recon/SKILL.md
- Agents skill: ~/.agents/skills/gym-recon/SKILL.md
- Friend pack: friend_install/ (double-click run_month.bat)
- Excel writes: openpyxl only (v1)
- OfficeCLI: optional post-run validate only
```

Also update project `SKILL.md` Excel preference to validate-only (same text as Phase 1 fix), then re-copy to skill dirs.

### VERIFY 6

```powershell
Select-String -Path C:\Users\Amit\Documents\gym-recon\CLAUDE.md -Pattern "friend_install|validate only|Documents\\gym-recon"
```

---

## Forbidden

| Forbidden | Why |
|-----------|-----|
| Re-copy Phase 0 over and wipe local edits carelessly | may lose friend_install / bridge |
| OfficeCLI writes to money cells | correctness / scope |
| Change pay_matrix / aliases / OCR / HOLD | business rules |
| Require `run_month.bat 6` without prompt | friend UX |
| ADHD / multi-model in monthly runtime | not packaging |

---

## Done criteria (v1)

| # | Criterion |
|---|-----------|
| 1 | Project at `Documents\gym-recon` (DONE) |
| 2 | Skill in `~\.claude\skills\gym-recon` (DONE) |
| 3 | `friend_install\` with bat that prompts/defaults month |
| 4 | openpyxl still sole writer |
| 5 | OfficeCLI optional; bridge validate-only no crash |
| 6 | CLAUDE.md install paths |

---

## EXECUTOR PROMPT (continue)

See bottom of this file and the user message “continue prompt”.

---

## EXECUTOR CONTINUE PROMPT (copy-paste)

```text
You are a careful junior engineer on Windows.

Read and follow EXACTLY:
C:\Users\Amit\Documents\gym-recon\PLAN_OFFICECLI_LOW_MODEL.md

STATUS (do not re-do unless VERIFY fails):
- Phase 0 DONE (project already at C:\Users\Amit\Documents\gym-recon)
- Phase 1 DONE (skill already in ~/.claude/skills/gym-recon and ~/.agents/skills/gym-recon)
- Phase 4B CANCELLED — never implement OfficeCLI money writes

POLICY v1:
- openpyxl = only Excel writer
- OfficeCLI = optional post-run validate only
- run_month.bat must prompt for month or default previous month (double-click works)

DO NEXT IN ORDER:
1) Phase 5 — create friend_install\ (install.ps1, run_month.bat with prompt/default, FRIEND_README.txt) + VERIFY 5
2) Phase 1 fix — update Excel preference text in SKILL.md (project + both skill copies) to validate-only; fix broken markdown fences if any
3) Phase 2 — try OfficeCLI install; if fail note OFFICECLI=0 and continue
4) Phase 3 — add core/officecli_bridge.py (available/validate only) + end-of-run_all post-validate that never crashes + VERIFY 3
5) Phase 6 — CLAUDE.md install paths + VERIFY 6

RULES:
- Do not redesign OCR, aliases, pay_matrix, three-way match, HOLD, or התאמה ידנית
- Do not rewrite billing_output.py / ledger_output.py for OfficeCLI writes
- After each phase print VERIFY results
- Stop only on VERIFY failure

Start Phase 5 now.
```
