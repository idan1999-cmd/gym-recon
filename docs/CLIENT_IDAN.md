<!--
═══════════════════════════════════════════════════════════════════════
  PROTECTED KNOWLEDGE FILE — DO NOT MODIFY WITHOUT OWNER APPROVAL
  Owner: Amit Swisa
  Status: source of truth for client context
  Agents: READ this before touching money logic, sheet layouts, or cadence.
          You MAY append to "Change log" at the bottom.
          You MAY NOT rewrite, summarize, condense, translate, or delete
          any section above the Change log. If something here contradicts
          the code, the CODE IS WRONG until the owner says otherwise.
═══════════════════════════════════════════════════════════════════════
-->

# Client knowledge — Idan Wekser / A+ Street Mall

**Company:** איי פלוס — סטריט מול בע"מ (sub-company 1511, under נכסי אריאל, עידן וקסר)
**Facilities:** חדר כושר + סטודיו (club) and פילאטיס (separate budget)
**Primary contact:** Idan Wekser — `idan1999@gmail.com`
**Role:** operations/finance manager. He prepares; **his boss approves.**
**Relationship:** paid engagement, initial payment already requested/made (Bit).

---

## 1. Why this document exists

Every agent session so far has re-derived the same context from scratch, and some
sessions got it wrong (see §8). This file is the **single place** where Idan's
actual words, actual workflow, and actual pain points live.

**Read this before:**
- changing anything about `תקציב מול ביצוע`
- changing month attribution, signs, or rollups
- deciding what to build next
- pricing or scoping the engagement

---

## 2. Who Idan is and what he actually does

Idan is not an accountant. He is an operations manager who was handed a finance
workflow built out of Excel and manual habits. His job each week is to tell his
boss: *are we inside budget, and if not, where.*

His work splits into four recurring jobs:

| # | Job | Cadence | Ends with |
|---|-----|---------|-----------|
| 1 | **דוח מרכז** — reconcile trainer/employee hours and produce a charge sheet | Monthly | Boss approval |
| 2 | **תקציב מול ביצוע** — budget vs actual dashboard | **Weekly** | 30–60 min boss meeting |
| 3 | **מס"ב מדריכים** (+30) — make sure freelancer invoices got paid | Monthly | HQ processes payment |
| 4 | **מס"ב ספקים** (+60) — choose which suppliers get released | Monthly | Boss approves in yellow |

> ### ⚠️ Cadence correction
> The engine was built as a **monthly close**. Idan's own words for
> תקציב מול ביצוע are **"שוטף, שבועי"** — a weekly dashboard, reviewed in a weekly
> boss meeting. This is the most commonly missed fact in this project.
> **Job 2 is a weekly product.** Jobs 1, 3, 4 are monthly.

---

## 3. Data flow, in his words

Idan wrote this flow himself. It is the authoritative description of how data
moves. Everything the engine does must fit inside it.

```
Priority (ERP, work PC only)
  │  manual export → Google Sheets → shared to himself
  ▼
כרטסת  ─────────────────────────────► תקציב מול ביצוע (weekly dashboard)
                                       │  manual assignment to סעיפים
                                       │  manual "balancing" so it looks clean
                                       ▼
                                   Boss weekly meeting (30–60 min)

Hilan (חילנט)  ──manual paste──►  דוח מרכז ► חיוב יזם ► תקציב מול ביצוע
Arbox (דו״ח שיעורים) ──────────►  דוח מרכז          ▲
Freelancer invoices (mail/WhatsApp) ─┘                │
                                                      │
מס"ב מדריכים (+30) ───────────────────────────────────┘
מס"ב ספקים (+60) ── boss approves in yellow ── HQ pays
```

### Key constraints he stated

