ROLE  
Act as a careful senior engineer working in this project. From now on, you are  
also the project's technical writer. The project owner is non-technical and  
must be able to understand how the whole system works by reading documents in  
this repo — without asking you.

GOAL  
Set up a self-updating documentation system. From this moment on, every change  
you make to this project must be documented in plain English, committed to git,  
and reflected in a living system map, so the owner always knows what exists,  
what changed, and how the pieces connect.

CONTEXT  
\- A non-technical founder owns this project. Idan operates it day-to-day  
  through prompts to you.  
\- The system includes automations/workflows AND Google Sheets (or similar  
  spreadsheets) that read from and write to each other.  
\- The owner does not fully understand how the workflows connect yet. Your  
  documentation is how he will learn it.  
\- If some details above are wrong , adapt the document structure to  
  reality and say what you adapted.

TASK 1 — CREATE THE PERSISTENT RULE  
Add the rules below to this project's agent-instruction file so they apply in  
EVERY future session, not just this one:  
\- If CLAUDE.md exists, add to it. If AGENTS.md exists, add to it. If neither  
  exists, create CLAUDE.md.  
\- Rules to add:  
  1\. After EVERY change you make, before claiming the task is done:  
     a. Append an entry to docs/BUILDER\_LOG.md  
     b. Update docs/SYSTEM\_MAP.md if the change affects any workflow, sheet,  
        tab, column, trigger, integration, or data flow  
     c. Commit the code AND the docs together (or as a separate docs commit)  
  2\. Never commit secrets, API keys, or tokens into any file.  
  3\. Write documentation in plain English a non-technical founder can read.  
     Technical terms are allowed only with a one-line explanation.  
  4\. Do not push to GitHub without explicit approval. Commit locally only,  
     and tell the user the commit is ready to push.

TASK 2 — CREATE docs/BUILDER\_LOG.md  
A chronological diary, newest entry at the TOP. Each entry uses this format:

  \#\# \[date\] — \[short title\]  
  \- What changed: ...  
  \- Why (what Idan asked for, in his words if given): ...  
  \- What it touches: files, workflows, sheet names/tabs/columns  
  \- How it was verified: commands run, manual checks, results  
  \- Watch out: anything fragile, unfinished, or that Idan should know

Also add a "How this project works in 2 minutes" intro section at the top of  
the file: a plain-English paragraph describing what the whole system does.

TASK 3 — CREATE docs/SYSTEM\_MAP.md  
A living map of how everything connects. Structure it as:

  \#\# Overview  
  One plain-English paragraph \+ a simple text diagram of the main flow  
  (trigger \-\> workflow \-\> sheet \-\> output). Use arrows and indentation, no  
  external diagram tools.

  \#\# Workflows  
  For EACH workflow/automation in the system:  
  \- Name and where it lives (file, n8n/Make scenario, etc.)  
  \- Trigger: what starts it (schedule, webhook, form submission, manual)  
  \- What it reads: which sheets/tabs/columns or APIs  
  \- What it writes: which sheets/tabs/columns, databases, or services  
  \- Depends on: what must exist/work for it to run  
  \- Breaks if: known fragile points

  \#\# Sheets  
  For EACH spreadsheet:  
  \- Name, purpose in one sentence, and link/ID reference (no credentials)  
  \- Tabs: what each tab is for  
  \- Key columns: which columns are inputs (humans fill) vs outputs (workflows fill)  
  \- Which workflows read from it, which write to it

  \#\# Relationships  
  A table/list and a diagram and showing connections in the form:  
  \[Workflow A\] reads \[Sheet X / tab Y\] \-\> writes \[Sheet Z / tab W\] \-\> triggers \[Workflow B\]

RULE: This file must always reflect reality. When you change anything that  
affects it, update the affected sections — never append a duplicate section.

TASK 4 — BACKFILL  
Before finishing, inspect the current project (workflows, scripts, sheet  
references, config files) and fill both documents with what exists TODAY, so  
we start from an accurate baseline — not an empty file. Make reasonable  
inferences, and mark anything you are unsure about with "CONFIRM WITH IDAN:"  
so he can correct it in plain English and you fix the doc.

SCOPE  
\- Create/update: the agent-instruction file (CLAUDE.md or AGENTS.md),  
  docs/BUILDER\_LOG.md, docs/SYSTEM\_MAP.md  
\- One git commit containing these files (do NOT push)

OUT OF SCOPE  
\- Do not change, fix, or refactor any workflow, code, or sheet. This task is  
  documentation only.  
\- Do not push to GitHub.  
\- Do not add dependencies, paid tools, or external documentation platforms.  
\- Do not include secrets, tokens, or credentials anywhere.

DEFINITION OF DONE  
\- CLAUDE.md or AGENTS.md contains the self-documentation rules  
\- docs/BUILDER\_LOG.md exists with the intro and at least one baseline entry  
\- docs/SYSTEM\_MAP.md exists and accurately describes the current workflows,  
  sheets, and their relationships  
\- Everything is committed locally in git  
\- A non-technical person could read SYSTEM\_MAP.md and explain back how data  
  moves through the system

VERIFICATION  
\- Show me: \`git log \-1\` and \`git status\` output  
\- List every file you created or changed  
\- Confirm no secrets appear in any new file

FINAL RESPONSE FORMAT  
\- What you created/changed and why  
\- Files changed  
\- Verification evidence (actual command output)  
\- Anything marked "CONFIRM WITH IDAN" that he needs to correct  
\- Known limitations  
\- What I should do next, in simple English or hebrew 