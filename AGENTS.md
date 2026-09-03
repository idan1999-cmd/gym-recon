# Agent rules — gym-recon (ledger & billing engine)

You are in the **monthly finance CLI engine** for אריאל פיט & ספא (A+ Street Mall).  
Client contact for budget-vs-actual: **Idan**.

## Operating model (read this first)

This product is **not** “100% deterministic agent.”  
It is **agent judgment + deterministic money tools.**

| Agent decides | Engine / tools own |
|---------------|--------------------|
| What’s wrong this month (flags, gaps, drift) | Final shekel amounts in official Excel |
| **What** to change (code, config, map, alias, test) | Ledger net (debit − credit), coded month rules |
| **How** to change it (approach, order, scope) | Two-layer write contract |
| Which tools to run (full month vs ledger only vs re-OCR) | Never invent amounts in chat as deliverables |
| How to explain results to Idan | Footer / audit trail of tool output |
| Product/process next steps when asked | |

**One-liner:** *Judgment is the agent’s job. Money math is the engine’s job. Prefer improving the engine over bypassing it.*

### Correct freedom
1. Diagnose (read outputs, דגלים, inputs, code)  
2. Decide what should change and how  
3. Implement in `core/` / `jobs/` / `tools/` / `config/` / `tests/` when needed  
4. Re-run the relevant tool(s)  
5. Validate and report  

### Wrong freedom
- Hand-paint תקציב / invent cells outside the product  
- Freestyle openpyxl “גרסה 2” as the official deliverable  
- Guess amounts in chat as the answer instead of fixing + re-running tools  

## What this product does for Idan

1. **תקציב מול ביצוע** — official workbooks from **כרטסת** + budget template  
   (`python tools/ledger_sync.py` → `output/תקציב_מול_ביצוע_*.xlsx`)
2. **Trainer billing & Manager reports** — invoice OCR + validation → `output/דו״ח מרכז חדר כושר *.xlsx`, `output/דו״ח מרכז פילאטיס *.xlsx` + `דגלים`
3. **Salaried Payroll Control** — `output/ריכוז בקרת שכר שכירים *.xlsx` (all-inclusive employer costs + developer reconciliation with 0 delta)
4. **Supplier pack** — `output/ספקים_לאישור_מנהל.xlsx` (+30/+60)

**Core Operator Contract:**  
*The operator does NOT need to create, duplicate, or calculate summary workbooks by hand. That is the exact job of this automation engine. We work on a single persistent master template that is automatically populated and updated from raw external inputs (Arbox, Hilan, Invoices, Sales).*

**Drop & Go Lifecycle Rule:**  
*Whenever the pipeline finishes processing a month from `📥_לגרור_לכאן_את_קבצי_החודש` (`input/dropzone`), all processed raw input files and PDF receipts are automatically archived to `🗄️_ארכיון_חודשים_קודמים` (`input/archive/YYYY-MM/`), leaving the dropzone clean and ready for the next month close.*

Idan reviews `output/` and `דגלים`; he should not need a freestyle Excel rebuild for official BvA.

## Sibling product (do not mix pipelines)

