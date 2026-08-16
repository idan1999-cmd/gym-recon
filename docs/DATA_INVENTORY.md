<!--
═══════════════════════════════════════════════════════════════════════
  PROTECTED KNOWLEDGE FILE — DO NOT MODIFY WITHOUT OWNER APPROVAL
  Owner: Amit Swisa
  Status: source of truth for input-file structure
  Agents: READ this before writing any parser, changing sheet lookups,
          or assuming a column exists. You MAY append to "Change log".
          You MAY NOT rewrite or condense the sections above it.
          Findings here were verified by direct inspection of the client's
          real files — not inferred from code.
═══════════════════════════════════════════════════════════════════════
-->

# Data inventory — what the client actually sends

**Inspected:** July 2026, real client files (`Downloads` + `gym-recon/input`)
**Method:** direct read via `openpyxl` (read-only). Hebrew names preserved.
**Purpose:** separate what is **repeatable across gyms** from what is **unique to Idan**.

> This distinction is the entire basis of the product/service strategy.
> See `PRODUCT_STRATEGY.md` §3.

---

## 0. The headline

| | Files | Meaning |
|---|---|---|
| **Raw system exports** | 4 | Same shape at any gym using Priority / Hilan / Arbox. **Product surface.** |
| **Hand-built workbooks** | 3 | Idan's personal Excel craft. **Service surface.** |

**The engine currently parses *and writes back into* the hand-built layer.**
That is the single biggest source of fragility in the project.

---

## 1. `כרטסת.xlsx` — accounting ledger

**344 KB · RAW EXPORT (Priority / Electra ERP) · 0 formulas**

The system of record for actuals. Everything in תקציב מול ביצוע ultimately comes
from here.

### Structure
- Fixed 9-line preamble: `Electra` / `נכסי אריאל, עידן וקסר` / export timestamp /
  `תת חברה 1511, איי פלוס - סטריט מול בע"מ,` / `כרטסת` / `נכון לתקופה: …`
- Header at **row 16**
- Body = repeating blocks: `חשבון: 10180001-1511` → `יתרת פתיחה: 0.00` → `שח` rows → block total

### Four snapshot tabs — each a full year-to-date re-export

| Tab | Period covered | Rows | Accounts | Data lines |
|---|---|---|---|---|
| `7.6` | 07/06/2026 – 01/01/2026 | 1017 | 86 | 818 |
| `29.6` | 29/06/2026 – 01/01/2026 | 1039 | 86 | 851 |
| `6.7` | 06/07/2026 – 01/01/2026 | 1063 | 86 | 875 |
| `13.7` | 13/07/2026 – 01/01/2026 | 1184 | 90 | 988 |

> ### 🚩 Risk 1 — the schema is not stable between tabs
>
> Tabs `7.6`, `29.6`, `6.7` have **17 columns**:
> `מט. | יתרה מצטברת | זכות | חובה | חתימה | תאור פרויקט | פרויקט | סוג תנועה | מס. תנועת היומן | תאור חשבון נגדי | חשבון נגדי | פרטים | אסמכתא 3 | אסמכתא 2 | אסמכתא 1 | תאריך ערך | תאריך למאזן`
>
> Tab `13.7` has **7 columns**:
> `מט. | יתרה מצטברת | זכות | חובה | פרטים | תאריך ערך | תאריך למאזן`
>
> Same file, same client, same month. A parser tuned to one shape will
> silently mis-read the other. **Detect columns by header name, never by index.**

> ### 🚩 Risk 2 — tab choice changes the answer by ~₪240,000
>
> June net movement, by tab:
>
> | Tab | June net |
> |---|---|
> | `7.6` | ₪2,104.96 |
> | `29.6` | ₪48,319.98 |
> | `6.7` | ₪49,569.98 |
> | `13.7` | −₪194,755.58 |
>
> The engine currently takes **the last tab in the file** (`core/ledger.py:15`),
> chosen by whatever the bookkeeper happened to append last, and **logs nothing**.
> This must become an explicit, recorded decision. → `CLIENT_IDAN.md` Q4.