| Constraint | His words | Consequence for us |
|---|---|---|
| Priority is not accessible remotely | *"אין לי גישה אליו מהמחשב הפרטי"* | **No API. File upload is the only integration.** |
| Budget coding happens at bookkeeping | *"כאשר קולטים חשבונית... הם קולטים אותה על שיוך תקציבי מסוים"* | Our mapping must mirror their chart of accounts, not invent one |
| Club and Pilates are fully separate budgets | *"לכל מתחם יש תקציב משלו עם קודי שיוך אחרים"* | Never merge branches. Shared costs are **not** split by % |
| A trainer working both branches issues **two** invoices | *"אנחנו מבקשים 2 חשבוניות שונות"* | Do not "helpfully" merge trainer invoices |
| Invoice intake is physical | *"אני צריך להדפיס אותה, לחתום עליה ולרשום את הסעיף התקציבי ביד"* | Separate sellable module: digital coding + approval |

---

## 4. The admission that matters most

> **"אם צריך לאזן בין תקציבים כדי שהדו״ח ׳יראה יפה׳ (כלומר, שלא חרגתי באף סעיף
> תקציבי) אני מתקן ידנית ולפעמים גם מפספס."**

Translation: when a line is over budget, he **manually moves numbers between
budget lines** so nothing looks over — and sometimes he makes mistakes doing it.

This is simultaneously:

- **the value** — automating the tedious part is worth 3.5 h/week to him
- **the governance risk** — an automated system that silently re-balances budgets
  is producing a report that misrepresents reality to the boss

> ### 🚩 Rule
> **The system must never auto-balance budget lines.**
> It may *flag* an overrun and *propose* a reclassification.
> A human — Idan or his boss — approves it, and the approval is recorded.
> This is not a technical preference; it is the difference between a control
> tool and a tool for dressing up numbers.

---

## 5. Value statement — his words, unedited

> **"פגז אחי. וואו, כמה זמן אתה חוסך לי כאן.
> זה ברמה של משהו שאני יכול לעשות עכשיו על בסיס שבועי בקלות (5 דק׳ עבודה עם
> תובנות ברורות) במקום שעה בשבוע. לפחות 3.5 שעות של חיסכון בשבוע על הדבר הזה."**

| Metric | Value |
|---|---|
| Before | ~1 hour per week on תקציב מול ביצוע |
| After | ~5 minutes per week |
| Stated saving | **≥ 3.5 hours per week** ≈ **14 h/month** |
| Scope of that saving | **Only Job 2.** Jobs 1, 3, 4 are additional, untouched upside. |

This is the pricing anchor. It is a direct quote and should be used as such —
not rounded up, not extrapolated to other gyms.

---

## 6. Idan's 6 findings on תקציב מול ביצוע (verbatim + status)

He tested only the budget file. His raw text:

> 1. אם תראה בתחתית הדו״ח הוא הוציא לי נתונים שאני לא מצליח להבין מאיפה הוא הביא לינואר (גם בפילאטיס וגם במועדון).
> 2. בחודש יוני, היה גם חיוב וגם זיכוי תחת אותו הסעיף (זה קורה לעיתים) ואני רואה שהוא רק חישב את הזיכוי תחת אותו הסעיף.
> 3. לפי מה הוא מחשב את התאריך? לפי תאריך מאזן או תאריך לערך? (שניהם מופיעים בכרטסת) - כי לפעמים רושמים בהערות על איזה חודש מדובר (אני יודע, דפוק. אבל ככה זה). יש אופציה לבקש ממנו להתחשב בהערות אם יש?
> 4. חסר לי כאן מקום שיסכים לי תקציב מול ביצוע נוכחי מתחילת השנה עד לחודש הנוכחי (אם יש אופציה לעשות את זה נוכחי), גם שאדע מה הפער בהכנסות (לכל סעיף ולכל חודש בנפרד) וגם להוצאות.
> 5. עמודת סה״כ הכנסות והוצאות, לא מסכמת את המידע הנכון.
> 6. הבוס שלי מעדיף שעמודת הכנסות תעמוד כמספר שלילי והוצאות כפלוס. נוכל לוודא שהוא הופך את זה באופן קבוע?