[`club-finance-recon`](https://github.com/amitswsisa-cyber/club-finance-recon) = trainer HTML recon, dashboard, GUI, **DRAFT** Excel packs.  
Different deliverable. Do not treat its drafts as `ledger_sync` output. See `SCOPE.md`.

## Session start

1. Read this file, `SCOPE.md`, `CLAUDE.md`, `.opencode/decisions.md` if present.  
2. Work under **this** repo root (`tools/`, `core/`, `jobs/`).  
3. Prefer relative paths: `./input`, `./output`, `python tools/...`.

## 🔒 Protected knowledge files — read before changing money logic

| File | Contains | Read it before |
|------|----------|----------------|
| `docs/CLIENT_IDAN.md` | Client transcript, real workflow, cadence, open questions | Touching cadence, sheet layout, or scope |
| `docs/DATA_INVENTORY.md` | Real input-file structure, verified risks | Writing/changing any parser |
| `docs/PRODUCT_STRATEGY.md` | Phase plan, what's in/out of scope | Proposing features or refactors |

**Rules for these three files:**
- They are **source of truth**. If code contradicts them, the **code** is wrong until the owner says otherwise.
- You may **append** to their Change log / Decision log sections.
- You may **not** rewrite, condense, summarize, translate, or delete anything above those sections.
- If your task is not in the current phase (`PRODUCT_STRATEGY.md` §5), **say so and stop** instead of doing it.

### Known-critical facts (do not "fix" without asking)
1. `התאמה ידנית` was **not found** in the client's real workbook — his manual column looks like `ביאורים`.
2. `כרטסת.xlsx` has **4 snapshot tabs**; June net differs by ~₪240k between them. Tab choice must be explicit.
3. תקציב מול ביצוע is a **weekly** dashboard for the client, not only a monthly close.

## Money write rules (non-negotiable)

| Do | Do not |
|----|--------|
| Prefer official numbers from tools under `output/` | Deliver freestyle xlsx as official BvA |
| When rules change: **edit engine code/config**, then re-run tools | Bypass engine by hand-totalling a new workbook |
| Never write `התאמה ידנית` | Invent amounts, accounts, or months in the deliverable |
| Keep Hebrew sheet/column keys as-is | Translate keys “for clarity” |
| Footer on official BvA: `written by gym-recon ledger_sync` | Treat Antigravity/גרסה 2 freestyle as engine truth |

## Default tools (extend code when rules need to change)

```text
python tools/preflight.py --input ./input
python tools/ocr_gemini.py --invoices ./input/invoices --output ./config/invoices_ocr.json
python tools/billing.py --input ./input --output ./output --month N
python tools/ledger_sync.py --input ./input --output ./output --month N
python tools/suppliers.py --input ./input --output ./output --month N
python tools/validate.py --output ./output
```

**Full month (primary path):** call `run_pipeline(input_dir, output_dir, month)` —
an agent runs this in-process, or `python run_all.py --input ./input --output ./output --month N`
from a terminal. `run_month.bat` is a **LEGACY** thin wrapper over `run_all.py`.

**Per-run audit (every full-month run):** `output/runs/<run_id>/` holds
`manifest.json` (input/output SHA-256 hashes + `selected_ledger_tab` + `client_id`),
`report_status.json` (`VALID` / `REVIEW_REQUIRED` / `INVALID`), and `run.log`.
`output/RUN_INVALID.txt` exists **only** for INVALID runs — never trust `output/`
while that marker is present.

- Choose subset by judgment (e.g. only `ledger_sync` if only budget from ledger).  
- If a rule is wrong for Idan: change `core/` / `jobs/` / `config/`, add/adjust tests, re-run — do not patch only the xlsx.

## Ledger business rules (current product law)

1. Two-layer: `ביצוע (כרטסת)` overwrite each run · `התאמה ידנית` never touch · `ביצוע` = sum (value).  
2. Income ≤ 0, expenses ≥ 0 (enforced on write).  
3. Month: memo `פרטים` (regex) → `תאריך למאזן` → `תאריך ערך`. Month attribution is coded, not ad-hoc LLM per row.  
4. Strip uncoded pricing-note rows; keep coded lines.  
5. YTD + income/expense rollups live in the engine — improve code if wrong, don’t reimplement once in chat.

## Tests before claiming a code change is done

```text
python tests/test_idan_fixes.py
python tests/test_resilience.py
python tests/test_acceptance.py
```

## Never commit

`input/**` (except README), `output/**` (except `.gitkeep`), `config/*_ocr.json`, API keys, `.env`.

## Billing business rules & precision principles (current product law)

1. **Reception Staff & Dual Roles (שעות קבלה ותפקידים כפולים):**
   - נועם תבל: 100% שעות קבלה (51 שעות בסיס + שעות נוספות).
   - לאוניד ורחובסקי: תפקיד כפול מדריך/קבלה (50% מדריך חדר כושר Col O, 50% נציג קבלה Col P).
   - עמודות הקבלה ב`דוח מרכז לאישור מנהל` נגזרות אך ורק באמצעות **נוסחה דינמית** מתוך `סיכום אמוני סטודיו וקבוצה` (`='סיכום אמוני סטודיו וקבוצה'!P22` ו-`P23`).
2. **Travel Allowance Law (תשלום נסיעות יחסי ועגול):**
   - הסכום המקסימלי לתשלום נסיעות הוא **208 ₪** עבור עובד שכיר שעבד בטווח של כ-`100–120` שעות.
   - עבור עובד שעבד פחות שעות, מחושב החלק היחסי המעוגל למספר עגול וברור (ללא שברים ומספרים רנדומליים, במכפלות של 10 ₪):
     - `100+` שעות: **208.00 ₪** (או לאוניד ורחובסקי = **208.50 ₪** לפי חוזה).
     - פחות מ-100 שעות: חישוב יחסי $\frac{\text{שעות}}{110} \times 208$, מעוגל לעשרות שקלים (לדוגמה: 72ש = 140 ₪, 64ש = 120 ₪, 51ש = 100 ₪, 47.5ש = 90 ₪ / 50 ₪).
   - **עקרון נסיעות יחיד בתפקיד כפול:** עובד בעל תפקיד כפול (כמו לאון) מקבל תשלום נסיעות **פעם אחת בלבד** (תחת קבלה עמודה D, ומאופס `None` תחת מדריך עמודה K).
3. **Salaried Group Classes vs Studio Classes (סעיף 22660 מול 22653):**
   - מאמנים שכירים (בטבלת השכר השחורה) משויכים **אך ורק תחת סעיף `22660 אימונים קבוצתיים`** (שורה 49).
   - שורה 52 (`22653 אימוני סטודיו` לשכירים) נשארת תמיד **0.00 ₪** (מאופסת).
   - שורה 53 (`22653 שיעורי סטודיו מאמני חוץ` - באדום) מיועדת **אך ורק למאמנות ומאמני חוץ עצמאיים**.
4. **Mixed Freelancer Invoices Itemization (פיצול מדויק של שורות חשבונית):**
   - עידו גליקו: שעות משמרת -> `22604` (שורה 56), אישיים -> `22650` (שורה 54), קבוצה/סטודיו -> `22653` (שורה 53), עמלות מכירת אישיים + בונוס -> `22650` (שורה 61).
   - נוי אסרף: אישיים -> `22650` (שורה 54), סטודיו -> `22653` (שורה 53).
   - עידן וקסר: ניהול מועדון 18,000 ₪ -> `22601` (שורה 57), אישיים 3,080 ₪ -> `22650` (שורה 54), סטודיו 300 ₪ -> `22653` (שורה 53), עמלת מכירה 1,000 ₪ -> `22650` (שורה 61).
   - ניר אייזנבך: ניהול מקצועי 4,000 ₪ -> 2,500 ₪ חדר כושר (`22655` / שורה 60) ו-1,500 ₪ פילאטיס (`181-22601` / שורה 51).
5. **Inactive Employee Clean Sweep (ניקוי מלא של עובד שסיים לעבוד):**
   - כאשר עובד מסיים לעבוד (כמו אורלי באומל), מבצעים ניקוי רוחבי של כל תא, שורה, טבלת עזר ונוסחת חיפוש המתייחסת אליו כדי למנוע שגיאות `#N/A`.
6. **Hours Comparison Table Alignment (יישור טבלת השוואת שעות):**
   - בטבלת השוואת שעות עבודה, כל המספרים מיושרים תמיד בטור אחד ישר בעמודה J (עמודה 10), ללא גלישה לעמודה K.
7. **Branch Isolation (הפרדה מוחלטת של סניפים):**
   - נעמה חיון וניקול אדלמן שייכות אך ורק לפילאטיס (דוח פילאטיס) ואינן מופיעות בדוח חילנט או עמלות של חדר הכושר.
   - עובדי חדר הכושר מופיעים אך ורק בדוח חדר הכושר.
8. **Live Dynamic Formula Preservation in Developer Charge (`חיוב יזם`):**
   - בגיליון `חיוב יזם`, כל תא סכום מכיל **נוסחת אקסל חיה ודינמית** המקושרת ישירות ל-`דוח מרכז לאישור מנהל` (לדוגמה `='דוח מרכז לאישור מנהל'!D50+'דוח מרכז לאישור מנהל'!D54`), לעולם לא מספר סטטי.
9. **Freelance Baseline Formula Shapes (נוסחאות בסיס מאמני חוץ):**
   - שורות מאמני החוץ ב-`דוח מרכז לאישור מנהל` נגזרות בנוסחאות דינמיות מתוך `סיכום אמוני סטודיו וקבוצה`:
     - שורה 53 (שיעורי סטודיו): `=SUM('סיכום אמוני סטודיו וקבוצה'!B3:B19)*'דוח מרכז לאישור מנהל'!P37`
     - שורה 54 (אישיים): `=SUM('סיכום אמוני סטודיו וקבוצה'!G3:L19)*'דוח מרכז לאישור מנהל'!O38`
     - שורה 55 (קבוצות): `=SUM('סיכום אמוני סטודיו וקבוצה'!C3:D19)*'דוח מרכז לאישור מנהל'!N38`
     - שורה 56 (ש"ע משמרת): `=SUM('סיכום אמוני סטודיו וקבוצה'!N3:N19)*$E$37`
10. **Pilates Clean Sales Table & Nicole Commission Wiring (עמלות פילאטיס וניקול אדלמן):**
   - בגיליון `סיכום אימונים ומכירות מנויים` בפילאטיס, המטריצה הישנה מיולי נמחקת ומוחלפת בטבלת עמלות אוגוסט נקייה.
   - עמלות המכירה של ניקול אדלמן מקושרות דינמית לשורה 26 עמודה C בטבלת העובדות (`='סיכום אימונים ומכירות מנויים'!C23`) ולשורה 47 בסעיפי התקציב (`='סיכום אימונים ומכירות מנויים'!C24`).
11. **Sales Commission National Insurance Multiplier & Special Effort (מכפיל ביטוח לאומי 1.08 ומאמץ מיוחד):**
   - בדוח מרכז חדר כושר ופילאטיס, סעיף עמלות מכירות, מנויים ושדרוגים (סעיף `22662` בחדר כושר וסעיף `181-22636` בפילאטיס) הנגזר מתוך גיליון ריכוז עמלות מכירה, מוכפל תמיד במקדם **`1.08`** (תוספת 8% ביטוח לאומי) **כולל רכיב ״מאמץ מיוחד״**.
   - בעת העברת הנתונים ל-`דוח בקרת שכר שכירים`, נלקחים המספרים **כולל (כולל 1.08 ומאמץ מיוחד)** — בדיוק כפי שהם מופיעים בדו״ח המרכז, לצורך סנכרון ותאימות מלאה (0 דלתא מול חיוב יזם).

## Self-documentation rules (Mandatory for all agent sessions)

1. After EVERY change you make, before claiming the task is done:
   a. Append an entry to `docs/BUILDER_LOG.md`
   b. Update `docs/SYSTEM_MAP.md` if the change affects any workflow, sheet, tab, column, trigger, integration, or data flow
   c. Commit the code AND the docs together (or as a separate docs commit)
2. Never commit secrets, API keys, or tokens into any file.
3. Write documentation in plain English a non-technical founder can read. Technical terms are allowed only with a one-line explanation.
4. Do not push to GitHub without explicit approval. Commit locally only, and tell the user the commit is ready to push.