### Also worth knowing
- `פרטים` is free text and encodes the real period: `6/26 הכנסות מנויים`,
  `ידני ל-4-6/2026`, `קיזוז הכנסה החזר ללקוחות`, `ביטול ל 26248884`.
  This is why memo-month parsing exists.
- Tab `13.7` contains **2,008 hand-applied yellow cells** on חובה/זכות.
  Yellow means a human marked it. Do not treat formatting as data — but do not
  assume the file is untouched either.
- `כרטסת עמית.xlsx` is a **different** file (different hash), same 4 tabs —
  a working copy. Do not assume the two are interchangeable.

**Verdict: standardizable.** This is the strongest product input.

---

## 2. `פרויקטים _ דוח פרויקטים ספא…xlsx` — Hilan payroll

**35 KB · RAW EXPORT (Hilan) · 0 formulas · single tab `דוח פרוייקטים ספא`**

387 rows × 26 columns, flat table. Two lines per employee-day: a clock line and
a project line (`900014 / פיטנס סטריט מול`).

Columns from col 4:
`מס עובד | שם משפחה | שם פרטי | מחלקה | שם מחלקה | תאריך | יום בשבוע | כניסה | יציאה | סה"כ לשכר | רגילות | שנ 100% | שנ 125% | שנ 150% | סטודיו גדול (הסכם 680) | סטודיו קטן (הסכם 680) | אימון אישי (הסכם 680) | אימון קבוצתי (הסכם 680) | פרויקט | שם פרויקט | כניסה לפרויקט | יציאה מפרויקט | סה"כ שעות פרוייקט`

**This is the source of the `חילנט` tabs pasted inside `דוח מרכז`.**
Idan copies from here by hand every month. That paste step is pure manual labor
a product removes — connect to this file directly.

**Verdict: cleanest input in the entire set.** Most product-ready.

---

## 3. `דו״ח שיעורים.xlsx` — Arbox class report

**243 KB · RAW EXPORT + hand-built summaries**

Ten tabs. Raw pulls `14.6` / `23.6` / `7.7` / `13.7`, plus hand-made summaries
(`סיכום …`, `מערכת שבועית מסוכמת`, `שיעורי פרי פיט`).

Raw tab structure (147 rows, 0 formulas, 14 columns):
`תאריך | יום | שעת התחלה | שעת סיום | משך השיעור | סטטוס | חדר | מאמנים | הטלפון של המאמן | הטלפון של המאמן השני | סוג שירות | שיעור | קטגוריה | הרשמות`

- `סטטוס` drives billing — only `מתקיים` sessions count.
- `מערכת שבועית מסוכמת` is **his own analysis**: an hour × weekday grid with cells
  like `9 - חזק`, `8.3 - רווחי`, `5.5 - לא רווחי`. A bespoke profitability
  heuristic. Interesting as a future feature; not a data source.

**Verdict: raw tabs standardizable.** The multi-tab-per-file habit is his, not Arbox's.

---

## 4. Freelancer invoice PDFs

**6 files, 34–45 KB each, in `input/invoices/`**

`זוהר 1019` · `יעלה תורן40058` · `לירון ניסן 01000036` · `מיכל לוק 40001` ·
`ספיר הורוביץ 40002` · `עופרי יוגה 1002`

Filenames encode *name + invoice number*, spacing inconsistent. Arrive by email
or WhatsApp. Every gym has this problem.

`input/invoices_suppliers/` is **empty** — supplier OCR has never run on real data.

> ### 🚩 Risk 3 — shipped supplier cache is sample data
> `config/suppliers_ocr.json` contains fake entries (`חשמל_יוני2026.pdf`,
> `ELEC-06-2026`, ₪20,850). Because the file exists, `run_all.py` will happily
> generate a supplier approval workbook full of **fictional money** for any month.