| # | Issue | Engine status | Note |
|---|---|---|---|
| 1 | Phantom January rows at the bottom | ✅ Fixed | Uncoded pricing-note rows stripped; coded rows (80008) kept |
| 2 | Debit **and** credit on one סעיף — only credit counted | ✅ Fixed | Net = Σdebit − Σcredit, with regression test |
| 3 | Which date? מאזן / ערך / memo | ✅ Fixed | Priority: `תאריך למאזן` → memo `פרטים` → `תאריך ערך`. **See open question Q3.** |
| 4 | No YTD from start of year to current month | ✅ Fixed | YTD budget / actual / variance columns |
| 5 | Total income & expense rows wrong | ✅ Fixed | Rollups by code prefix + explicit סה"כ labels |
| 6 | Boss wants income negative, expenses positive | ✅ Fixed | Enforced on write |

**Delivered but not yet confirmed by Idan.** Nothing here is closed until he says so.

---

## 7. What he has NOT tested yet

He was explicit: *"כרגע ׳שיחקתי׳ רק עם התקציב תזרים."*

Untested by the client:

- Trainer billing / invoice OCR
- Supplier pack (+30 / +60)
- דוח מרכז reconciliation
- Anything multi-month or weekly-repeated

Treat all of these as **unvalidated with the customer**, regardless of test status.

---

## 8. Prior incidents — do not repeat

### Incident 1 — the agent rebuilt the workbook by hand

Idan was sent to clone `club-finance-recon` and drive it with a local AI agent
(Antigravity). Instead of running the pipeline, the agent **hand-built an Excel**
(`תקציב מול ביצוע גרסה 2.xlsx`) with:

