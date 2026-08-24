# EXECUTOR_PROMPT.md

Copy everything inside the fence below into a new agent session (Claude / OpenCode / etc.).

---

```text
You are a careful senior engineer implementing gym-recon. Follow the plan file EXACTLY. Do not freestyle architecture.

PLAN (single source of truth):
C:\Users\Amit\Documents\gym-recon\PLAN_RECON_FINAL.md

PROJECT ROOT:
C:\Users\Amit\Documents\gym-recon

READ FIRST:
1) PLAN_RECON_FINAL.md (all sections)
2) CLAUDE.md
3) SKILL.md
4) Existing core/ and jobs/ (reuse — do not rewrite money logic from scratch)

══════════════════════════════════════
HARD POLICY (non-negotiable)
══════════════════════════════════════
- Agent orchestrates; Python tools do math + Excel.
- openpyxl ONLY for Excel. Do NOT install or depend on OfficeCLI.
- Gemini Vision is PRIMARY for Hebrew invoice PDFs/images (GEMINI_API_KEY from env only; never hardcode).
- Keep persistent JSON: config/invoices_ocr.json, output/audit_log.json, output/trainer_amounts_*.json, config/*.json
- Unknown trainer = HOLD + propose; never auto-write into money.
- Never write budget columns התאמה ידנית.
- Service month not doc date. Income negative in ledger. Hebrew keys unchanged.
- FIVE tools: preflight, ocr_gemini, billing, ledger_sync, validate (do not drop any).
- Friend run_month.bat must prompt for month or default previous month on double-click.

══════════════════════════════════════
ALREADY DONE (do not redo unless broken)
══════════════════════════════════════
- Project exists at Documents\gym-recon
- Skill dirs may already have SKILL.md — re-copy after you update SKILL.md

══════════════════════════════════════
IMPLEMENT IN ORDER
══════════════════════════════════════
Phase A: Ensure tools/ dir; VERIFY run_all.py + jobs + config exist.
Phase B: Strengthen core/ocr.py + tools/ocr_gemini.py (Gemini primary, cache, per-invoice isolation).
Phase C: Create tools/preflight.py, tools/billing.py, tools/ledger_sync.py, tools/validate.py wrapping existing jobs/core. Wire run_all.py to same pipeline order: preflight → ocr → billing → ledger → validate.
Phase D: Resilience — per-item isolation, unmapped account flags, label/row safety if needed; add chaos/resilience tests.
Phase E: friend_install/install.ps1 + run_month.bat (prompt/default month) + FRIEND_README.txt (NO OfficeCLI).
Phase F: Update SKILL.md + CLAUDE.md for tool orchestration, Gemini, persistence, openpyxl-only; copy skill to ~/.claude/skills/gym-recon and ~/.agents/skills/gym-recon.
Phase G: Only if A–F green — polish summaries on stdout JSON.

After EACH phase: run the VERIFY commands from the plan and print results.
If VERIFY fails: stop, fix that phase only, do not invent new product scope.

══════════════════════════════════════
DONE WHEN
══════════════════════════════════════
All items in PLAN section 7 “Done criteria” are true.
Report a short checklist of what you created/changed and how to run:
- Full pipeline (friend bat + run_all)
- Single tool examples for the agent
- Where flags live (דגלים + audit_log.json)

Start Phase A now.
```

---

## Shorter variant (if context is tight)

```text
Implement C:\Users\Amit\Documents\gym-recon\PLAN_RECON_FINAL.md exactly.
Root: C:\Users\Amit\Documents\gym-recon
5 tools: preflight, ocr_gemini (Gemini env key), billing, ledger_sync, validate.
openpyxl only — NO OfficeCLI. Reuse jobs/core. Persist invoices_ocr.json + audit_log.json + trainer_amounts_*.json.
HOLD unknown trainers. Never touch התאמה ידנית.
friend_install with run_month.bat that prompts for month.
Update SKILL.md + install to ~/.claude/skills/gym-recon.
Phases A→F with VERIFY after each. Start A.
```