**Verdict: standardizable.** Only the filename convention is local.

---

## 5. `תקציב תזרים 2026.xlsx` — the budget workbook

**175–181 KB · HAND-BUILT · ~500 formulas · 26–27 tabs**

This is the file Idan lives in, and the one the engine writes into.

### Three tab families

**(a) Cash-flow** — `תזרים 2025` (61r × 40c), `תזרים 2026` (38r × 38c)
Row 3 = month labels (`ינואר 26`…), row 4 = `תחזית`/`בפועל` pairs, 3 cols/month.
120 formulas, 377 cream-filled cells.

**(b) 20 hidden monthly supplier tabs** — see §6.

**(c) Budget vs actual** — the product surface:
- `תקציב מול ביצוע 2026 - מועדון` (63–65 rows)
- `תקציב מול ביצוע 2026 - פילאטיס` (49–52 rows)
- plus locked baselines `תקציב 2026 מאושר - …`

### Column layout (header row 2)

```
סעיף תקציבי | הכנסה | ינואר | ינואר - ביצוע | פברואר | פברואר - ביצוע | …
… | יוני | יוני - ביצוע | יולי | אוגוסט | … | דצמבר
| תקציב 2026 | סה"כ תקציב 1-5/26 | סה"כ ביצוע 1-5/26 | ביצוע מול תקציב | ביאורים
```

Pattern: **budget/actual pair for closed months, budget-only for future months.**

> ### 🚩 Risk 4 — the layout mutates every single month
>
> Verified between two versions of the same file:
>
> | Change | July version | Later version |
> |---|---|---|
> | July columns | `יולי` | `יולי - תכנון ראשוני` \| `יולי - תכנון עדכני` \| `יולי - ביצוע` |
> | YTD label (מועדון) | `1-5/26` | `1-6/26` |
> | YTD label (פילאטיס) | `1-5/26` | **`1-7/26`** |
>
> The two branch tabs are **inconsistent with each other inside the same file**.
> Writing into a target that reshapes monthly is a permanent maintenance tax and
> the strongest argument for emitting our own workbook instead.
> → `CLIENT_IDAN.md` Q6.

> ### 🚩 Risk 5 — `התאמה ידנית` does not exist in these files
>
> No column named `התאמה ידנית` was found in either budget tab.
> The manual/notes column present today is **`ביאורים`**.
>
> The engine's central safety contract — *"never overwrite `התאמה ידנית`"* —
> currently protects a column that is not in the client's workbook.
> `input/README.md` instructs him not to edit it. This must be resolved.
> → `CLIENT_IDAN.md` Q1. **Do not "fix" this in code before asking.**

### Account codes
- Club: income `80xxx`, expenses `22xxx` / `50xxx` / `90xxx`
  (`80001` מנויים, `80004` אימונים אישיים, `22604` עלות מאמנים, `22620` נציגת קבלה,
  `50103` עמלות אשראי)
- Pilates: income `81xxx`
- Rows 3–4 are **non-financial KPIs** (`כמות מנויים פעילים`, `כמות מנויים משלמים`) —
  do not sum them into money totals.

**Verdict: bespoke.** A product must **own** this layout, not parse it.

---

## 6. `מס"ב ספקים` tabs — supplier payment batch

**HAND-BUILT · 20 near-identical monthly tabs, all but the newest hidden**

> ### 🚩 Risk 6 — the tab naming convention changed twice mid-year
> `ספקים לתשלום 1.25` … `4.25` → `מס"ב ספקים 5.25` … `9.25` → `מסב ספקים 10.25` … `8.26`
> (spaces and quote marks differ). Any name-matching parser must handle all three.