- income flipped to **positive** (violates his boss's stated preference)
- a stripped 2-tab layout that discarded the real workbook structure
- numbers that did not come from the engine

**Root cause:** the agent had no hard instruction that money output must come
from the tool. Fixed via `AGENTS.md` + skill lockdown. Do not weaken that rule.

### Incident 2 — wrong product sent for the job

`club-finance-recon` produces **draft** Excel packs; it does not implement the
two-layer ledger sync Idan's 6 points require. The correct product for
תקציב מול ביצוע is **`gym-recon`** (`tools/ledger_sync.py`). See `SCOPE.md`.

---

## 9. Open questions — status after file analysis (2026-07-31)

Q1, Q3 and Q4 were **answered from the client's own files** — no need to ask.
Evidence and method in `DATA_INVENTORY.md` §12.

| # | Question | Status | Answer |
|---|---|---|---|
| **Q1** | Does `התאמה ידנית` exist? | ✅ **ANSWERED — NO** | Scanned all 25 tabs of `תקציב תזרים 2026.xlsx`. The column does **not** exist anywhere. The manual column is **`ביאורים`** (`X2` on מועדון, `Y2` on פילאטיס). The engine's two-layer contract currently protects a phantom column. |
| **Q2** | Weekly or monthly? | ⚠️ **Still ask** | His words say weekly. Engine is monthly. Cheap to confirm in one line. |
| **Q3** | Memo month vs balance date — which wins? | ✅ **ANSWERED — memo should win** | 440 of 987 rows carry a month in `פרטים`; **159 disagree** with the balance date, and **105 of those are exactly +1 month** — a systematic accrual lag (`5/26 חשמל` booked in June, etc.). Current code prefers balance date → **June is wrong by ₪28,651.65**. |
| **Q4** | Which כרטסת tab is authoritative? | ✅ **ANSWERED — the latest** | The 4 tabs are **progressive snapshots**, not competing versions. Each is a full YTD re-export with more rows than the last (June rows: 12 → 45 → 61 → 113). The latest tab (`13.7`) is a strict superset. My earlier "₪240k discrepancy" was **wrong** — it compared incomplete snapshots. |
| **Q5** | Idan or the boss approves spend? | ⚠️ **Still ask** | Commercial, not technical. |
| **Q6** | May we emit our own workbook? | ⚠️ **Still ask** | Now more urgent — see the branch-drift finding below. |

### 🔴 New finding — the two branch tabs have already drifted apart

In the **same file**, the same header row:

| | מועדון | פילאטיס |
|---|---|---|
| June actual column | ❌ **missing** (`M=יוני`, then `N=יולי`) | ✅ present (`M=יוני`, `N=יוני - ביצוע`) |
| Annual budget column | `T=תקציב 2026` | `U=סה"כ תקציב שנתי 2026` |
| YTD labels | `סה"כ תקציב 1-5/26` | `סה"כ תקציב 1-5/26` |
| Manual/notes column | `X=ביאורים` | `Y=ביאורים` |

**מועדון has no `יוני - ביצוע` column at all.** Idan had not yet added it when he
exported. Every column after June sits at a different letter on each tab.

This is the strongest possible argument for **Q6**: any engine that writes into
his workbook must handle a layout that differs *between two tabs of one file* and
changes shape every month.

---

## 10. Communication norms

- **Language:** Hebrew. He writes casually (*"אחי"*, *"פגז"*). Match the register.
- **Format:** short, numbered, concrete. He responds point-by-point.
- **Privacy:** he explicitly warned — *"לא להעביר את המידע הלאה כי יש כאן מידע אישי."*
  Client files contain names, tax IDs, salaries. Never commit them. Never paste
  them into third-party tools.
- **Tone:** he is enthusiastic and forgiving of bugs, but he is showing this to
  his boss. A wrong number in front of the boss costs far more than a late fix.

---

## 11. Full email transcript (verbatim, newest → oldest)

Preserved unedited as evidentiary record. Do not summarize or "clean up".

---

### Idan → Amit (after first run of the budget pipeline)

> קודם כל - כרגע ״שיחקתי״ רק עם התקציב תזרים.
>
> כמה דברים ראשונים ששמתי לב אליהם, מצרף לך את המסמך שהוציא לי.
>
> 1. אם תראה בתחתית הדו״ח הוא הוציא לי נתונים שאני לא מצליח להבין מאיפה הוא הביא לינואר (גם בפילאטיס וגם במועדון).
> 2. בחודש יוני, היה גם חיוב וגם זיכוי תחת אותו הסעיף (זה קורה לעיתים) ואני רואה שהוא רק חישב את הזיכוי תחת אותו הסעיף.
> 3. לפי מה הוא מחשב את התאריך? לפי תאריך מאזן או תאריך לערך? (שניהם מופיעים בכרטסת) - כי לפעמים רושמים בהערות על איזה חודש מדובר (אני יודע, דפוק. אבל ככה זה). יש אופציה לבקש ממנו להתחשב בהערות אם יש?
> 4. חסר לי כאן מקום שיסכים לי תקציב מול ביצוע נוכחי מתחילת השנה עד לחודש הנוכחי (אם יש אופציה לעשות את זה נוכחי), גם שאדע מה הפער בהכנסות (לכל סעיף ולכל חודש בנפרד) וגם להוצאות.
> 5. עמודת סה״כ הכנסות והוצאות, לא מסכמת את המידע הנכון.
> 6. הבוס שלי מעדיף שעמודת הכנסות תעמוד כמספר שלילי והוצאות כפלוס. נוכל לוודא שהוא הופך את זה באופן קבוע?
>
> חוץ מזה, פגז אחי. וואו, כמה זמן אתה חוסך לי כאן.
> זה ברמה של משהו שאני יכול לעשות עכשיו על בסיס שבועי בקלות (5 דק׳ עבודה עם תובנות ברורות) במקום שעה בשבוע. לפחות 3.5 שעות של חיסכון בשבוע על הדבר הזה.

---

### Amit → Idan — 26 July 2026, 20:03

> היי אחי
> בקצרה, המערכת עושה עבורך שלושה דברים: קוראת את כל חשבוניות המדריכים ומוציאה מהן את הנתונים אוטומטית (OCR, בלי הקלדה ידנית), מוצאת חריגות ואי-התאמות מול ארבוקס/חילן/דוח מרכז, ובסוף מייצרת לך דוח וטיוטת אקסל מוכנים להצגה לבוס - תקציב מול ביצוע.
>
> מה אתה צריך להתקין קודם - "סוכן AI" שמריץ את הקוד בשבילך
>
> חושבים על זה כמו על עוזר שיודע לקרוא קוד ולהריץ אותו במחשב שלך. הכי מומלץ לך: Google Antigravity.
>
> למה דווקא הוא?
>
> חינמי לגמרי (preview כרגע) ויש לך חשבון PRO אז בכלל יש לך מכסה גדולה.
> נכנסים אליו פשוט עם חשבון Gmail הרגיל שלך - אין צורך במנוי נוסף, אז לא צריך לשלם על Claude Pro בנפרד
> עובד על מק.
> קישור להורדה: https://antigravity.google/download
>
> תוודא שזה מוכן
> איך מריצים את המערכת עצמה:
>
> אחרי זה אתה שולח לו את הקישור הבא ומבקש ממנו שיתקין המערכת אצלך שים לב הקישור ייסגר אחרי מחר אז אם אתה מוריד אותו כבר היום זה מצויין.
> https://github.com/amitswsisa-cyber/club-finance-recon
> תבקש ממנו שיוריד את זה יש לסוכן שם את כל ההנחיות וכל הכישורים הוא כבר מכיר את הלוגיקה העסקית והקבצים שלכם. משם אתה אמור לדבר איתו כמו עובד דיגיטלי והוא אמור לעשות לך את הדברים. ואם יש בעיות תעדכן אותי ונבין.
>
> שים לב שמתי שם הנחיות לכל הסוכן AI שידע להנחות אותך למה שאתה צריך אבל זה לכל הפקודות.
>
> בוא נתחיל מזה - אחרי שזה רץ אצלך פעם אחת נראה יחד מה כדאי לשפר או להוסיף.

---

### Idan → Amit — 14 July 2026, 05:53

> מצרף לך סיכום חשבוניות מדריכים של חודש יוני. שתוכל לשחק על הכל. כמובן, לא להעביר את המידע הלאה כי יש כאן מידע אישי.
> תראה שהמערכת גם תדע לעבוד עם מסה וסוגי חשבוניות אחרים (מכל מיני גופים).

### Amit → Idan — 14 July 2026, 00:21

> היי אח תוכל לשלוח לי דוגמא לחשבוניות אני רוצה לראות אם זה יוכל לקרוא אותן ולהטמיע את הנתונים אוטמטית. תודה יאח ובוקר טוב (:

### Idan → Amit — 13 July 2026, 17:11

> מעולה, תגיד מה עוד צריך

### Amit → Idan — 13 July 2026, 17:04

> כן אחי לאט לאט הדברים יותר מתבהרים זה טוב ששלחת לי אותם זה נותן לי זמן לקרוא אותם, בכלל עוד הייתי יכול לשרוק אותם

---

### Idan → Amit — 13 July 2026, 16:23

> היי אחי,
> מצרף דו״ח שיעורים (כאן אני מוציא את השיעורים שיש בארבוקס - על מנת להשוות לחשבוניות שהם מביאים לי).
> מצרף גם דו״ח חילנ״ט לדוג׳ על חודש יוני (שעות עבודה של שכירים).
>
> לא צריכות להיות חריגות בדו״ח מרכז - הכל צריך לעלות בצורה תקינה. אם יש תקלות אני צריך לוודא איפה התקלה ולסדר אותה.
> גיליון ספקים לא מתעדכן כל שבוע - אבל שווה לחשוב על זה. הוא מקור צפוי.
>
> תקציב מול ביצוע מעמיד את הביצוע אל מול התקציב - מעין דשבורד ניהול שוטף.
>
> אתה מצליח להבין?

### Amit → Idan — 13 July 2026, 07:05

> היי אחי שולח לך עוד שאלות שהתחילו באיפיון,
> אשמח לדוח חילן כמה חשבוניונות לדוגמא שאבין גם איך הם שולחים לך אותם ואיך נראים הנתוינם מארבוקס או איך שאתה מיצא אותם.
> בנוסף אשמח לדעת מה קורה במידה ויש חריגות בדוח מרכז? אתה מסדר פשוט קומסטית ואז מציג לבוס? כאילו אין חריגות?
> האם גיליון "ספקים לתשלום" מתעדכן כל שבוע? האם הוא מקור האמת למה שצפוי לשלם, או שתקציב מול ביצוע הוא מקור טוב יותר?

---

### Idan → Amit — 7 July 2026, 15:56 — the full workflow answer

> יש לי כמה שאלות כדי להבין יותר לעומק את כל תהליך העבודה וזרימת הנתונים בין הקבצים:
>
> **איפה קובץ ה-Priority נמצא בדיוק יכול לתת לי שם מדוייק?**
> הקובץ נמצא בתוך מערכת ה Priority שאני צריך להוציא באופן ידני מתוך המחשב של העבודה, אין לי גישה אליו מהמחשב הפרטי. אני מעלה אותו לגוגל שיטס ומשתף עם עצמי.
>
> **איך נקבע לאיזה קוד ספק משויך כל נתון? האם הקודים נלקחים מדוח "מרכז חדר כושר" ו"דוח מרכז פילאטיס" לאחר אישור מנהל?**
> נכון, יש יישור קו על הקודים של כל הכנסה/הוצאה (קוראים לזה שיוך תקציבי).
>
> **כלומר, איך המערכת\אתה יודעת לאן לשייך כל הכנסה או הוצאה?**
> כאשר קולטים חשבונית במערכת (את זה הנהלת חשבונות עושה), הם קולטים אותה על שיוך תקציבי מסוים שהגדרנו להם (גם להכנסות וגם להוצאות). ברגע שזה עולה על השיוך התקציבי הנכון, אנחנו נראה את זה בקובץ ב Priority כמו שצריך ומשם נגזור לדוחות שלנו.
>
> **כיצד מתבצעת החלוקה של ההוצאות המשותפות בין חדר הכושר לסטודיו לפילאטיס? האם מדובר באחוז חלוקה קבוע?**
> לכל מתחם יש תקציב משלו עם קודי שיוך אחרים. מועדון וסטודיו לחוד, פילאטיס לחוד (גם שכר של מאמנים, בנפרד. לדוג׳ אם יש מאמן שעושה גם פילאטיס וגם אימוני סטודיו - אנחנו מבקשים 2 חשבוניות שונות).
>
> **לדוגמה: חשמל, מים, שכירות וכדומה.**
> כנ״ל, תקציב שונה.
>
> **מאיפה נמשכים הנתונים האלה?**
> כל הנתונים האלו מגיעים מה Priority, מאותו הדו״ח. אני קולט את החשבוניות מהספקים במייל או בווטסאפ (בין אם זה מאמנים או ספקים של שירותים - חשמל, גז).
>
> **אם הבנתי נכון, המטרה היא שכל הנתונים ייכנסו בסופו של דבר לשני דוחות "תקציב מול ביצוע" ולדאשבורד ויזואלי:** מדויק.
>
> תקציב מול ביצוע – פילאטיס.
> תקציב מול ביצוע – חדר כושר.
>
> כל הנתונים נמשכים מה - Priority, למעט דו״ח מס״ב וריכוז נוכחות עובדים (שכירים ועצמאיים). בונה לך למטה Flow Chart.
>
> ובזמנך אחי אשמח אם תוכל להעביר לי את התשלום לביט את התשלום ההתחלתי
> ככה או ככה אני כבר מתחיל לעבוד

**His flow chart, verbatim:**

> **דו״ח מרכז (בכל חודש)**
> מכיל בתוכו:
> - ריכוז נוכחות עובדים שכירים - שעות עבודה מכל מיני סוגים (עובר ידנית מדו״ח שאני מוציא מחילנ״ט)
> - ריכוז נוכחות עובדים עצמאיים - שעות עבודה מכל מיני סוגים (מדריכי חדר כושר, סטודיו ופילאטיס מכשירים - אני בניתי דו״ח שאני מרכז ידנית את כל החשבוניות של המדריכים ואז מעביר אותו ידנית לדו״ח המרכז)
> - ריכוז עמלות פקידי קבלה ומכירות - כמה כסף עשו בעמלות (ידנית, אני עושה חישוב מתוך טבלת המכירות. כרגע אין צורך לטייב את זה)
>
> הדו״ח מצליב את כל מה שאני הזנתי (מה שאני צפוי לשלם לפי הדיווחים שלהם) עם כל מה שאני יודע מהמערכת שאני צריך לשלם (ארבוקס וצפי חודשי קבוע) לוודא שאין חריגות או אי סדירויות ולרכז את כל החיוב שאנחנו צריכים להעביר לבוס שלי.
> הקובץ הזה נשלח לבוס שלי, לאישור שלו.
>
> **דו״ח תקציב מול תזרים (שוטף, שבועי)**
> זה ה Dashboard השוטף שאני מנהל. איתו אני צריך לעבוד על בסיס שבועי להבין אם אני עומד בתקציב שנקבע בתחילת השנה.
> הנתונים מגיעים באופן ידני מדו״ח שאני מוציא מ Priority כמו שכתבתי לך קודם. מצרף לך איך זה נראה. — כרטסת
> הם עוברים לסעיפים על ידי באופן ידני.
> אם צריך לאזן בין תקציבים כדי שהדו״ח ״יראה יפה״ (כלומר, שלא חרגתי באף סעיף תקציבי) אני מתקן ידנית ולפעמים גם מפספס.
> זה עובר לאישור הבוס שלי, בכל שבוע בפגישה שבועית של 30-60 דק׳.
>
> **דו״ח מס״ב ספקים מדריכים (שוטף + 30)**
> לאחר שריכזתי את כל החשבוניות של המדריכים, אני צריך לוודא שהם מקבלים תשלום (כלומר, שמישהי במטה שאני שולח לה את כל החשבוניות מזינה אותם לסעיף התקציבי הנכון ב - Priority ואני לא פספסתי אף חשבונית.
> מצרף לך איך אני מרכז את זה על בסיס חודשי. — בקרת חשבוניות עצמאיים איי פלוס
> היא מעלה את זה למחשב אצלהם, שולחת לתשלום בכל חודש.
>
> **דו״ח מסב ספקי שירות/מוצרים (שוטף +60)**
> עם ספרי שירות/מוצרים - ההתנהלות טיפה אחרת. אנחנו ״בוחרים״ למי לשחרר תקציב בהתאם לכמה שיש לי.
> אני עולה לבוס שלי עם ריכוז של כל חשבוניות הספקים בכל חודש (תראה את זה בגיליון מס״ב ספקים) ומאשר מולו (בצהוב) למי אני הולך לשלם במס״ב הבא.
> לאחר שאנחנו מאשרים, אני שולח את מה שמאושר למי שמטפלת בזה במטה.
>
> **חידוד חשוב** - כדי שאוכל לקלוט חשבונית אני צריך להדפיס אותה, לחתום עליה ולרשום את הסעיף התקציבי ביד. מאמין שגם כאן אפשר לייעל דיגיטלית..
> **התקציב תזרים 2026 הוא העדכני.**

---

## 12. Facts vs assumptions

Strict separation. Do not let assumptions drift into facts.

### Verified facts (his words or his files)
- Weekly cadence for תקציב מול ביצוע; monthly for the other three jobs
- Boss approves weekly (30–60 min) and approves supplier payments in yellow
- Priority export is manual, work-PC only
- Club and Pilates are separate budgets, separate codes, separate invoices
- He manually rebalances budgets and sometimes misses
- ≥3.5 h/week saved on Job 2 alone
- Invoice intake requires print + sign + handwritten code
- He has tested **only** the budget pipeline

### Assumptions (unconfirmed — do not build on these)
- That `ביאורים` is his manual column (Q1)
- That memo month should only apply when balance date is missing (Q3)
- That the newest כרטסת tab is authoritative (Q4)
- That other gyms use Priority + Arbox + Hilan
- That the boss would fund this directly

---

## Change log

Append only. One line per entry.

| Date | Who | Change |
|------|-----|--------|
| 2026-07-31 | Amit + agent | Created from full email transcript, workflow answers, and 6-point feedback |
| 2026-08-21 | Idan + agent | Clarified active month planning structure (תכנון ראשוני vs תכנון עדכני) and dynamic monthly roll-forward |
| 2026-09-03 | Idan + agent | Finalized August close: dynamic reception formulas (Leon 44.44h/Noam 51h), single travel allocation (no duplicate on dual roles), salaried classes strictly under 22660 (22653 salaried zeroed), mixed freelance line item splits (Ido Gliko, Noy Asraf, Idan Wekser), inactive employee complete sweep (Orly Baumel), and hours comparison table column J alignment. |