### Structure (e.g. `מסב ספקים 8.26`, 84 rows × 12 cols)
- r3 `ספקים לתשלום`, r4 payment date + total, r5 `מזומן`, r6 `סה"כ`
- r9 header — only **3 real columns**: `שם ספק | סכום חשבונית | פרוט`
- Supplier blocks separated by blank rows, each closed by `=SUM(...)`:
  `סטריטמול` (ניקיון/חשמל/מים/דמי ניהול/ארנונה) · `אריאל ספא` · misc
  (`אגנטק`, `ארבוקס + ווטסאפ`, `אנרגים`, `מועצה מקומית רמת ישי`, `דורגז`,
  `יניב אינסטלטור`, `קופה קטנה`)
- Footer: `סה"כ חובות ספקים` = `=C28+C41+C61+C63+C64+C65` — hardcoded cell refs

### Yellow = approval, and it is precise
In `מסב ספקים 8.26` there are **exactly 12 yellow cells**, and all 12 are
human-decision cells: `מגדל` amount, `החזר הלוואה`, `נרקיס - הו"ק`, and the two
footer totals.

**Yellow is a genuine approval convention, not decoration.** Idan confirmed it:
*"ומאשר מולו (בצהוב) למי אני הולך לשלם במס״ב הבא."*

Also present: inline arithmetic left in cells (`=47355/7`) — a person calculating
in place. `פרוט` is free text encoding period + service (`5/26 ניקיון`,
`5-6/26 ארנונה שטחים משותפים`, `הסכם שנתי 2026 7 תשלומים, תש' 5/12`).

**Verdict: the *concept* is standardizable** (supplier batch + approve flag).
**The file is not.**

---

## 7. `דוח מרכז 06.26 …xlsx` — the approval report

**106 KB (חדר כושר) / 84 KB (פילאטיס) · HAND-BUILT · 239 formulas**

The monthly pack that goes to the boss. Two branch variants that have already
**diverged from each other**.

### Tabs
`ריכוז שעות` · `דוח מרכז לאישור מנהל` · `חילנט` · `חיוב יזם` · `מכירות` ·
`חגים` (794 rows) · several hidden

### `דוח מרכז לאישור מנהל` — employees are **columns**, not rows
- r4 `שם העובד :` → ניקול אדלמן, נועם תבל, לאון ורחובסקי…
- r5 `פירוט` → `נציגת קבלה` / `מדריך`
- Rows = `שעות רגילות`, `תעריף לפי 125%/150%/175%/200%`, `תשלום נסיעות בפועל`,
  `שונות (בונוס)`, `חיוב מאמנים שעות רגילות`…

Embedded **rate card** (r36–r45): `ברוטו עובד | סוציאליות 30% | סה"כ עלות מעביד | עלות חיוב לפרוייקט`,
with a parallel block for reception at **25%**. Two different burden rates, hardcoded in the sheet.

Embedded **reconciliation block** (r47–r58): `סה"כ שעות עבודה בחילנט 596.13` vs
`שעות עבודה בפועל 477.13` … `סה"כ שעות נטו 594.13`, `הפרש 2.00`.

> ### 🚩 Risk 7 — the engine's Hilan control is dead
> `tools/billing.py:95-103` calls `.cell()` on a `Workbook` object (no such
> method). A bare `except` swallows the error and returns `{system:0, actual:0, delta:0}`.
> The live `דגלים` sheet therefore reports **"0 מול 0 (Δ0)"** while the real
> numbers are **596.13 vs 594.13**.
> **A money control is reporting a false all-clear.** Fix before next delivery.

### Branch divergence (verified)
| | חדר כושר | פילאטיס |
|---|---|---|
| Employees on approval sheet | 9 | 2 |
| Extra row | — | `שעות ישיבות והשתלמויות` |
| `חילנט` tab origin | row 1 / col 2 | row 2 / col 4 |
| `חיוב יזם` codes | bare (`22620`) | prefixed (`181-22620`) |
| `חגים` tab | visible | hidden |

### `חיוב יזם` — **the real interface**
`מס סעיף | שם סעיף | סכום | הערות`
Totals: **124,467.9** (club) · **33,202.9** (pilates)

This small, account-coded table is the bridge from the operational workbook into
תקציב מול ביצוע. **This is the contract worth standardizing** — not the 10-tab
workbook around it.

`ריכוז שעות` is full of `#N/A` / `ERR` from broken lookups against `חגים`.
Client-side breakage that predates us.

**Verdict: deeply bespoke.** Highest-effort, lowest-reusability file in the set.

---

## 8. Derived / already-automated artifacts

| File | What it proves |
|---|---|
| `DRAFT_תקציב_מול_ביצוע_2026-06.xlsx` | Contains `_AUTO_LOG` (`sheet,row,code,name,amount,account,source_label,col`) and `_UNMAPPED` — an automated pipeline already ran |
| `_UNMAPPED` contents | 3 real failures: `22660 אימונים קבוצתיים 2,990` · `22655 ניהול מקצועי 2,500` · `22601 ניהול חדר כושר 22,000` — all *"no line match"*. **These are unmapped chart-of-accounts entries, i.e. per-client configuration.** |
| `gym_report_2026-06.csv` | Pipeline **output**: `שם מדריך \| סוג \| שיעורים (ארבוקס) \| שעות בארבוקס \| שעות בחילן \| סכום חשבונית \| צ'ק-אין ממוצע \| סטטוס בדיקה` with OK/WARN/ERROR |
| `תקציב מול ביצוע גרסה 2.xlsx` | The agent-freestyled rewrite — 2 tabs only, income sign inverted. **The incident that triggered the lockdown rules.** See `CLIENT_IDAN.md` §8. |

---

## 9. Duplicates and version traps

- `תקציב תזרים 2026 (1)` == `(2)` (identical hash) but **≠** the copy in
  `gym-recon/input` — input holds the **older** version (174,689 B vs 180,502 B).
  **Always confirm which version is current before a run.**
- `דוח מרכז … (1).xlsx` duplicates are byte-identical — safe.
- `כרטסת.xlsx` ≠ `כרטסת עמית.xlsx` — different hashes, same tab names.
- Loose CSV tab-exports in Downloads (`… - חילנט.csv`, `… - חיוב יזם.csv`) —
  evidence he exports individual tabs by hand.
- `עותק של כללי 01.26/02.26/03.26/12.25.xls` — legacy BIFF format,
  **not readable by openpyxl**. Not inspected.

---

## 10. Summary table — product surface vs service surface

| File | Type | Reusable at gym #2? | Notes |
|---|---|---|---|
| `כרטסת.xlsx` | Priority export | ✅ Yes | Watch 17-col vs 7-col drift; tab choice is material |
| `דוח פרויקטים` (Hilan) | Hilan export | ✅ Yes | Cleanest input; replaces a manual paste |
| `דו״ח שיעורים` raw tabs | Arbox export | ✅ Yes | 14 fixed columns |
| Invoice PDFs | Documents | ✅ Yes | Only filename convention is local |
| `תקציב תזרים 2026` | Hand-built | ❌ No | 26 tabs, ~500 formulas, layout mutates monthly |
| `מס"ב ספקים` tabs | Hand-built | ❌ No | 3 naming conventions, blank-row blocks, yellow = approval |
| `דוח מרכז` | Hand-built | ❌ No | Employees as columns, embedded rate card, branches diverged |

### The architectural conclusion

> **Read the raw exports. Own the outputs. Treat the hand-built workbooks as
> legacy artifacts to be replaced — not formats to be maintained.**

Four standard inputs in, our own clean workbook out, with `חיוב יזם` as the
account-coded interface contract. That is the shape of the product.

---

## 11. Consolidated risk register

| # | Risk | Where | Severity |
|---|---|---|---|
| 1 | Ledger schema differs between snapshot tabs (17 vs 7 cols) | §1 | High |
| 2 | Tab choice swings June by ~₪240k, chosen silently | §1 | **Critical** |
| 3 | Supplier OCR cache ships with fake data | §4 | High |
| 4 | Budget layout mutates monthly; branches inconsistent | §5 | High |
| 5 | `התאמה ידנית` does not exist in client files | §5 | **Critical** |
| 6 | Supplier tab naming changed twice | §6 | Medium |
| 7 | Hilan control silently dead — false all-clear | §7 | **Critical** |
| 8 | `input/` holds an outdated budget workbook | §9 | Medium |

---

## 12. Verified analysis — `קבצים ווקסר` (2026-07-31)

Ran directly against the client's own folder
`C:\Users\Amit\Downloads\קבצים ווקסר`. This section **supersedes** any earlier
assumption in this document where they conflict.

### 12.1 `התאמה ידנית` does not exist — confirmed

Scanned all **25 tabs** for `התאמה` / `ידנית` / `ביאור` / `הערות` in rows 1–8.

| Tab | Cell | Header |
|---|---|---|
| תקציב מול ביצוע 2026 - מועדון | `X2` | `ביאורים` |
| תקציב מול ביצוע 2026 - פילאטיס | `Y2` | `ביאורים` |
| תקציב 2026 מאושר - מועדון | `G2` | `ביאורים` |
| תקציב 2026 מאושר - פילאטיס | `G2` | `ביאורים` |

**Zero occurrences of `התאמה ידנית`.** The engine's central safety contract
protects a column the client does not have.

### 12.2 The two branch tabs are not aligned

Header row 2, from the same workbook:

```
מועדון  : A=סעיף תקציבי B=הכנסה C=ינואר D=ינואר-ביצוע … K=מאי L=מאי-ביצוע
          M=יוני  N=יולי  O=אוגוסט … S=דצמבר T=תקציב 2026
          U=סה"כ תקציב 1-5/26 V=סה"כ ביצוע 1-5/26 W=ביצוע מול תקציב X=ביאורים

פילאטיס : A=סעיף תקציבי B=הכנסה C=ינואר D=ינואר-ביצוע … K=מאי L=מאי-ביצוע
          M=יוני  N=יוני-ביצוע  O=יולי … T=דצמבר U=סה"כ תקציב שנתי 2026
          V=סה"כ תקציב 1-5/26 W=סה"כ ביצוע 1-5/26 X=ביצוע מול תקציב Y=ביאורים
```

> **מועדון has no `יוני - ביצוע` column.** The actual-column pattern stops at May
> on one tab and continues to June on the other. Everything downstream is shifted
> by one column between branches. Row-index or fixed-letter binding **cannot** work.

### 12.3 The 4 ledger tabs are progressive snapshots — earlier claim retracted

| Tab | Data rows | June rows | June net | Months covered |
|---|---|---|---|---|
| `7.6` | 816 | 12 | −41,424.44 | 01–06 |
| `29.6` | 849 | 45 | −318,143.87 | 01–06 |
| `6.7` | 873 | 61 | −318,644.99 | 01–07 |
| `13.7` | 987 | 113 | −302,278.11 | 01–07 |

Each tab is a **full YTD re-export**, strictly growing. `7.6` shows only 12 June
rows because it was pulled on 7 June — the month had barely started.

> **Correction:** the earlier "₪240k discrepancy between tabs" in §1 was an
> artifact of comparing incomplete snapshots. **Rule: always use the latest tab
> that covers the target month.** Still log which tab was used — but this is no
> longer a critical ambiguity.

### 12.4 Memo month must win — quantified

Tab `13.7`, 987 data rows:

| Measure | Count |
|---|---|
| Rows with a parseable month in `פרטים` | **440** (45%) |
| Rows where memo month ≠ balance month | **159** |
| Of those, exactly **+1 month** lag | **105** |
| Rows with **no** balance date at all | **90** |

Lag distribution (balance month − memo month):

| Lag | Rows |
|---|---|
| −1 | 21 |
| **0** | **281** |
| **+1** | **105** |
| +2 | 15 |
| +4/+5/+7 | 5 |
| −2 / −6 | 9 |
| −119 (typo years) | 4 |

Real examples — recurring monthly costs booked one month late:

```
'1/26 חשמל'      → balance 2026-02
'2/26 חשמל'      → balance 2026-03
'3/26 חשמל'      → balance 2026-04
'4/26 חשמל'      → balance 2026-05
'5/26 חשמל'      → balance 2026-06
'5/26 פלאקארד'   → balance 2026-07
'3/26 ריטיינר'   → balance 2026-04
```

This is a **systematic accrual lag**, not noise. The bookkeeper posts the invoice
when it arrives and writes the true service month in `פרטים`.

**Impact on June:**

| Rule | June net |
|---|---|
| Balance date first (current engine) | **−302,278.11** |
| Memo month first | **−273,626.46** |
| **Difference** | **₪28,651.65** |

> 🚩 The engine's current priority (`balance → memo → value`) is **backwards** for
> this client. Idan's question 3 was pointing straight at this.
> Correct order: **memo `פרטים` → `תאריך למאזן` → `תאריך ערך`**.

### 12.5 Two real bugs in `parse_memo_month`

| Input | Returns | Should be |
|---|---|---|
| `'05.06.26'` | `2006-05` ❌ | `2026-05` or `2026-06` |
| `'הסכם שנתי 2026 7 תשלומים, תש 5/12'` | `2012-05` ❌ | ignore (`5/12` = instalment 5 of 12) |

Correct results for the common cases:

| Input | Returns |
|---|---|
| `'5/26 הכנסות מנויים'` | `2026-05` ✅ |
| `'12/25 פלאקארד'` | `2025-12` ✅ |
| `'1-3/26 הסכם שירות'` | `2026-03` ✅ |
| `'5-6/26 ארנונה'` | `2026-06` ✅ |
| `'ידני ל-4-6/2026'` | `2026-06` ✅ |

**Fixes needed:** reject 2-digit years < 20 as years; ignore `n/m` where `m > 12`
and no year context (instalment notation).

### 12.6 Unmapped ledger accounts — not a coverage gap

90 ledger accounts; 58 match a budget code by suffix; **32 do not**.

All 32 are **balance-sheet accounts**, correctly outside a P&L budget:

| Prefix | Meaning | Count |
|---|---|---|
| `10999xxx` | clearing / suspense | 5 |
| `12050199` | fixed assets | 1 |
| `25xxxxxx` | payables | 7 |
| `33xxxxxx` | receivables / banks | 6 |
| `35002000` | equity | 1 |
| `37xxxxxx` | loans / related parties | 11 |
| `99999999` | unallocated | 1 |

**Conclusion:** the account map is not missing P&L lines. The engine should
**classify** these as out-of-scope rather than report them as failures.
The `_UNMAPPED` entries seen in `DRAFT_…xlsx` (`22660`, `22655`, `22601`) are a
different problem — those *are* P&L codes that failed **row matching** inside the
budget sheet, which is the branch-drift issue in §12.2.

### 12.7 What this changes

| Belief | Verdict |
|---|---|
| `התאמה ידנית` is the manual column | ❌ It is `ביאורים` |
| Ledger tabs conflict by ₪240k | ❌ Progressive snapshots; use the latest |
| Balance date is the right month rule | ❌ Memo must win — ₪28.6k on June alone |
| Unmapped accounts = missing config | ❌ They are balance-sheet, out of scope |
| Budget layout is stable within a file | ❌ The two branch tabs differ by one column |

---

## Change log

Append only.

| Date | Who | Change |
|------|-----|--------|
| 2026-07-31 | Amit + agent | Created from direct inspection of client files (Downloads + input) |
| 2026-07-31 | Amit + agent | Added §12 — verified analysis of `קבצים ווקסר`. Answered Q1/Q3/Q4, retracted the ₪240k tab claim, quantified the ₪28,651.65 memo-month impact, found 2 parser bugs |
