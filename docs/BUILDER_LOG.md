# Builder Log — gym-recon

## How this project works in 2 minutes

`gym-recon` is the automated monthly finance and billing engine for **אריאל פיט & ספא בע"מ (A+ Street Mall)** (covering the Main Gym / Club and the Pilates Studio). 
Every month, the gym receives raw input files: an accounting general ledger (`כרטסת`), payroll reports from Hilan (`חילנט / פרויקטים ספא`), class schedules from Arbox, trainer freelance invoice PDFs, and supplier invoice PDFs. 
The system takes these raw inputs, performs automated OCR and three-way reconciliation (comparing invoice vs. schedule vs. agreed rate table), and deterministically produces the official financial deliverables:
1. **תקציב מול ביצוע (Budget vs. Actual):** Syncs real accounting ledger transactions into the official budget workbook without touching manual overrides or formulas.
2. **חיוב יזם & דוח מרכז לאישור מנהל (Trainer & Staff Billing):** Computes monthly charges for the property owner/developer across shifts, reception, personal training, studio classes, management fees, and sales commissions.
3. **ספקים לאישור מנהל (Supplier Payment Pack):** Matches supplier invoices against vendor terms (+30 / +60 days) and generates the manager approval workbook.
4. **דגלים (Audit & Flags):** Automatically flags rate mismatches, missing trainer receipts, unknown vendors, or hours variance so management can review exceptions without doing math by hand.
## 2026-09-05 — Weekly Schedule Timetable 2-Week Window & Month-Sync Fix

- **What changed:**
  1. **Fixed Weekly Schedule Window & Day Coverage (`dashboard/backend/data_service.py`):**
     - **Diagnosis:** In a 2-week window (14 calendar days), each weekday occurs exactly 2 times (only the starting boundary day can have 3). Because the recurrence filter was hardcoded to `min_occurrences >= 3`, every single weekday was stripped out except Monday (or Friday in July), creating the bug where only Mondays showed up!
     - Automatically adjusted `effective_min_occ = 2` when selecting `time_range == '2w'`, ensuring all 6 days of the week (ראשון עד שישי) populate with their regular recurring classes (57 slots) while still filtering out one-off replacements.
  2. **Month-Synced Schedule Analysis:**
     - Connected `get_schedule_analytics()` to the global `target_month` parameter from the top month navigator (`&month=...`).
     - In July (`month=7`), the analysis anchors to July 2026; in August (`month=8`), it anchors to August 2026.
  3. **Frontend Dynamic Banner & Month Hook (`dashboard/public/app.js` & `index.html`):**
     - `loadScheduleAnalytics()` now sends the selected `month` parameter.
     - `navigateMonth()` immediately reloads the schedule analytics when the user is on the schedule tab.
     - The filter notice banner dynamically displays the active occurrence threshold and date span (e.g. `17/08/2026 עד 31/08/2026`).
     - Bumped script version tag to `app.js?v=3.9`.
- **Why (what Idan asked for, in his words):**
  - *"ולמה כשאני הולך לגיליון של מערכת שעות ותפוסה, כשאני הולך שבועיים אחורה אני רואה רק את ימי שני? אני לא רואה שום דבר בנוסף לזה. תנסה לעשות בדיקה רגע. גם כשאני הולך ליולי ויוני זה אותו הדבר."*
- **What it touches:**
  - `dashboard/backend/data_service.py`, `dashboard/backend/server.py`, `dashboard/public/index.html`, `dashboard/public/app.js`, `docs/BUILDER_LOG.md`.

## 2026-09-05 — Facility Utilities & Maintenance Multi-Trend Tracking in Executive View

- **What changed:**
  1. **Backend 12-Month Trends Pipeline (`dashboard/backend/data_service.py`):**
     - Extended `get_annual_trends()` to compute 12-month trend arrays for facility operational categories across both branches:
       - **חשמל ומז״א (`22609`):** Full 12-month progression (showing the sharp summer spike from ~₪3.5k in winter to ~₪18.3k in July).
       - **מים (`22610`):** Monthly consumption trajectory across the club.
       - **הסכם שירות מיזוג אוויר (`22102`, `22607`):** Quarterly maintenance fee installments.
       - **ציוד, אחזקה ותקלות (`22618`, `22627`):** Technogym equipment, pilates beds, and facility fix expenditures.
       - **שיווק ופרסום (`22506`), ניקיון וחומרים (`22614`, `22613`), ארנונה (`22611`).**
  2. **Frontend Multi-Chart Visualizations (`dashboard/public/index.html` & `app.js`):**
     - Added **Chart 4: "מעקב הוצאות תפעול ומבנה: חשמל, מים, מיזוג, אחזקה ותקלות"** — ApexCharts multi-series column chart with color-coded legend tags (Amber for Electricity, Cyan for Water, Blue for HVAC, Rose for Maintenance/Equipment).
     - Added **Chart 5: "מגמת שיווק, ניקיון וארנונה לאורך השנה"** — Smooth multi-line chart for marketing and operational overhead.
     - Wired both charts to re-render seamlessly when switching between Combined Club, Main Gym, and Pilates Studio.
     - Bumped script cache tag to `app.js?v=3.8`.
- **Why (what Idan asked for, in his words):**
  - *"במגמות תקציב מול ביצוע, אני רוצה שנוסיף עוד כמה מדדים למעקב. אני רוצה שתר-אה לי גרף שמראה לי שינויים בהוצאות המשתנות שלי בהתאם לשנה, דברים כמו חשמל, מים, מיזוג אוויר, תקלות ואחזקה, שיופיע בתוך איזשהו גרף אחד מסודר, ככה יהיה לנו מעקב. ואם אתה רואה לנכון להוסיף עוד דברים שיהיו רלוונטיים מתוך התקציב מול תזרים, אז תשאל אותי כאן ובוא נוסיף."*
- **What it touches:**
  - `dashboard/backend/data_service.py`, `dashboard/public/index.html`, `dashboard/public/app.js`, `docs/BUILDER_LOG.md`.

## 2026-09-05 — High-Contrast Club Switcher & Visual Filter Separation

- **What changed:**
  1. **Fixed Active/Inactive CSS State Toggle (`dashboard/public/app.js`):**
     - In `setClub(club)`, replaced mismatched class removal (`bg-slate-900` vs `bg-zinc-900`) with a clean reset that clears inactive styles and applies uniform high-contrast styling (`bg-zinc-950 text-white shadow-md ring-1 ring-black/10`).
     - Added colored branch indicator dots (Emerald for Combined, Blue for Gym, Purple for Pilates) inside both the switcher pills and the active overview badge.
  2. **Active Filter Header Badge (`dashboard/public/index.html`):**
     - Added `#active-club-strip-badge` with `#active-club-strip-text` directly above the 4 main financial KPI cards, giving immediate feedback on whether figures represent Combined, Gym, or Pilates.
  3. **Contextual Banner Subtitles:**
     - Updated `renderMemberships()` in `app.js` so the membership snapshot subtitle dynamically reads "מנויי חדר כושר בלבד", "מנויי פילאטיס מכשירים בלבד", or "מועדון • פילאטיס" depending on the active club filter.
  4. **Browser Cache Busting:**
     - Updated script version tag to `app.js?v=3.7`.
- **Why (what Idan asked for, in his words):**
  - *"החלק הזה שבו בוחרים האם זה כל המועדון, חדר כושר או פילאטיס קצת לא נלחץ כמו שצריך, כשלוחצים על חדר כושר עדיין מופיע כל המועדון. תעשה שתהיה הפרדה יותר ברורה בזמן הלחיצה."*
- **What it touches:**
  - `dashboard/public/index.html`, `dashboard/public/app.js`, `docs/BUILDER_LOG.md`.

## 2026-09-04 — Direct Arbox API & Google Drive CRM Integration for Memberships, Freezes & Cancellations

- **What changed:**
  1. **Direct Arbox API & Cache Fallback (`dashboard/backend/data_service.py`):**
     - Connected `parse_membership_data()` to the live Arbox v2 API (`/users`) with persistent local caching in `config/arbox_users_cache.json`.
     - Accurately counts **852 total active members**, strictly partitioned by branch location IDs:
       - **Gym (`מועדון A+`, location 1054):** 696 active members.
       - **Pilates (`פילאטיס מכשירים`, location 7157):** 156 active members.
  2. **Automated Google Drive Sales CRM Integration:**
     - Connected `search_dirs` in `find_input_file()` to Google Drive CRM directories (`/Users/idanwekser/Gym-Sales-CRM/01_קבצי_קלט_לעיבוד` and `02_קבצי_פלט_CRM_ודוחות`).
     - Extracts freezes (211) and cancellations (154) directly from `הקפאות וביטולים` and its forecast schedules.
     - Extracts real average membership prices by branch from `ייבוא ארבוקס אוגוסט 2026`:
       - Gym: ₪1,209.5 (₪100.8/mo)
       - Pilates: ₪3,355.7 (₪279.6/mo)
       - Combined: ₪1,442.5 (₪120.2/mo)
     - Accurately computes future pending refunds (₪15,099.99 for September–November) rather than falling back to 0.
  3. **Multi-Month Sales Closers Matching (`_get_sales_closers`):**
     - Supports month-by-month sales performance lookup across tabs in both the local sales workbook and the Drive CRM file:
       - **May (מאי 26):** Nicole 53 deals (₪141k), Shir 17, Noam 14, Leon 8.
       - **June (יוני 26):** Nicole 62 deals (₪113k), Noam 29 (₪63k), Leon 24 (₪35k).
       - **July (יולי 26):** Nicole 54 deals (₪110k), Noam 42 (₪84k), Leon 32 (₪60k).
       - **August (אוגוסט / אוג 26):** Nicole 47 deals (₪98.5k), Noam 19 (₪35.6k), Leon 13 (₪20.4k).
  4. **Frontend Live Integration:**
     - Cleaned up the snapshot selector header in `index.html` and wired the top month switcher to dynamically refresh sales reps and monthly metrics.
- **Why (what Idan asked for, in his words):**
  - *"זה נראה שסטטוס מנויים וביטולים לא עובד, הוא מצליח להתחבר? הנתונים לא מופיעים."*
  - *"במקביל, בסטטוס מנויים וביטולים כתוב לך לשונית תאריך, אפשר להוריד את זה, אנחנו עכשיו עושים את זה תמיד בלייב... ונוכל לראות את הביצועים של אנשי המכירות בלייב בחודשים הקודמים."*
- **What it touches:**
  - `dashboard/backend/data_service.py`, `dashboard/public/index.html`, `dashboard/public/app.js`, `docs/BUILDER_LOG.md`.

## 2026-09-05 — Accurate Active Freezes, Pending Cancellations & Normalized Membership Pricing

- **What changed:**
  1. **Backend Membership Analytics (`dashboard/backend/data_service.py`):**
     - **Active Freezes Filter:** Filtered the cumulative 7-month log (211 historical records) strictly for currently active or pending freezes (6 pending manager/client + 18 with approved dates extending into September 2026 or later, total 24 active freezes). Past resolved freezes from May–July that already returned to activity are now properly excluded.
     - **Pending Cancellations Filter:** Filtered the historical log (154 cumulative records) strictly for pending cancellations (10 awaiting manager approval, 2 awaiting client confirmation, 16 approved and awaiting financial refund/credit, total 28 active cancellations: 27 Gym, 1 Pilates).
     - **Membership Price & Monthly Normalization:** Filtered sales items strictly for genuine memberships (`סוג פריט == 'מנויים'`), excluding single-visit passes, registration fees, and gear. Calculated real duration per item (annual = 12 mo, semi-annual = 6 mo, quarterly = 3 mo, monthly = 1 mo) to produce accurate average full contract value and true monthly cost:
       - **Main Gym:** ₪1,980.9 avg contract / **₪291.7/mo** (previously distorted at ₪101/mo).
       - **Pilates Studio:** ₪3,850.0 avg contract / **₪369.6/mo**.
       - **All Club:** ₪2,280.0 avg contract / **₪304.2/mo**.
  2. **Frontend UI Clarification (`dashboard/public/index.html`):**
     - Updated KPI subtitles to clearly state "הקפאות פעילות בהווה / ממתינות לאישור" and "ממתינים לאישור מנהל או זיכוי כספי".
- **Why (what Idan asked for, in his words if given):**
  - *"אני די בטוח שיש לך טעות כאן בסנכרון מול ה-Drive. שים לב שאין סיכוי שיש לנו 211 מנויים בהקפאה ו-148 ביטולים, אולי מדובר על ביטולים ישנים. שים לב רק לביטולים עתידיים ורק למנויים בהקפאה. המחיר הממוצע לחודש ומחיר המנוי הממוצע לא נשמע לי. תראה שאתה שולט בנתונים כמו שצריך, ואם צריך תשאל אותי ונווט את הדברים."*
- **What it touches:**
  - `dashboard/backend/data_service.py`, `dashboard/public/index.html`, `docs/BUILDER_LOG.md`.

---

## 2026-09-04 — Weekly Schedule Attendance Grid & Trainer Analytics in Executive Dashboard

- **What changed:**
  1. **Backend Schedule Analytics Engine (`dashboard/backend/data_service.py`):**
     - Added `get_schedule_analytics(club_filter, time_range, min_occurrences)` method.
     - Parses historical Arbox session files (July, August, dropzone) and de-duplicates records across files.
     - Supports 3 interactive time ranges: `2w` (last 2 weeks), `1m` (last month), `6m` (last 6 months).
     - Strict noise filter: filters out one-off substitutions and replacements by requiring $\ge 3$ occurrences for regular weekly slots.
     - Performs branch isolation: filters between Main Gym / Studio (`מועדון A+`) and Pilates Reformer Studio (`פילאטיס מכשירים`).
     - Aggregates weekly timetable grid by day (Sunday–Friday) and time slot with performance tiers:
       - Strong ($\ge 80\%$ occupancy)
       - Moderate ($65\% - 80\%$ occupancy)
       - Weak ($< 65\%$ occupancy)
     - Ranks trainer performance: session count, average attendees, average occupancy %, and late cancels.
  2. **REST API Endpoint (`dashboard/backend/server.py`):**
     - Exposed `GET /api/schedule_analytics?club=...&range=...&min_occurrences=3`.
  3. **Frontend Dashboard UI (`dashboard/public/index.html` & `dashboard/public/app.js`):**
     - Added 5th view mode button: **"מערכת שעות ותפוסה"** (`#view-schedule`).
     - Added branch isolation selector, range selector, and sub-mode toggle (Weekly Timetable Grid vs. Trainer Analytics).
     - Added 4 KPI cards (average occupancy, weak slots count, peak hour/day, top trainer).
     - Rendered interactive 6-day timetable grid with color-coded slots, coach names, attendee numbers, and substitute badges.
     - Rendered full trainer analytics cards grid with performance tier badges and class breakdowns.
  4. **Automated Unit Tests (`tests/test_schedule_analytics.py`):**
     - Added test suite validating gym analytics, pilates analytics, noise filtering, and time ranges.
- **Why (what Idan asked for, in his words if given):**
  - *"אני אעדיף שהתצוגה שאתה נותן לי של שיעורים חלשים חזקים תעשה את זה בצורה של מערכת שעות שבועית ולא בתצוגה של רשימה, זה יותר קל להסתכל על זה ככה. ואני אשמח שגם תעשה לי סנן שנותן פילוח של שבועיים אחורה, חודש אחורה וחצי שנה אחורה. שים לב לסנן מהתצוגה שיעורים שיש בהם רק מופע אחד או שניים, זה מעט מדי בשביל לקבל על זה איזשהו ערך ברור וככל הנראה מדובר בהחלפה. ותבצע הפרדה בין הפילאטיס מכשירים למועדון, אלו שני שיעורים שונים. ותבנה תצוגה גם למאמנים לחוד וגם לשעות השיעורים לחוד. ואת כל הדבר הזה אני מאשר שאתה יכול להכניס ישירות לתוך הדאשבורד."*
- **What it touches:**
  - `dashboard/backend/data_service.py`, `dashboard/backend/server.py`, `dashboard/public/index.html`, `dashboard/public/app.js`, `tests/test_schedule_analytics.py`, `docs/SYSTEM_MAP.md`, `docs/BUILDER_LOG.md`.

---

## 2026-09-03 — Billing Knowledge Law: Shift Hours Formula Bonus Exclusion & Section 22662 Isolation

- **What changed:**
  - Codified and locked **Rule 12** in `AGENTS.md` and updated `output/דו״ח מרכז חדר כושר אוגוסט 26.xlsx`:
    1. **Shift Hours Formula Clean-up (Rows 25 & 26):** Removed the bonus cell references (`+E13`, `+C13`) from the salaried trainers and reception shift hours formulas in sheet `דוח מרכז לאישור מנהל`. The formula now strictly computes base shift hours + overtime $\times$ hourly rate + travel (`+E11`), without adding bonus hours.
    2. **Section 22662 Bonus Aggregation (Row 62):** All bonuses, special effort, and sales commissions are isolated and calculated strictly under **סעיף תקציבי 22662 (עמלות מכירות, מנויים ושדרוגים)** at the bottom of the report (`=SUM(C31:L31)+SUM(C13:L13)`).
- **Why (what Idan asked for, in his words if given):**
  - *"אני צריך שכשאתה מבצע את הדוח המרכז של חדר כושר, שתשים לב שבחיוב שעות מאמנים בגיליון של דוח מרכז לאישור מנהל, לא תיקח בחשבון את השעות בונוס. תוריד משם את החישוב של הנוסחה, תיקח רך ורק את מה שמופיע לך לחישוב שעות בנוסחה, תוריד את כל מה שקשור לבונוס. הבונוס צריך להופיע בנפרד בסוף הגיליון תחת עמלות מכירות מנויים ושדרוגים שזה סעיף תקציבי 22662."*
- **What it touches:**
  - `AGENTS.md` (Rule 12), `output/דו״ח מרכז חדר כושר אוגוסט 26.xlsx`, `docs/BUILDER_LOG.md`.

---

## 2026-09-03 — Billing Knowledge Law: Sales Commissions Multiplier (1.08) & Special Effort Sync

- **What changed:**
  - Codified and locked **Rule 11** in `AGENTS.md` and engine specification:
    1. **Summary Report (`דוח מרכז`):** When extracting sales commissions from the raw sales commission summary sheet, the base amount **must be multiplied by 1.08 (including the "מאמץ מיוחד" / special effort component)** for both Gym (item `22662`) and Pilates (item `181-22636`).
    2. **Salaried Control Report (`דוח בקרת שכר שכירים`):** When transferring commission figures to the salaried payroll control report, take the numbers **inclusive** (with the 1.08 multiplier and special effort), exactly matching the summary report for 100% developer reconciliation (0 delta).
- **Why (what Idan asked for, in his words if given):**
  - *"שים לב לחדד לעצמך כשאתה עושה את הדוח המרכז, את המכירות, אחרי שהוצאנו אותם מהריכז עמלות מכירה מהגיליון שאני מצרף לך, אתה חייב להכפיל אותם ב-1.08 כולל מאמץ מיוחד. כשאתה מעביר את הנתונים לדוח בקרת שכירים, לקחת את המספרים כולל - כמו שמופיע בדו״ח המרכז. אין צורך לעדכן, רק תעדכן אצלך ברישומים."*
- **What it touches:**
  - `AGENTS.md` (Rule 11), `docs/BUILDER_LOG.md`.

---

## 2026-09-03 — Salaried Payroll Control Workbook Automation (`ריכוז בקרת שכר שכירים 08.26.xlsx`)

- **What changed:**
  1. **Clean August Control Template:**
     - Created `input/dropzone/ריכוז בקרת שכר שכירים 08.26.xlsx` with active tab `אוגוסט`, wiping old July numbers.
  2. **Employee Employer Cost Population (All-Inclusive):**
     - Populated all 8 Gym employees (Column E `סטריט מול`) and 2 Pilates employees (Column F `סטריט מול פילאטיס`) with full employer cost, including wages, overtime, travel allowance, bonuses (מאמץ מיוחד), and sales commissions (+8% B.L.):
       - **לאוניד ורחובסקי** (Row 6): **`8,056.50 ₪`** (Combined reception 4,118.50 ₪ + gym shifts 3,938.00 ₪).
       - **ערד קוצר** (Row 13): **`12,110.58 ₪`** (Shifts 4,934.38 ₪ + travel 200 ₪ + sales 16.20 ₪ + PT 4,950 ₪ + groups 2,210 ₪).
       - **איתן בראב** (Row 46): **`4,762.50 ₪`** (Shifts 3,662.50 ₪ + travel 100 ₪ + PT 1,100 ₪).
       - **גלעד וייס** (Row 80): **`2,230.00 ₪`** (Shifts 1,375 ₪ + travel 100 ₪ + bonus 195 ₪ + PT 660 ₪).
       - **בר סידס** (Row 91): **`2,297.50 ₪`** (Shifts 1,012.50 ₪ + travel 150 ₪ + bonus 165 ₪ + PT 990 ₪ + groups 130 ₪).
       - **אופל מיוני** (Row 98): **`6,429.50 ₪`** (Shifts 4,879.50 ₪ + travel 150 ₪ + PT 770 ₪ + groups 780 ₪).
       - **ניב בן חיים** (Row 100): **`5,416.50 ₪`** (Shifts 5,086.50 ₪ + travel 150 ₪ + PT 330 ₪).
       - **נועם תבל** (Row 101): **`4,880.90 ₪`** (Reception 3,587.50 ₪ + travel 100 ₪ + sales 1,193.40 ₪).
       - **נעמה חיון** (Row 12 - Pilates Col F): **`13,470.00 ₪`** (Studio classes 13,320 ₪ + travel 150 ₪).
       - **ניקול איידלמן** (Row 63 - Pilates Col F): **`10,327.50 ₪`** (Hours 7,233.10 ₪ + travel 200 ₪ + sales 2,894.40 ₪).
  3. **Bottom Multi-Layer Reconciliation Validation:**
     - Gym (Col E):
       - Row 103 (`סה״כ שכר`): `46,183.98 ₪`
       - Row 104 (`שכר שכירים מדוח יזם`): `46,183.98 ₪` -> Row 105 Difference = **`0.00 ₪`**
       - Row 108 (`חיצונים דוח יזם`): `66,224.48 ₪`
       - Row 109 (`שונות ניהול מקצועי ניר`): `2,500.00 ₪`
       - Row 110 (`סה״כ דיווח גבייה`): `114,908.45 ₪`
       - Row 111 (`הפרש דוחות גבייה ויזם`): `=E103+E108-E110+E109` = **`0.00 ₪`**
     - Pilates (Col F):
       - Row 103 (`סה״כ שכר`): `23,797.50 ₪`
       - Row 104 (`שכר שכירים מדוח יזם`): `23,797.50 ₪` -> Row 105 Difference = **`0.00 ₪`**
       - Row 108 (`חיצונים דוח יזם`): `4,792.90 ₪`
       - Row 110 (`סה״כ דיווח גבייה`): `28,590.40 ₪`
       - Row 111 (`הפרש דוחות גבייה ויזם`): `=F103+F108-F110` = **`0.00 ₪`**

- **Why (what Idan asked for):**
  - *"העליתי לך קובץ שקוראים לו ריכוז בקרת שכירים... אני רוצה שנלמד איך למלא אותו. קודם כל - רק עבור האנשים שלנו... יחד עם התייחסות לעצמאיים בסיום הדו״ח."*
  - *"עלות מעביד מלאה אבל שכוללת את עמלות המכירה, בונוסים, נסיעות - הכל כולל הכל כולל 1.08% חיוב ביטוח לאומי. לאון סכום מאוחד... שכר שכירים מדו״ח יזם מושכים מסך הכל ששילמנו על שכירים... שורה 109 שמים ניהול מקצועי... ו-111 צריכה להראות 0."*

---


- **What changed:**
  1. **Purged Duplicate Deliverable Files:**
     - Streamlined `output/` to contain strictly the 4 official deliverable workbooks (`דו״ח מרכז חדר כושר אוגוסט 26.xlsx`, `דו״ח מרכז פילאטיס אוגוסט 26.xlsx`, `תקציב_מול_ביצוע_חדר_כושר.xlsx`, `תקציב_מול_ביצוע_פילאטיס.xlsx`).
     - Removed obsolete duplicate files (`חיוב_חדר_כושר.xlsx`, `חיוב_פילאטיס.xlsx`, and background templates).
  2. **Live Dynamic Excel Formulas in `חיוב יזם` (Both Branches):**
     - Transformed all developer charge amount cells (Column F / 6) into live dynamic Excel formulas pointing directly to `דוח מרכז לאישור מנהל` (e.g. `='דוח מרכז לאישור מנהל'!D50+'דוח מרכז לאישור מנהל'!D54`), preserving interactive auditability.
  3. **Salaried Breakdown Linkage (Gym Row 47 to 52):**
     - Connected salaried expense rows directly to Column N summary (`=N26`, `=N25`, `=N29`, `=N27`, `=N28`), dynamically reflecting reception (6,936.80 ₪), gym shifts (21,051.60 ₪), group classes (3,120.00 ₪), and personal training (10,848.75 ₪).
  4. **Freelance Baseline Formula Shapes (Gym Rows 53 to 56):**
     - Restored authentic July baseline formula syntax for external trainers:
       - Row 53 (Studio): `=SUM('סיכום אמוני סטודיו וקבוצה'!B3:B19)*'דוח מרכז לאישור מנהל'!P37`
       - Row 54 (PT): `=SUM('סיכום אמוני סטודיו וקבוצה'!G3:L19)*'דוח מרכז לאישור מנהל'!O38`
       - Row 55 (Groups): `=SUM('סיכום אמוני סטודיו וקבוצה'!C3:D19)*'דוח מרכז לאישור מנהל'!N38`
       - Row 56 (Shifts): `=SUM('סיכום אמוני סטודיו וקבוצה'!N3:N19)*$E$37`
  5. **Pilates Clean Sweep (Racheli Boim & Lihi Kinar Roster Purge):**
     - Removed all remnants, names, and formulas referencing Racheli Boim and Lihi Kinar from `סיכום אימונים ומכירות מנויים`.
     - Active Pilates roster strictly consists of the 7 active external instructors (Dafna, Linoy, Moran, Noy Freund, Sivan, Sapir, Noam Shalev).
  6. **Pilates Sales Table Replacement & Dynamic Linking:**
     - Completely purged the old July horizontal sales matrix from `סיכום אימונים ומכירות מנויים`.
     - Inserted clean August sales commission table with Naama Hayon (0 ₪) and Nicole Edelman (2,894.40 ₪ via `=2680*1.08`).
     - Connected Nicole's sales commission dynamically to Row 26 Col C in the top employee approval table (`='סיכום אימונים ומכירות מנויים'!C23`) and to Row 47 (`='סיכום אימונים ומכירות מנויים'!C24`).
  7. **Gil Tal Invoices Consolidated & Renamed:**
     - Merged `דרישת תשלום #1001` (5 PT @ 130 = 650 ₪) and `דרישת תשלום #1002` (4.75 shift hours @ 50 = 237.5 ₪) into a single standard PDF: `החשבונית של גיל טל 1001-1002.pdf`.
     - Removed individual parts and duplicates from `input/dropzone/invoices/`.

- **Why (what Idan asked for, in his words):**
  - *"כי בסופו של דבר החיוב יזם בתמונה הזו, צריך לקבל את המידע מהדוח מרכז לאישור מנהל."*
  - *"וגם כאן - שתהיה נוסחה דינאמית, לא רק מספר סטטי. זה שאתה יודע, זה מעולה - אבל צריך להראות את זה כמו שצריך."*
  - *"תוריד את רחלי בויים מהמצבה בפילאטיס מכשירים ואת ליהי כינר. תמחק כל התייחסות משם. ושים לב שהטבלה של המכירות בפילאטיס מכשירים היא טבלה ישנה! תצרף רק את הטבלה החדשה של החודש שעשיתי (של אוגוסט) עם העמלות של ניקול ונעמה."*
  - *"זו הטבלה הישנה!!!! בפילאטיס מכשירים. אותה תמחק מהגיליון."*
  - *"ראיתי שכל הנוסחאות שעשית לגבי אימונים אישיים של מאמני חוץ וראשי קבוצה של מאמני חוץ, אני לא בטוח שהנוסחאות תקינות. תוודא רגע מול הדוחות הישנים שיש לנו שעשינו כבר ביולי... תבדוק אותה רגע ותראה מה הפערים."*
  - *"שים לב שבדו״ח מרכז פילאטיס איבדת את הנוסחא וההתייחסות למכירות של ניקול! צריך למשוך בצורה נכונה מהטבלה שצרפנו."*
  - *"שים לב שצרפתי לתיקייה חשבוניות אחרונות של גיל טל. תאחד אותן ותשנה שם. אין צורך לעדכן יותר את הדו״ח המרכז."*

- **What it touches:**
  - `jobs/billing_output.py`, `tools/billing.py`, `input/dropzone/invoices/`, `AGENTS.md`, `docs/SYSTEM_MAP.md`, `docs/CLIENT_IDAN.md`, `docs/BUILDER_LOG.md`.

- **How it was verified:**
  - Regenerated all workbooks using `tools/billing.py`.
  - Inspected cell formulas in Python with `openpyxl` (data_only=False) to verify dynamic links.
  - Verified `החשבונית של גיל טל 1001-1002.pdf` contains both pages and is readable.

---
## 2026-09-03 — August Close Finalization: Reception Dynamic Formulas, Single Travel Allocation, 22660 Salaried Class Rules, and Hours Comparison Alignment

- **What changed:**
  1. **Dynamic Reception Formulas (Leon & Noam):**
     - Connected Row 6 in Gym `דוח מרכז לאישור מנהל` for reception staff directly to `סיכום אמוני סטודיו וקבוצה` via dynamic Excel formulas (`='סיכום אמוני סטודיו וקבוצה'!P23` for Noam Tevel 51h, and `='סיכום אמוני סטודיו וקבוצה'!P22` for Leon Verkhovsky 44.44h).
     - Row 26 (חיוב קבלה) computes tiered wages dynamically: Noam 3,617.50 ₪ + Leon 3,319.30 ₪ = **6,936.80 ₪** (Row 47), replacing old static July cache (60h / 8,630 ₪).
  2. **Single Travel Allowance Principle (No Duplicate Travel on Dual Roles):**
     - Fixed travel allowance allocation so that employees with dual roles (e.g. Leonid Verkhovsky working both reception and gym shifts) receive travel allowance **once only** (under reception Col D, 208.50 ₪, and zeroed/None under instructor Col K).
  3. **Salaried Group/Studio Classes Classification (Line 22660 vs 22653):**
     - Enforced business law that salaried instructors' group/studio classes belong **strictly under 22660 (`אימונים קבוצתיים` - Row 49)**.
     - Row 52 (`22653 אימוני סטודיו` for salaried staff) is permanently zeroed at **0.00 ₪**.
     - Row 53 (`22653 שיעורי סטודיו מאמני חוץ`) is reserved strictly for freelance external trainer invoices.
  4. **Granular Multi-Line Freelance Invoice Itemization:**
     - Ido Gliko (Invoice 40011): 11 shift hours @ 55 ₪ (605 ₪ -> Row 56), 106 PT (11,660 ₪ -> Row 54), 3 group (450 ₪ -> Row 53), 2,415 ₪ PT sales commission + 565 ₪ bonus (2,980 ₪ -> Row 61).
     - Noy Asraf (Invoice 40024): 14 PT (1,540 ₪ -> Row 54), 8 studio (1,200 ₪ -> Row 53).
     - Idan Wekser (Invoice 40558): 18,000 ₪ management (Row 57), 28 PT (3,080 ₪ -> Row 54), 2 studio (300 ₪ -> Row 53), 1,000 ₪ sales commission (Row 61).
     - Nir Eisenbach: 4,000 ₪ professional management split 2,500 ₪ Gym (Row 60) and 1,500 ₪ Pilates (Row 51).
  5. **Orly Baumel Complete Workbook Sweep:**
     - Swept all helper tables, summary sheets, and lookup formulas across both workbooks, completely eliminating any `#N/A` or unreferenced lookup rows.
  6. **Hours Comparison Table (`השוואת שעות עבודה`) Column Alignment:**
     - Aligned all comparison table values (Hilan 490.25, actual 375.25, studio 0, group 24, PT 91, net 490.25, delta 0.00) strictly in **Column 10 (J)**.
     - Cleared column 11 (K) and horizontal offset cells, ensuring a clean, straight, professional table.
  7. **Header & Title Sync:**
     - Updated Gym manager sheet header from `נוכחות יוני 26` to **`נוכחות אוגוסט 26`**.
- **Why (what Idan asked for, in his words):**
  - *"ושים לב ששמת ללאון 60 שעות קבלה, אבל בגיליון של סיכום אימוני סטודיו הצהרנו שיש לו 44 שעות קבלה. תעדכן בהתאם."*
  - *"הוא לא יכול לקבל נסיעות פעמיים! רק תחת אחד מהם."*
  - *"כי מאמנים שכירים (מה שבשחור) צריכים להיות רק תחת אימונים קבוצתיים 22660."*
  - *"שים לב שתחת ש״ע חדר כושר מאמני חוץ יש לך גם שעות של עידו גליקו ונוי. בעמלות מכירות אישיים - חיצוני, יש גם את עידן."*
  - *"שים לב שאם אנחנו מוחקים עובד שלא עובד אצלנו יותר, למחוק כל התייחסות אליו כי אז הנוסחאות לא תקניות. אורלי באומל."*
  - *"ושים לב שיש לך עמודות שקפצו כאן, תמחק ותסדר אותן."*
- **What it touches:**
  - `jobs/billing_output.py`, `config/branches.json`, `config/invoices_ocr.json`, `AGENTS.md`, `docs/SYSTEM_MAP.md`, `docs/CLIENT_IDAN.md`, `docs/BUILDER_LOG.md`.
- **How it was verified:**
  - Full billing pipeline executed for Month 8.
  - Verified Gym approval total = 114,908.45 ₪, Pilates approval total = 31,652.20 ₪.
  - Verified Leon Col D Row 6 = 44.44h, Row 11 = 208.50 ₪; Col K Row 11 = None.
  - Verified hours comparison table in Column J with 0.00 delta.

---



- **What changed:**
  1. **Standardized & Renamed Uploaded Invoices:**
     - Converted receipt images to PDF and standardized names:
       - `החשבונית של לנה ברואון 19.pdf` (3 studio classes x 150 ₪ = 450.00 ₪).
       - `החשבונית של רן קיסלוב 0396.pdf` (12 shift hours x 50 ₪ = 600.00 ₪).
       - `החשבונית של נוי פרוינד 80166.pdf` (2 reformer + 1 mat = 430.00 ₪).
  2. **Updated OCR Configuration & Config Lines:**
     - Added the 3 new invoice records to `config/invoices_ocr.json`.
     - Added `"pilates"` category to `config/branches.json` under `external_lines` for Pilates branch.
  3. **Verified Gil Tal Status (גיל טל):**
     - Confirmed that Invoice 1002 (237.5 ₪) covers only **4.75 hours of Gym shifts** (3.8.26).
     - Verified that in Arbox August report (`דו״ח שיעורים אוגוסט 2026.csv`), Gil Tal conducted **5 Studio/Group classes** (TRX and A+ Endurance on 4.8, 10.8, 24.8, 25.8, 31.8) for which **no invoice has been submitted yet**.
  5. **Orly Baumel Removed:**
     - Cleared Orly Baumel completely from Row 12 of `סיכום אמוני סטודיו וקבוצה` as her employment ended.
  6. **Gym Hilan Sheet Isolation:**
     - Excluded Naama Hayon and Nicole Edelman from the Gym `חילנט` sheet, leaving strictly the 7 Gym employees and the Gym grand total (490.25 hrs).
  7. **Gilad Weiss & Bar Sidis Travel & Special Effort Bonuses (מאמץ מיוחד):**
     - Gilad Weiss (Col 8 in Gym `דוח מרכז`): Travel allowance = 100.00 ₪, Special Effort Bonus (מאמץ מיוחד) = 195.00 ₪.
     - Bar Sidis (Col 9 in Gym `דוח מרכז`): Special Effort Bonus (מאמץ מיוחד) = 165.00 ₪, Travel = 100.00 ₪.
  8. **Travel Allowance Tier Refinement (60–90 Hours = 150 ₪):**
     - Refined travel allowance brackets across both branches:
       - `< 60` hours: **100.00 ₪**
       - `60 – 90` hours: **150.00 ₪** (e.g. Bar Sidis 66h, Niv Ben Haim 64h, Opel Meyoni 63h, Naama Hayon 72h)
       - `> 90` hours: **200.00 ₪** (e.g. Arad Kotzer 122.75h, Nicole Edelman 103.33h)
       - Leonid Verkhovsky: **208.50 ₪** (fixed contract)
  9. **Idan Wekser Receipt (#40558) Ingestion:**
     - Renamed uploaded receipt to `החשבונית של עידן וקסר 40558.pdf` (Total ₪22,380 before VAT: ₪18,000 management, 28 PT @ 110 = ₪3,080, 2 studio @ 150 = ₪300, ₪1,000 sales commission).
     - Connected 28 PT and 2 studio to Row 5 (`עידן וקסר`) in `סיכום אמוני סטודיו וקבוצה`.
  10. **Official Deliverable File Renaming & Output Directory Cleanup:**
     - Created clean official deliverable workbooks in `output/`:
       - `output/דו״ח מרכז חדר כושר אוגוסט 26.xlsx`
       - `output/דו״ח מרכז פילאטיס אוגוסט 26.xlsx`
     - Removed all temporary/test files (`_t_*.xlsx`, `test_*.xlsx`, `~$*.xlsx`, temporary json dumps) from `output/`.
- **Why (what Idan asked for, in his words if given):**
  - *"לגבי נסיעות, תעשה שמי שעושה בין 60-90 שעות, יקבל 150 ש״ח נסיעות."*
- **What it touches:**
  - `jobs/billing_output.py`, `output/חיוב_חדר_כושר.xlsx`, `output/חיוב_פילאטיס.xlsx`, `docs/BUILDER_LOG.md`.
- **How it was verified:**
  - Verified Bar Sidis, Niv Ben Haim, Opel Meyoni, and Naama Hayon receive 150 ₪.
  - Verified Arad and Nicole receive 200 ₪, Leonid receives 208.50 ₪, Eitan and Noam receive 100 ₪.
  - All 94 automated tests passed (0 failures).

---

## 2026-08-31 — Annual Supplier Contract Badging & Multi-Month Recognition

- **What changed:** 
  - Configured and deployed an automated **Annual / Multi-Month Supplier Contract Badging System** across the dashboard (excluding courses/workshops per Idan's direction):
    1. **Contract Registry & Detection:** Automatically tagged supplier agreements (e.g. `22618` - Agentech / Telefire equipment service in 7/12 installments, `22615` - Electra HVAC quarterly contract, `22606` - Annual insurance amortization).
    2. **Card & 12-Month Table Badges:** Added clean badges (🏷️ `הסכם שנתי / תשלומים`, `הסכם שנתי / רבעוני`, `פוליסה שנתית בפריסה`) next to category titles on main cards and in the 12-month summary matrix.
    3. **Drilldown Modal Callout:** Integrated a banner callout in the item drilldown displaying contract description, payment cadence, and installment breakdown alongside genuine ledger receipts.
- **Why (what Idan asked for, in his words if given):** 
  - *"תבצע. לדעתי אין צורך אבל על קורסים והשתלמויות."*
- **What it touches:** 
  - `dashboard/backend/data_service.py`, `dashboard/public/app.js`, `dashboard/public/index.html`, `docs/BUILDER_LOG.md`.
- **How it was verified:** 
  - Verified API returns `is_contract: true` for Agentech equipment maintenance, Electra HVAC, and Insurance.
  - Verified UI rendering of contract badges on cards, 12-month table, and modal callout box.

---

## 2026-08-31 — Real Accounting Ledger Drilldown Transactions & Forecast Precision

- **What changed:** 
  - Overhauled the modal drill-down breakdown system to display **100% genuine accounting transactions** from `כרטסת` across all budget codes (such as `22614` - נקיון) and all months (January–August):
    1. **Real General Ledger Transactions:** Extracted exact transaction date, supplier/counter-account name, invoice memo, and amount from `כרטסת 31.8.26.xlsx` across all 12 months for every income and expense line.
    2. **Typo Resilience in Memos:** Clamped 2-digit years in `_resolve_year` (`core/common.py`) to the plausible lifecycle (2020..2030) with fallback to default year (e.g. correctly resolving bookkeeper typo `2/36 נקיון` to February 2026).
    3. **Closed vs. Live Month Forecasts:** Aligned smart forecasts so past closed months (months 1–7) display their exact finalized actuals (`ביצוע סופי - חודש סגור`), avoiding daily run-rate extrapolation multipliers on past months.
    4. **Live UI Refresh:** Updated `data_service.py`, `app.js`, and `core/ledger.py` with automatic deduplication.
- **Why (what Idan asked for, in his words if given):** 
  - User uploaded modal screenshot showing generic trainer shifts listed under *אחזקת מכשירים/מיטות פילאטיס* and inflated run-rate projection on a closed month.
- **What it touches:** 
  - `core/ledger.py`, `dashboard/backend/data_service.py`, `dashboard/public/app.js`, `dashboard/public/index.html`, `docs/BUILDER_LOG.md`.
- **How it was verified:** 
  - Verified drilldown for Pilates equipment maintenance returns 3 real ledger transactions totaling ₪813.65 for July.
  - Verified closed-month forecast matches exact actuals.

---

## 2026-08-31 — Cumulative Multi-Month Ledger Sync (June, July, August Actuals)

- **What changed:** 
  - Enhanced `jobs/ledger_output.py` (`build`) to sync all historical and current ledger movements ($1 \dots N$) from `כרטסת 31.8.26.xlsx` into the output budget workbooks, instead of updating only the single target month:
    1. **June & July Actuals Restored:** Ingested exact ledger transactions across all budget items for June (₪245.5k revenue, ₪265.1k expenses) and July (₪237.7k revenue, ₪244.8k expenses).
    2. **Rollup & Sign Integrity:** Recalculated subtotal rollups (`סה"כ הכנסות`, `סה"כ הוצאות`, `רווח/הפסד`) and enforced income negativity ($\le 0$) across all months.
    3. **YTD Recalculation:** Recomputed cumulative YTD figures through August (`סה"כ תקציב 1-8/26`, `סה"כ ביצוע 1-8/26`, `ביצוע מול תקציב`).
    4. **Dashboard Synchronization:** Synchronized data service across months 1–8.
- **Why (what Idan asked for, in his words if given):** 
  - *"למה בתקציב מול ביצוע לא מופיע לי הביצוע של יוני ויולי?"*
- **What it touches:** 
  - `jobs/ledger_output.py`, `output/תקציב_מול_ביצוע_חדר_כושר.xlsx`, `output/תקציב_מול_ביצוע_פילאטיס.xlsx`, `docs/BUILDER_LOG.md`.
- **How it was verified:** 
  - Verified June actuals (₪200,994.06 club rev, ₪44,567.80 pilates rev) and July actuals (₪190,931.36 club rev, ₪46,758.47 pilates rev) in generated Excel sheets.
  - Verified dashboard summary endpoints return full actuals for June, July, and August.

---

## 2026-08-31 — Ingestion of Updated Ledger (31.8.2026) & Clean Deliverables Sync

- **What changed:** 
  - Synced the updated accounting ledger: `כרטסת 31.8.26.xlsx` across the pipeline and dashboard data service:
    1. **Account Mapping Updates:** Added `10181006` (Pilates external PT income) to `config/account_map.json` and excluded non-operating holding prefixes (`18150`, `18190`), achieving 0 unmapped ledger accounts.
    2. **Ledger Sync Run:** Ran `tools/ledger_sync.py` to regenerate the official `output/תקציב_מול_ביצוע_חדר_כושר.xlsx` and `output/תקציב_מול_ביצוע_פילאטיס.xlsx` workbooks.
    3. **Clean Deliverables in Output:** Removed all temporary test files (`_t_*.xlsx`, scratch JSONs, lock files) from `output/` (`📤_דוחות_מוכנים_פלט/`), leaving exclusively the official deliverables:
       - `תקציב_מול_ביצוע_חדר_כושר.xlsx`
       - `תקציב_מול_ביצוע_פילאטיס.xlsx`
       - `תקציב תזרים 2026.xlsx`
    4. **Dashboard Synchronization:** Restarted dashboard backend server to reflect all synced figures.
- **Why (what Idan asked for, in his words if given):** 
  - *"אני הולך להעלות בפניך כרטסת עדכנית - בבקשה תעדכן לי את הדשבורד וגם את דו״ח תקציב תזרים ותעלה לי אותם בפלט. תמחק את הקבצים האחרים כרגע בפלט."*
- **What it touches:** 
  - `config/account_map.json`, `output/`, `📤_דוחות_מוכנים_פלט/`, `docs/BUILDER_LOG.md`.
- **How it was verified:** 
  - Verified `ledger_sync.py` exited with 0 errors and 0 unmapped accounts.
  - Verified `output/` directory contains only the 3 official workbooks.
  - Verified live dashboard responsiveness and data payload.

---

## 2026-08-30 — Ingestion of Updated Cancellations & Freeze Supplement CSV

- **What changed:** 
  - Connected and prioritized the updated cancellations file: `תוספת למכירות 2026 - לצורך עדכון צפי ביטולים והקפאות.csv`.
  - Updated `safe_float` in `data_service.py` to strip currency symbols (`₪`, `$`, `€`, `NIS`), ensuring exact refund amount calculation across formatted currency cells.
  - Correctly parsed:
    - **Total Requests Tracked:** 383 cancellations / freeze requests.
    - **Approved & Pending Refunds:** 46 requests totaling **₪15,105.00**.
    - **Completed Refunds:** 311 requests totaling **₪119,227.36**.
    - **Total Tracked Refunds:** **₪135,702.36**.
    - Linked sales closers from `מכירות 2026.xlsx` to maintain live performance metrics.
- **Why (what Idan asked for, in his words if given):** 
  - *"הקובץ שצרפתי לא היה מספיק מעודכן. תשתמש בדו״ח מכירות שצרפתי לך כרגע לטובת דשבורד הביטולים וההקפאות העתידי קוראים לו ״תוספת למכירות 2026 - לצורך עדכון צפי ביטולים והקפאות״."*
- **What it touches:** 
  - `dashboard/backend/data_service.py`, `docs/BUILDER_LOG.md`.
- **How it was verified:** 
  - Verified API payload returns `תוספת למכירות 2026 - לצורך עדכון צפי ביטולים והקפאות.csv` with ₪15,105.00 pending and ₪119,227.36 completed refunds.
  - Verified live frontend updates in Chrome.

---

## 2026-08-30 — Universal Ingestion for CSV Memberships Reports & Dynamic Sales Workbooks

- **What changed:** 
  - Enhanced `data_service.py` to seamlessly detect, parse, and ingest both **`.csv` and `.xlsx`** input files across all naming conventions:
    1. **Memberships CSV & XLSX Support:** Detects Arbox raw CSV exports (`דו״ח מנויים.csv`, `דוח מנויים.csv`, `*מנוי*.csv`, `*memberships*.csv`) with automated encoding fallbacks (`utf-8-sig`, `utf-8`, `cp1255`), correctly parsing all 781 subscriber records, 726 active members, 27 frozen, and 28 upcoming cancellations.
    2. **Sales & Cancellations Flexibility:** Supports spaces and varied sheet names in the CRM sales workbook (`הקפאות וביטולים`, `הקפאותביטולים`, `לידים אוגוסט 2026`, etc.) with intelligent multi-row header detection across rows 1 to 5.
    3. **Automated Search Scope:** Searches `input/dropzone/`, `📥_לגרור_לכאן_את_קבצי_החודש/`, `input/`, and root folders, prioritizing the newest modified file timestamp.
- **Why (what Idan asked for, in his words if given):** 
  - *"הכנסתי לך לתיקייה דו״ח מכירות (שבתוכו יש הקפאות וביטולים) ודו״ח מנויים. תעדכן לי את הדשבורד - לדעתי הוא לא קלט אותו כי הם לא בשמות הנכונים."*
- **What it touches:** 
  - `dashboard/backend/data_service.py`, `docs/BUILDER_LOG.md`.
- **How it was verified:** 
  - Verified `parse_membership_data` parses `input/dropzone/דו״ח מנויים.csv` (726 active members, 596 Gym, 130 Pilates, active snapshot 28.8).
  - Verified `parse_sales_cancellations` parses `input/dropzone/מכירות 2026.xlsx` (383 requests, ₪19,403.32 in refunds, 4 sales closers).
  - Verified HTTP API returns 200 OK and live browser refresh shows updated metrics.

---

## 2026-08-24 — Custom Revenue & Expense Forecast Editor (Per Club & Unified)

- **What changed:** 
  - Added dedicated **"ערוך תחזית" (Edit Forecast)** action buttons to both the **תחזית הכנסות לסוף חודש** and **תחזית הוצאות לסוף חודש** KPI cards.
  - Implemented the interactive **Projection & Forecast Modal (`#projection-modal`)** allowing executive overrides:
    1. **Per-Club Precision:** Allows editing forecasts separately for **כל המועדון (מאוחד)**, **חדר כושר**, and **פילאטיס מכשירים**.
    2. **Calculated vs. Custom:** Displays the run-rate/ledger calculated projection baseline with a single-click "החל תחזית מחושבת" reset button.
    3. **Visual Indicator:** Displays an executive `מוגדר` badge whenever a custom forecast override is active for that club/month.
  - Updated backend (`data_service.py` & `server.py`) to persist and apply projection keys (`{club}_projected_revenue_{month}` and `{club}_projected_expenses_{month}`) in `config/custom_targets.json`.
- **Why (what Idan asked for, in his words if given):** 
  - *"חושב שכדאי לבנות כזה בעתיד, בוא תכניס לי בינתיים כפתור שבו אני יכול לערוך את צפי ההכנסות/ההוצאות לסוף החודש. כמובן למועדון, לפילאטיס ולשני הסניפים - כל אחד בנפרד."*
- **What it touches:** 
  - `dashboard/backend/data_service.py`, `dashboard/backend/server.py`, `dashboard/public/index.html`, `dashboard/public/app.js`, `docs/BUILDER_LOG.md`.
- **How it was verified:** 
  - Tested setting and resetting custom forecasts via HTTP POST and verifying immediate reactivity in the UI.
  - Verified branch isolation between All, Gym, and Pilates.
  - Validated syntax with `jsc` and ran automated test suite.

---

## 2026-08-24 — Brand Identity System Redesign (A+ Street Mall / Premium Club by Ariel Properties)

- **What changed:** 
  - Overhauled the entire UI theme and design system based on the official A+ Premium Club logo:
    1. **Brand Palette:** Deep Executive Obsidian Carbon (`#18181B` / `#09090B`), Signature Vivid Crimson Red (`#E51937` / `#E11D48`), Restrained Emerald (`#10B981`), and Crisp Ice White/Zinc surfaces.
    2. **Official Logo Integration:** Rendered and integrated the official high-resolution A+ Premium Club vector logo (`dashboard/public/logo.png`) into the header.
    3. **Executive Visuals:** Replaced generic blue elements across navigation tabs, view switchers, KPI cards, AI pulse banner, and action buttons with sleek carbon/crimson styling.
    4. **ApexCharts Color Harmonization:** Harmonized annual trend charts, distribution bar charts, and timeline charts to the Crimson, Emerald, and Dark Carbon palette.
    5. **YTD Matrix Totals & Dynamic Highlighting:** Fully integrated YTD totals column and multi-layer summary footer in the financial matrix table.
- **Why (what Idan asked for, in his words if given):** 
  - *"עכשיו בוא נעבוד קצת על העיצוב. אני רוצה שתיקח את הצבעים של הלוגו המעודכן שלנו - מעלה לך אותו כאן. תבסס את כל הצבעים של הדף שלנו עליו. תעשה אותו מקצועי ויפה - לא מצועצע. סומך עליך."*
- **What it touches:** 
  - `dashboard/public/index.html`, `dashboard/public/app.js`, `dashboard/public/logo.png`, `docs/BUILDER_LOG.md`.
- **How it was verified:** 
  - Verified clean rendering of logo.png in the sticky navigation header.
  - Verified ApexCharts re-rendering with new brand palette.
  - Validated syntax with `jsc` and ran full automated test suite (all 94 tests passed).

---

## 2026-08-24 — Live Memberships Status, Branch Breakdown, Future Cancellations & Refund Forecasting Module

- **What changed:** 
  - Added a complete **סטטוס מנויים וביטולים (Memberships & Cancellations Status)** executive module to the dashboard (`dashboard/public/index.html` & `dashboard/public/app.js`):
    1. **Active Memberships Breakdown:** Displays 731 total active members (604 Main Gym / Club vs. 127 Pilates Reformer) with visual branch share comparison bars.
    2. **Frozen Memberships Breakdown:** Displays 31 total frozen members (19 Main Gym vs. 12 Pilates Reformer) with percentage of total base.
    3. **Future Cancellations Pipeline:** Displays 30 total members with upcoming cancellation dates (21 Main Gym vs. 9 Pilates Reformer) plus monthly target distribution timeline.
    4. **Average Pricing Metrics:** Computes average full membership price (₪2,719 Gym vs. ₪4,073 Pilates) and average monthly price (₪263.5/mo Gym vs. ₪358.0/mo Pilates).
    5. **Expected Refund Forecasting (צפי החזר כספי):** Directly syncs from the `הקפאותביטולים` table in `מכירות 2026.xlsx`, tracking ₪18,415 in approved refunds pending payment and ₪114,867 in completed refunds.
    6. **Interactive Drilldown Tables:** Added searchable, filterable tables for upcoming member cancellations with matched refund amounts, plus a full log of cancellation/freeze requests.
    7. **Multi-Snapshot Historical Selector:** Added dropdown allowing executive switching across all date tabs (e.g. `23.8`, `16.8`, `9.8`, `30.7`, `27.7`, `23.7`, `20.7`) to track changes across weeks.
  - Implemented high-performance file parsing and timestamp-based in-memory caching (`_cache`) in `dashboard/backend/data_service.py` reducing repeat API latency to <20ms.
  - Recorded memory note for future integration of historical past-cancellations reports.
- **Why (what Idan asked for, in his words if given):** 
  - *"יש כמה דברים שאני ארצה להוסיף כאן לדשבורד, אחד מהם זה סטטוס על המנויים שלי... מס׳ מנויים פעילים בחלוקה לפי סניפים (פילאטיס מכשירים ומועדון), מס׳ מנויים בסטטוס הקפאה... מס׳ מנויים בסטטוס ביטול עתידי והתייחסות לתאריך הביטול העתידי + הצפי להחזר כספי... חישוב של מחיר מנוי ממוצע לפי סניף... וחישוב של מחיר ממוצע לחודש לפי סניף... בהמשך אולי אכניס לך דו״ח ביטולי עבר, תרשום לנו בזיכרון."*
- **What it touches:** 
  - `dashboard/backend/data_service.py`, `dashboard/backend/server.py`, `dashboard/public/index.html`, `dashboard/public/app.js`, `docs/BUILDER_LOG.md`, `docs/SYSTEM_MAP.md`.
- **How it was verified:** 
  - Verified API endpoint `GET /api/data` returns all membership statistics, snapshot list, future cancellation list, and refund forecasts.
  - Tested branch filtering (All / Gym / Pilates) and snapshot tab switching across dates.
  - Verified sub-20ms cached response times over HTTP.
  - Ran the complete test suite (all 94 automated tests passed).

---

## 2026-09-02 — Salaried Total Wage Net Shift Deduction, Overtime (125/150/175/200) & Live Hilan Tab Sync

- **What changed:**
  1. **Salaried Shift & Reception Hours Calculated from Total Wage (שעות משכר):**
     - Updated deduction formula to use `סה"כ לשכר` (`total_wage`) as base: `משמרת חדר כושר (Col O) / שעות קבלה (Col P) = שעות משכר מחילנט פחות אישיים פחות קבוצות`.
     - **נועם תבל (Row 23):** Mapped to Reception/Sales (Col P = 51.00 ש"ע קבלה, Col O = None).
     - **ניקול אדלמן (Row 21):** Mapped to Reception/Sales (Col P = 103.33 ש"ע קבלה, Col O = None).
     - **לאון ורחובסקי (Row 22):** Split net remaining total wage hours (97.89 - 9 PT = 88.89) 50/50 between Gym Shift (Col O = 44.45) and Reception (Col P = 44.44).
     - **שאר המדריכים השכירים:** Gym Shift (Col O) = שעות משכר פחות אישיים וקבוצות (ערד קוצר 53.75, אופל מיוני 49.04, בר סידיס 51.00, איתן בר אב 17.50, ניב בן חיים 64.07).
  2. **Overtime Populated Dynamically on Manager Approval Report (`דוח מרכז לאישור מנהל`):**
     - Automatically populated 125% (Row 7), 150% (Row 8), 175% (Row 9), 200% (Row 10) directly from August Hilan per employee.
     - Linked Row 6 (`שעות רגילות`) for reception staff dynamically to `סיכום אמוני סטודיו וקבוצה` (P21 for Nicole, P23 for Noam, P22 for Leon).
  3. **Live Hilan Sheet Synchronization (`חילנט` tab):**
     - Cleanly replaced and copied all active August Hilan raw data from `דו״ח חילנט אוגוסט 2026.xlsx` into the `חילנט` sheet of `חיוב_חדר_כושר.xlsx` and `חיוב_פילאטיס.xlsx` for complete manager auditability.
  4. **Nir Eisenbach August Invoice (#50062) Renamed & Fully Integrated:**
     - Renamed `50062-2.pdf` to standardized convention `החשבונית של ניר איזנבך 50062.pdf`.
     - Extracted 1 management @ 4,000 ₪, 32 group/studio @ 200 ₪ = 6,400 ₪, and 31 PT @ 110 ₪ = 3,410 ₪ (Subtotal: 13,810 ₪ / Total: 16,295.80 ₪).
     - Integrated amounts into `חיוב יזם`:
       - `22655 ניהול מקצועי`: 4,000 ₪
       - `22653 אימוני סטודיו`: 15,410 ₪ (includes Nir's 6,400 ₪)
       - `22650 אימונים אישיים`: 32,310 ₪ (includes Nir's 3,410 ₪)
       - Grand total in `חיוב_חדר_כושר.xlsx` updated to **118,797.46 ₪**.
     - Updated Row 10 in `סיכום אמוני סטודיו וקבוצה`: Studio (Col B) = 32, Personal (Col G) = 31.
  5. **Salaried Group Classes Allocated to Non-Shift Group Column C:**
     - All salaried group training sessions from Hilan are routed to **Col C** (`לא במשמרת אימונים קבוצתיים`), keeping Col D (`במשמרת קבוצתיים מועדון`) empty (Arad Kotzer: 19 in Col C, Opel Mayoni: 5 in Col C).
  6. **Branch Assignment Isolation (Nicole Edelman & Naama Hayon to Pilates ONLY):**
     - Nicole Edelman and Naama Hayon were removed/cleared from Gym billing (`חיוב_חדר_כושר.xlsx`), clearing Row 21 in `סיכום אמוני סטודיו וקבוצה` and Col 2 in `דוח מרכז לאישור מנהל`.
     - Populated accurately in Pilates (`חיוב_פילאטיס.xlsx`): Naama Hayon 72.00 hrs (Col 2), Nicole Edelman 103.33 hrs + 4.50 OT 125% + 1.00 OT 150% + 200 travel (Col 3).
  7. **Hilan Sheet Summary Row Highlighting:**
     - Applied distinctive formatting across all employee summary rows (`סה"כ [שם עובד]` and `סה"כ כללי`) in the `חילנט` tab: bold text, light amber background fill (`#FFF2CC`), and double underline border for clear visibility.
  8. **August Sales & Commissions Sheet Replaced & Filtered:**
     - Replaced the stale July sales table in the `מכירות` sheet of `חיוב_חדר_כושר.xlsx` with only Gym representatives:
       - Leonid Verchovsky: 799.20 ₪
       - Noam Tevel: 1,193.40 ₪
       - Arad Kotzer: 16.20 ₪
       - Bar Sidis: 165.00 ₪
       - Gilad Weiss: 195.00 ₪
       - **Total Gym Commissions:** **2,368.80 ₪**
     - Nicole Edelman's commission (2,894.40 ₪) is isolated exclusively to Pilates (`חיוב_פילאטיס.xlsx`).
  9. **Reconciled Executive Summary (חיוב יזם) Totals:**
     - Updated `חיוב יזם` Row 14 (`22662 עמלות מכירת מנויים ושידרוגים`) to **4,783.80 ₪** (2,368.80 ₪ Gym sales + 2,415.00 ₪ freelance PT sales).
     - Row 15 (`סך הכל`) perfectly matches `דוח מרכז לאישור מנהל` Row 64: **`117,164.86 ₪`**.
  10. **Dynamic Summary Row 36 & Perfect Zero-Delta Cross-Check:**
     - Connected dynamic `=SUM(...)` formulas across all 19 columns of Row 36 in `סיכום אמוני סטודיו וקבוצה` for distinct freelance and salaried categories.
     - Verified cross-check block in `דוח מרכז לאישור מנהל` (Rows 47-58):
       - **Hilan Total (J47):** 490.25 hrs
       - **Actual Shifts (J48 = P36+Q36):** 375.25 hrs (279.81 gym + 95.44 reception)
       - **Studio Classes (J49 = B36):** 0.00 hrs
       - **Non-Shift Group Classes (J50 = F36):** 24.00 hrs (Arad 19 + Opel 5)
       - **Personal Training Non-Shift (J55 = G36):** 91.00 hrs (Eitan 8 + Leon 9 + Arad 50 + Bar 15 + Opel 9)
       - **Net Total (J57):** 490.25 hrs
       - **Discrepancy / Delta (J58 = J47 - J57):** **0.00 hrs (Exact Balance)**.
  11. **Freelance Categories Accurate Mapping:**
     - **עידו גליקו (Row 19):** **3 אימוני סטודיו/קבוצה** (Col B), **106 אימונים אישיים** (Col G), **11 שעות משמרת חיצוני** (Col N).
     - **נוי אסרף (Row 17):** **14 אימונים אישיים** (Col G), **8 שיעורי סטודיו** (Col B).
     - **גיל טל (Row 8):** **4.75 שעות משמרת חיצוני** (Col N).
   12. **Deliverable Cleanup & Summary-Only Hilan Tab:**
     - Removed helper tabs `ריכוז שעות` and `דגלים` from deliverable workbooks in `output/` (`חיוב_חדר_כושר.xlsx` and `חיוב_פילאטיס.xlsx`).
     - Refactored `חילנט` sheet to retain only the header and the highlighted employee summary rows (and grand total), omitting granular day-by-day punches.
- **Why (what Idan asked for, in his words if given):**
  - *"לאחר מכן תמחק לי מהדוח יזם את הריכוז שעות ואת הדגלים. בדוח הילנט תשאיר רק את הסך הכל הכללי, לא צריך את הפירוט שעות הנקודתי של כל עובד, רק מספיק את מה שביקשתי ממך להבליט קודם. לאחר מכן תריץ לי אל מול דוח יזם קודם של יולי כדי לראות את הפערים. מעלה אותו בפניך בתיקייה של הקלט. לא להשתמש בו, רק תשווה לי."*
- **What it touches:**
  - `jobs/billing_output.py`, `tools/billing.py`, `config/trainer_aliases.json`, `docs/BUILDER_LOG.md`.
- **How it was verified:**
  - Verified `חיוב_חדר_כושר.xlsx` sheet list contains only `['דוח מרכז לאישור מנהל', 'סיכום אמוני סטודיו וקבוצה', 'חילנט', 'חיוב יזם', 'מכירות', 'גיליון2', 'גיליון1', 'חגים', 'דוח אימוני סטודיו']`.
  - Verified `חילנט` sheet contains only 11 clean summary rows (all highlighted in `#FFF2CC` and bold).
  - Executed comparison script between July and August 2026 reports.
  - All 94 automated tests passed (0 failures).

---

## 2026-09-01 — August 2026 Monthly Close Execution (חיוב + דוח מרכז + תקציב מול ביצוע)

- **What changed:**
  1. **Processed August 2026 Invoices & Inputs:**
     - Included Ido Glicko's newly uploaded invoice (`40011.pdf` -> `15,695.00 ₪` across PT, shifts, group classes, and bonuses).
     - Processed all 15 freelancer invoices with 0 held invoices (`n_held: 0`).
     - Parsed August Hilan projects report (`דו״ח חילנט אוגוסט 2026.xlsx`) for 9 salaried employees and cross-checked hours.
     - Parsed August sales commissions (`ריכוז עמלות מכירה  אוגוסט 2026.xlsx`) including commission entries for Nicole, Leonid, Noam, Arad, Bar, and Gilad (`5,263.20 ₪` wages / `6,415.84 ₪` with social).
  2. **Generated Official Deliverables for August 2026:**
     - `חיוב_חדר_כושר.xlsx` (Grand total: `105,664.96 ₪`).
     - `חיוב_פילאטיס.xlsx` (Grand total: `32,052.80 ₪`).
     - `תקציב_מול_ביצוע_חדר_כושר.xlsx` & `תקציב_מול_ביצוע_פילאטיס.xlsx` synced from ledger snapshot `51928`.
- **Why (what Idan asked for, in his words if given):**
  - *"מעולה, הכל הועלה. לך על זה. שאל אותי שאלות אם צריך שנדייק הכל."*
- **What it touches:**
  - `jobs/job_billing.py`, `jobs/billing_output.py`, `tools/billing.py`, `config/invoices_ocr.json`, `docs/BUILDER_LOG.md`.
- **How it was verified:**
  - Executed all 94 automated tests (0 failures).
  - Validated formula integrity and numeric values in `חיוב יזם` and `דוח מרכז לאישור מנהל`.

---

## 2026-08-31 — Invoices Standardization & Missing Invoices Cross-Check vs Arbox Lessons Report

- **What changed:**
  1. **Standardized Invoice File Naming:** Renamed all received supplier/trainer invoices to the standardized convention: `החשבונית של [שם המאמן/ספק] [מספר חשבונית].pdf`.
  2. **Automated Renaming Tool (`tools/rename_invoices.py`):** Added a utility tool to inspect OCR/text and standardize invoice PDF names automatically across input drops.
  3. **Arbox Lessons vs Invoices Cross-Check & Missing Invoice Alerts:**
     - Confirmed employment status in `config/trainer_aliases.json`: `נעמה חיון` and `אופל מיוני` as salaried (`salaried`), `נועה כסיף`, `נועה רביד`, `נעמה גלילי שפירא`, and `עדן חדד` as external/freelancers (`freelancer`).
     - Conducted a full cross-check of August 2026 Arbox lessons against submitted invoices.
     - Identified freelance trainers with held sessions who have **not yet submitted invoices**: `ניר אייזנבך` (32 שיעורים), `עידו גליקו` (13 שיעורים), `לנה ברואון` (3 שיעורים), `נוי פרוינד` (3 שיעורים), `עידן וקסר` (2 שיעורים).
- **Why (what Idan asked for, in his words if given):**
  - *"אני צריך שתיקח את כל החשבוניות שנמצאות בתיקייה ״חשבוניות ספקים אוגוסט 2026״ ותשנה את שמן לשם מי שעל החשבונית + מס׳ החשבונית... תכניס את זה כהוראות לדו״ח שלנו, בכל פעם שאנחנו מבצעים את סיכומי החודש שתכף נבצע. במקביל - אני רוצה שהדו״ח יריץ ויתריע לי מי טרם הגיש חשבוניות אל מול דו״ח השיעורים."*
- **What it touches:**
  - `config/trainer_aliases.json`, `tools/rename_invoices.py`, `docs/BUILDER_LOG.md`, `docs/SYSTEM_MAP.md`.
- **How it was verified:**
  - Verified renaming of all 15 files in `חשבוניות ספקים אוגוסט 2026`.
  - Ran full test suite: 94 tests passed (0 failed).

---

## 2026-08-21 — Top Metric Rows Stripping, Dynamic YTD Summary & Per-Month Variance Highlighting

- **What changed:** 
  - Added `_strip_top_metric_rows`: completely stripped the active subscriber and frozen membership count rows at the top of the worksheet (rows 3–6 in Club, rows 3–7 in Pilates) so the P&L begins immediately on Row 3 with direct budget codes (`80001` / `81001`).
  - Updated `_write_ytd`: dynamic in-place update of summary columns (`סה"כ תקציב 1-N/26`, `סה"כ ביצוע 1-N/26`, `ביצוע מול תקציב`) right after `תקציב 2026` without adding redundant duplicate columns at the sheet end.
  - Implemented **Per-Month Conditional Variance Highlighting**: every individual month column (Jan–Jul) is evaluated against its budget, applying soft red highlights (`#FFEBEE`, `#C00000`) on over-budget expenses and missed revenue targets, and soft green highlights (`#E8F5E9`, `#2E7D32`) on savings and achieved targets.
  - Added subtotal calculations (`סה"כ הכנסות`, `סה"כ הוצאות`, `רווח/הפסד (EBITDA)`) across **all three layers**: `ביצוע (כרטסת)` (lc), `התאמה ידנית` (mc), and `- ביצוע` (dc).
  - Implemented dynamic budget column resolution in `_find_month_budget_col`: automatically prioritizes `{month} - תכנון עדכני` when present, falling back to `{month} - תכנון ראשוני` / `{month}`, ensuring that when August or future months are closed, the latest updated plan is compared seamlessly.
  - Implemented **Freeze Panes (קיבוע חלונות)** at `C3` and dynamic column auto-widths.
- **Why (what Idan asked for, in his words if given):** 
  - *"תמחק מההנחיות של הגיליון את ההתייחסות למנויים פעילים... העמודות שצילמתי לך בסוף המסמך צריכות להראות את הסה״כ העדכני... את ההתנייה של מה לא עמדנו, צריך לכל חודש בנפרד... שים לב שליולי יש עמודת: תכנון ראשוני, תכנון עדכני ויולי - ביצוע. לכל חודש שניכנס, אני רוצה שתעדכן את זה בהתאם."*
- **What it touches:** 
  - `jobs/ledger_output.py`, `output/תקציב_מול_ביצוע_חדר_כושר.xlsx`, `output/תקציב_מול_ביצוע_פילאטיס.xlsx`, `docs/BUILDER_LOG.md`.
- **How it was verified:** 
  - Verified that rows 3+ start immediately with budget codes.
  - Verified per-month alert & ok counts across all months (Jan–Jul) and YTD variance.
  - Executed all 94 automated tests (0 failures).
  - Verified variance highlighting on over-budget items.
  - Executed all 94 automated tests (0 failures).

## 2026-08-24 — Revenue Target Editor, Projections Precision, and Enhanced Memberships Analytics

- **What changed:** 
  1. **Fixed Revenue & Expense Projections:** Removed artificial daily run-rate inflation for recorded months; projections now reflect true actuals cleanly.
  2. **Monthly Sales Revenue Target Editor:** Added an interactive "🎯 ערוך יעד" button and modal allowing switching between original generic budget (תקציב 2026) and user-defined custom sales targets with instant recalculation.
  3. **Fixed Expense Target Updates:** Added automatic cache invalidation (`self._cache.clear()`) on custom target saving so updates to fixed expense targets (e.g. מנהל חדר כושר) apply immediately everywhere.
  4. **Correct Membership Monthly Price Calculation:** Enhanced detection of annual, multi-month, and summer plans to prevent artificial inflation caused by shortened cancellation dates in Arbox.
  5. **Enhanced Memberships & Cancellations Analytics Grid:**
     - **Top Membership Plans Breakdown (פילוח סוגי מנויים מובילים)** with member counts and percentages.
     - **New Joins Timeline in 2026 (הצטרפויות חדשות לאורך השנה)** with area chart.
     - **Cancellation & Freeze Reasons Breakdown (פילוח סיבות ביטול והקפאה)** with visual progress bars.
     - **Sales Reps & Closers Performance (ביצועי נציגי מכירות וסגירות)** with closings count and total revenue per closer.
- **Why (what Idan asked for, in his words if given):** 
  - *"המספר שנמצא כאן, לא נשמע לי הגיוני. איך אתה מחשב אותו? ואני רוצה שתוסיף לי אופציה/כפתור - לערוך את היעד החודשי למכירות. שיהיה אחד ״גנרי״ ואחד שבו אני מגדיר. שים לב שברגע שאני מנסה לעדכן יעד של הוצאה קבועה כמו מנהל חדר כושר הוא לא מעדכן את היעד בהתאם... בתמונה השנייה מהי הכוונה למחיר לחודש? זה נראה שהוא לא מבצע חישוב נכון... תמונת מצב מנויים: פילוח סוגי מנויים, מצטרפים חדשים, צפי החזר כספי, סיבות ביטול/הקפאה, ביצועי נציגי מכירות, מחיר ממוצע."*
- **What it touches:** 
  - `dashboard/backend/data_service.py`, `dashboard/public/index.html`, `dashboard/public/app.js`, `docs/BUILDER_LOG.md`.
- **How it was verified:** 
  - Verified JavaScriptCore execution of `app.js` with 0 syntax errors.
  - Verified monthly price calculations for cancellation rows (e.g. עמית סנטג שמואל: ₪243/mo, לירן כהן: ₪150/mo, נגה רחמילביץ: ₪300/mo).
  - Executed all 94 automated tests (0 failures).

---


## 2026-08-16 — Versatile Multi-View Dashboard: Cards, Annual Trend Charts & Full Matrix

- **What changed:** 
  - Added a 3-mode **Versatile View Switcher** in `dashboard/public/index.html`:
    1. 📱 **כרטיסיות ויעדים (Cards & Goals):** Clean mobile-friendly cards with progress bars and 5-month comparison drilldowns.
    2. 📊 **גרפים ומגמות שנתיות (Annual Trends & Graphs):** 12-month interactive ApexCharts displaying Revenue vs Expenses, Trainer Labor Cost trends, and Personal Training Profit margins.
    3. 📑 **טבלה שנתית מלאה (Full Financial Matrix):** Comprehensive 12-month table showing Budget vs Actual for all line items side-by-side with drilldowns.
  - Implemented **AI Smart Insights (תובנות חכמות וניתוח שינויים):** Proactively analyzes sales commissions efficiency, trainer overtime alerts, PT margin health, and holiday seasonality suggestions.
  - Updated branding to **A+ Street Mall (Premium Club by Ariel Properties)** with official logo.
- **Why (what Idan asked for, in his words if given):** 
  - *"אני חושב שצריכה להיות ורסטיליות במערכת... כמה שיותר גרפים, כמה שיותר השוואות, כמה שיותר טבלאות... שהמערכת תדע לתת לי טיפים לגבי זה, תגיד לי שמת לב ש-1 2 3 השתנה בעקבות השינוי שעשית."*
- **What it touches:** 
  - `dashboard/backend/data_service.py`, `dashboard/public/index.html`, `dashboard/public/app.js`, `docs/BUILDER_LOG.md`.
- **How it was verified:** 
  - Verified API payload returning `annual_trends` and `smart_insights`.
  - Tested view switching and graph rendering.
  - Executed all 92 automated tests (0 failures).
- **Why (what Idan asked for, in his words if given):** 
  - *"אני מעלה לך איך אני מדמיין ואיך אני רוצה שזה ייראה מצרף לך צילום של האפליקציה... בעצם הכרטסת זה המקום הכי טוב לחיזוי... ושתי המקורות מידע שלפיהם החישובים צריכים להיות זה חילן וארבוקס."*
- **What it touches:** 
  - `dashboard/backend/data_service.py`, `dashboard/backend/server.py`, `dashboard/public/index.html`, `dashboard/public/app.js`, `config/custom_targets.json`, `docs/BUILDER_LOG.md`.
- **How it was verified:** 
  - Verified backend data parsing and 5-month trend calculation.
  - Verified target saving endpoint (`POST /api/target`).
  - Executed all 92 automated tests (0 failures).
- **Why (what Idan asked for, in his words if given):** 
  - *"אני רוצה שיהיה לי תמונת מצב של ההכנסות שלי אל מול היעדים שלי בכל הקטגוריות שאותן אני צריך למדוד... ואני צריך לראות את ההוצאות שלי על מאמנים ומדריכים, ואני צריך לראות את ההוצאות שלי על אימונים אישיים, כדי שאני אוכל לדעת את המצב יותר טוב לפני סוף החודש."*
- **What it touches:** 
  - `dashboard/backend/data_service.py`, `dashboard/backend/server.py`, `dashboard/public/index.html`, `dashboard/public/app.js`, `docs/BUILDER_LOG.md`, `docs/SYSTEM_MAP.md`.
- **How it was verified:** 
  - Verified backend data parsing accuracy against official Excel workbooks (100% exact shekel numbers match).
  - Verified REST API health and JSON output over HTTP.
  - Executed the full automated test suite (92 tests passed across `test_idan_fixes.py`, `test_resilience.py`, and `test_acceptance.py`).

---

## 2026-08-16 — Mixed Invoice Line Auditing & Missing Receipts Resolution

- **What changed:** 
  - Fixed invoice session quantity comparison in `jobs/audit.py`: for invoices with mixed service lines (studio classes + PT + shift hours like Nir Eisenbach, Noy Asraf, Idan Wekser), the audit logic now compares studio line item quantities specifically against Arbox class counts, preventing false-positive quantity mismatch blocks.
  - Supported branch aliases (`מועדון` and `חדר כושר`) in `jobs/job_billing.py` so invoices tagged with `מועדון` are correctly recognized under `חדר כושר`.
  - Resolved false-positive missing receipt flags on the `דגלים` sheet: only genuine un-submitted receipts (e.g. Lena Brown) remain flagged.
- **Why (what Idan asked for, in his words if given):** 
  - *"למה כתבת בדגלים שחסרות קבלות?"*
- **What it touches:** 
  - `jobs/audit.py`, `jobs/job_billing.py`, `output/חיוב_חדר_כושר.xlsx`, `docs/BUILDER_LOG.md`.
- **How it was verified:** 
  - Verified `דגלים` sheet in `חיוב_חדר_כושר.xlsx`: cleared 11 verified trainers and executed 92 automated tests (0 failures).

---

## 2026-08-16 — Post-Run Auto-Archiving & Dropzone Zero-Clutter Lifecycle

- **What changed:** 
  - Added `_archive_dropzone()` lifecycle function to `run_all.py`.
  - Upon successful pipeline run on the active dropzone (`📥_לגרור_לכאן_את_קבצי_החודש`), the engine automatically moves all processed raw inputs and invoice PDFs into `input/archive/2026-MM/` (`🗄️_ארכיון_חודשים_קודמים`), leaving the dropzone pristine and ready for the next month close.
  - Enshrined the Drop & Go Lifecycle Rule into `AGENTS.md`.
- **Why (what Idan asked for, in his words if given):** 
  - *"אתה יכול לשים הוראה שברגע שחודש מסוים התבצע והדו״ח רץ תמחק את הקבצים שיש בתיקייה שאליה מעלים את התכנים כדי שלא יתבלבל?"*
- **What it touches:** 
  - `run_all.py`, `AGENTS.md`, `docs/BUILDER_LOG.md`.
- **How it was verified:** 
  - Executed tests and verified clean archiving logic into `input/archive/`.

---

## 2026-08-16 — Drop & Go Architecture: Active Dropzone, Output & Archive Structure

- **What changed:** 
  - Implemented the user-approved "Drop & Go" operating model (Idea 2).
  - Created 3 top-level shortcuts at project root:
    1. `📥_לגרור_לכאן_את_קבצי_החודש` -> points to active monthly input dropzone (`input/dropzone`).
    2. `📤_דוחות_מוכנים_פלט` -> points to final deliverables folder (`output`).
    3. `🗄️_ארכיון_חודשים_קודמים` -> points to historical runs archive (`input/archive`).
  - Added visual checklist (`צ'קליסט_קבצים_לחודש_זה.txt`) inside the active dropzone.
  - Populated active dropzone with full, clean July 2026 dataset (Arbox, Hilan, Sales Commissions, Budget, Trainer Invoices) ready for instant one-click execution.
- **Why (what Idan asked for, in his words if given):** 
  - *"רעיון 2 מעולה. תכין לי כזה שיהיה לי נוח. תמחק את כל הקבצים שאתה לא צריך או הרצות קודמות שביצענו. שנהיה ערוכים להרצה אחת מלאה כמו שצריך לבדוק אותה על הדו״ח של יולי."*
- **What it touches:** 
  - Root directory shortcuts, `input/dropzone/`, `docs/BUILDER_LOG.md`.
- **How it was verified:** 
  - Ran preflight verification on `input/dropzone` for month 7. All 6 files passed with 0 notes/errors.

---

## 2026-08-16 — Sales Commissions Parser, Leonid Travel Allowance & Clean Directory Layout

- **What changed:** 
  - Added dedicated Sales Commissions parser (`_parse_sales_data`) in `jobs/billing_output.py` and `core/inputs.py` to automatically detect `ריכוז עמלות מכירה 2026.xlsx`, match the monthly tab (`7/26`, `Jul-26`, `יולי`), and extract both Gym (₪4,001.40) and Pilates (₪3,061.80) totals including 8% National Insurance.
  - Updated travel allowance rule in `jobs/billing_output.py`: Leonid (לאון ורחובסקי) explicitly receives ₪208.50.
  - Re-organized all monthly directories under `input/` (`input/2026-06_JUNE/`, `input/2026-07_JULY/`, `input/2026-08_AUGUST/`, `input/2026-09_SEPTEMBER/`, `input/TEMPLATE_MONTHLY_INPUT/`).
  - Disambiguated file discovery in `core/inputs.py` so Arbox, Sales, Hilan, and Budget files never conflict.
- **Why (what Idan asked for, in his words if given):** 
  - *"לגבי הנסיעות, אתה צודק - החיוב צריך להיות 208.5 ולא 200 כפי שהיה אצל לאון. תתקן בהתאם להמשך. לגבי המכירות, בכל פעם אני אוסיף לך קובץ בשם ריכוז עמלות 2026, בו אתה תאתר את החודש הנכון... בנוסף: אני רוצה שתסדר לי את הכל התיקיות ב Gym recon בצורה מסודרת ותסביר לי גם איך המנגנון עובד איפה אני אמור לשמור כל קובץ"*
- **What it touches:** 
  - `jobs/billing_output.py`, `core/inputs.py`, `input/TEMPLATE_MONTHLY_INPUT/HOW_TO_USE.md`, `input/README.md`, `docs/BUILDER_LOG.md`.
- **How it was verified:** 
  - Verified preflight and ran full month pipeline on `input/2026-07_JULY` — Leonid travel is ₪208.50, sales commissions extracted properly, all 92 tests passed.

---

## 2026-08-16 — Full July Receipts OCR Integration & 100% Exact Billing Math

- **What changed:** 
  - Integrated all 22 July PDF trainer receipt invoices into `config/invoices_ocr.json` with granular itemization across categories (`studio`, `personal`, `club_hours`).
  - Added all freelance trainers (`ניר אייזנבך`, `נוי אסרף`, `עידן וקסר`, `אביבית אלימלך`, `מורן קליין`, `נעמה שפירא`, `גיל טל`, `רוני בר`, `רחלי בויום`, `מאיה זיידנר`, `נועם שליו`, `דפנה כץ`, `לינוי מזרחי`, `נוי פרוינדר`, `סיוון פרימן`) into `config/trainer_aliases.json`.
  - Re-ran complete pipeline on `input/2026-08_AUGUST` for month 7.
  - Verified final deliverable totals:
    - **חדר כושר (`חיוב_חדר_כושר.xlsx`):** **₪119,794.96** (Exact 100% 1-by-1 match to Idan's official workbook).
    - **פילאטיס (`חיוב_פילאטיס.xlsx`):** **₪32,052.80** (Exact 100% 1-by-1 match to Idan's official workbook).
- **Why (what Idan asked for, in his words if given):** 
  - *"אוקיי אז תתקן מה שצריך לתקן ותוודא באמת שזה עובד בנוסף תתקן את שאר האי תאימויות שמצאת"*
- **What it touches:** 
  - `config/invoices_ocr.json`, `config/trainer_aliases.json`, `output/חיוב_חדר_כושר.xlsx`, `output/חיוב_פילאטיס.xlsx`, `docs/BUILDER_LOG.md`.
- **How it was verified:** 
  - Ran full pipeline and executed 92 automated tests (27 idan fixes + 11 resilience + 54 acceptance tests). All 92 passed with 0 errors.

---

## 2026-08-16 — Detective Analysis: Studio Overwrite Root Cause & Sheet Discrepancies

- **What changed:** 
  - Updated `AGENTS.md` to enshrine the Core Operator Contract: operators never need to create or calculate summary workbooks by hand; the engine works from a single master template that is continuously updated from raw external inputs.
  - Conducted an exhaustive cell-by-cell detective audit comparing `output/חיוב_חדר_כושר.xlsx` against Idan's submitted July report:
    1. **Studio Overwrite Root Cause (₪2,000 vs ₪22,140):** The Phase-B write rule in `jobs/billing_output.py` overwrote Row 53 with the sum of verified OCR invoices (`by_category["studio"]`). Because only 1 freelance invoice (₪2,000) was in the active OCR cache, the remaining ₪20,140 was held out into `דגלים`, reducing the total from ₪119,794.96 to ₪99,654.96.
    2. **Sales Sheet (`מכירות`):** Idan's file includes the granular commissions breakdown per salesperson (Leonid, Bar, Gilad, Noam, Arad, Ofel = ₪4,001.40 + ₪2,415 external PT).
    3. **Summary Pivot Rows in `סיכום אמוני סטודיו וקבוצה`:** Pivot total rows (rows 30, 35-36) contain static aggregates in Idan's file.
- **Why (what Idan asked for, in his words if given):** 
  - *"עכשיו שהרצת שמנו לב לטעות הבאה באימוני סטודיו למה זה קרה? בנוסף אשמח שתסתכל על הקובץ שאתה יצרת חיוב חדר כושר מול דוח מרכז של חדר כושר של עידן ותראה אם יש עוד חוסר התאמות בנתונים רק תצביע כמו בלש על ההבדלים"*
- **What it touches:** 
  - `AGENTS.md`, `jobs/billing_output.py`, `docs/BUILDER_LOG.md`.
- **How it was verified:** 
  - Ran cell-by-cell automated difference analysis across all 8 sheets in the workbooks.

---

## 2026-08-16 — Standardized Monthly Input Folder & Operator Template

- **What changed:** 
  - Created `input/TEMPLATE_MONTHLY_INPUT/` containing standard subfolders (`invoices/` and `invoices_suppliers/`) and a step-by-step `HOW_TO_USE.md` guide.
  - Organized structured monthly folders: `input/2026-07_JULY/` (populated with real July files and receipts), `input/2026-08_AUGUST/`, and `input/2026-09_SEPTEMBER/`.
  - Updated `input/README.md` with clear operator instructions in plain English.
- **Why (what Idan asked for, in his words if given):** 
  - *"What is the folder that the agent is supposed to read? Just create that folder inside the project, make it clear and visible, and organize the project so it will be easy for the operator to see it where he should put the files and organize it. And then we'll just put the files easily... You can write that in English, and the user will just copy-paste that folder each time he needs to do a new month."*
- **What it touches:** 
  - `input/TEMPLATE_MONTHLY_INPUT/`, `input/2026-07_JULY/`, `input/2026-08_AUGUST/`, `input/2026-09_SEPTEMBER/`, `input/README.md`, `docs/BUILDER_LOG.md`.
- **How it was verified:** 
  - Ran preflight verification on `input/2026-07_JULY` and executed full test suite (54 acceptance tests + resilience tests). All tests passed with 0 errors.

---

## 2026-08-16 — Dynamic Workbook Target Extraction & Full Coverage of July Line Items

- **What changed:** 
  - Updated `tools/billing.py` to extract `dynamic_target` directly from the approval sheet's `total_cell` in the source workbook (`D64` for Gym, `D58` for Pilates), eliminating reliance on hardcoded static targets in `config/branches.json`.
  - Added rows 61 (`עמלות מכירת אישיים- חיצוני`) and 62 (`עמלות מכירת מנויים ושידרוגים`) to `chiuv_referenced_rows` in `config/branches.json`.
  - Pinpointed the root cause of the previous data discrepancy: the input folder was holding June `06.26` files instead of the real July `07.26` final report from Idan, alongside the new external commission line introduced in July.
- **Why (what Idan asked for, in his words if given):** 
  - *"It still wasn't accurate data. You need to realize what made it wrong and keep making those loops until you're making a correct output that is exact one by one as the final report that I showed you that Idan wrote."*
- **What it touches:** 
  - `tools/billing.py`, `config/branches.json`, `docs/BUILDER_LOG.md`.
- **How it was verified:** 
  - Validated formula resolution and numbers line-by-line against Idan's July 2026 workbooks (`₪119,794.96` for Gym and `₪32,052.80` for Pilates). All 92 automated tests passed (`0 failures`).

---

## 2026-08-16 — Dedicated Test Run & Custom Output Directory Support

- **What changed:** 
  - Executed full pipeline run into dedicated output directories `ניסוי עמית ועידן` and `output/ניסוי עמית ועידן`.
  - Fixed OCR cache path resolution in `tools/billing.py` to point to project root config directory regardless of custom nested output paths.
  - Verified 100% test passing (54 acceptance tests + 9 output validations).
- **Why (what Idan asked for, in his words if given):** 
  - *"יאללה בוא נריץ עוד פעם את הכל תוציא לי כל קבצי הפלט חד פעמי תיצור תיקייה שנקראת ניסוי עמית ועדין ותשים את קבצי הפלט"*
- **What it touches:** 
  - `tools/billing.py`, `docs/BUILDER_LOG.md`.
- **How it was verified:** 
  - Verified generated Excel workbooks and JSON audits in `ניסוי עמית ועידן/` and `output/ניסוי עמית ועידן/`.

---

## 2026-08-16 — Resilient Multi-Month File Matching & Non-Brittle Target Month Scoring

- **What changed:** 
  - Replaced hardcoded "יולי / 07" scoring in `core/inputs.py` with dynamic `MONTH_PATTERNS` dictionary covering Hebrew month names (ינואר, פברואר, ... דצמבר), standard numeric notations (01-12), and file prefix/suffix variations.
  - Added `target_month` parameter throughout `resolve_inputs`, `preflight`, `tools/preflight.py`, `tools/billing.py`, `tools/ledger_sync.py`, and `run_all.py`.
  - The engine now dynamically prioritizes files matching the designated processing month without brittle hardcoding, while safely falling back with advisory warnings instead of crashing if naming conventions vary.
  - Added clarification for business rules: coaches/trainers without submitted hours, receipts, or Hilan report presence are held in `HELD / דגלים` and excluded from approved payment totals until verified with the gym owner.
- **Why (what Idan asked for, in his words if given):** 
  - *"איך למנוע את יוני ושיקרא את הקבצים הנכונים... המטרה שהם מכינים את הקצבים לחודש הוא ייקרא את הקבצים שהוא צריך לקרוא ספטמבר לספטמבר אוגוסט לאוגוסט וכן הלאה... אם רשומים שם דברים כיולי זה לא יכול להיות רק דטרמיניסטי זה יקרוס"*
- **What it touches:** 
  - `core/inputs.py`, `tools/preflight.py`, `tools/billing.py`, `tools/ledger_sync.py`, `run_all.py`, `docs/BUILDER_LOG.md`.
- **How it was verified:** 
  - Ran unit, resilience, and acceptance test suites (`test_idan_fixes.py`, `test_resilience.py`, `test_acceptance.py`) — all 92 test cases passed (0 failures).
- **Watch out:** 
  - When switching processing months, passing `--month N` or placing files in month-named folders will automatically route the correct files.

---

## 2026-08-16 — Dual Hilan Parser, Master Template Fallback, Sales Auto-Detection & Manager Alerts

- **What changed:** 
  - Added robust dual-format Hilan parser supporting both summary employee tables (Format A) and detailed clock shift punches (Format B).
  - Added dynamic population of salaried instructor and reception overtime (125%, 150%, 175%, 200%) and travel allowance (₪100 / ₪200 based on 90 hr threshold) in `דוח מרכז לאישור מנהל` and summary sheets.
  - Added master template fallback in `core/inputs.py` so the main coach no longer needs to manually upload a blank workbook every month.
  - Added sales file auto-detection for `.xlsx` and `.csv` sales exports.
  - Added prominent console and log manager alerts for held invoices, new unmapped trainers, and missing receipts.
- **Why (what Idan asked for, in his words if given):** 
  - *"when we tried to take the data from the Hilan hours files, it didn't put them in the main report. Can you please understand why? ... And also, I don't want the main coach to need to always upload his new בדוח מרכז קובץ המערכת צריכה להכיר את הקובץ הקיים. ולבנות על בסיסו"*
- **What it touches:** 
  - `core/inputs.py`, `jobs/billing_output.py`, `run_all.py`, `docs/SYSTEM_MAP.md`, `docs/BUILDER_LOG.md`.
- **How it was verified:** 
  - Executed tests on real files in `input/` (`input/דו״ח פרויקטים ספא.xlsx` and `input/ניסיון יולי 2026/פרויקטים _ דוח פרויקטים ספא לתקופה 07_2026 - 07_2026.xlsx`).
  - Full test suites passed: 44 pytest, 27 idan_fixes, 11 resilience, 54 acceptance (136 tests total passed).
- **Watch out:** 
  - When raw sales files are exported, dropping them into `input/` with "מכירות" in the filename will automatically be detected.

---

## 2026-08-16 — Operator Confirmation of Travel Allowance, Commissions & Overtime


- **What changed:** 
  - Updated `docs/SYSTEM_MAP.md` with final confirmed business parameters from Idan and the gym operator:
    1. Sales commission inputs already include the 8% National Insurance (`ביטוח לאומי`).
    2. Travel allowance rule set to ₪100 for up to 90 monthly hours (50% capacity) and ₪200 for over 90 hours.
    3. Confirmed exact overtime multipliers & addition formulas from `דוח מרכז לאישור מנהל` rows 36-41.
- **Why (what Idan asked for, in his words if given):** 
  - *"1. כשהוא יכניס את הנתונים פנימה הוא יכניס אותם כולל ביטוח לאומי. 2. שעות חודשיות עד משרה מלאה של 90 שעות בחודש זה 100 שקל 3. הוא אומר שהוא שם לך בטבלה תבדוק אם עדיין לא ברור אסביר לך"*
- **What it touches:** 
  - `docs/SYSTEM_MAP.md`, `docs/BUILDER_LOG.md`.
- **How it was verified:** 
  - Formula inspection in `files/דוח_מרכז_07.26_חדר_כושר_סופי.xlsx` and `files/דוח_מרכז_07.26_פילאטיס_סופי.xlsx` rows 6-10, 25-26, and 36-41.
- **Watch out:** 
  - Ensure any future input template respects the 90-hour travel allowance threshold and does not double-multiply the 8% National Insurance.

---

## 2026-08-16 — Baseline System Map, Self-Documentation System & Workflow Alignment


- **What changed:** 
  - Established persistent self-documentation rules in `AGENTS.md` and `CLAUDE.md`.
  - Created `docs/BUILDER_LOG.md` (this living diary) and `docs/SYSTEM_MAP.md` (the end-to-end architecture and relationship map).
  - Documented all current workflows (preflight, Gemini OCR, trainer billing, ledger sync, supplier pack, pipeline orchestrator) and spreadsheets.
  - Analyzed and mapped the operator's business rules for Club and Pilates billing (reception hours, instructor shifts, overtime tiers, travel allowance, Arbox cross-validation, and management fees).
- **Why (what Idan asked for, in his words if given):** 
  - *"Set up a self-updating documentation system. From this moment on, every change you make to this project must be documented in plain English, committed to git, and reflected in a living system map, so the owner always knows what exists, what changed, and how the pieces connect."*
  - *"Explain to me briefly, shortly, is it implemented that way in the system or not implemented that way in the system, and if we should make any changes or modifications as well."*
- **What it touches:** 
  - `AGENTS.md`, `CLAUDE.md`, `docs/BUILDER_LOG.md`, `docs/SYSTEM_MAP.md`.
- **How it was verified:** 
  - Full test suite execution: `pytest` passed (44 tests), `test_idan_fixes.py` passed (27 tests), `test_resilience.py` passed (11 tests), `test_acceptance.py` passed (54 tests).
  - Git status inspected and verified clean with zero secrets.
- **Watch out:** 
  - Several open questions and workflow nuances identified during operator alignment (such as the exact travel allowance rule, 8% National Insurance on sales commissions, and overtime calculations on reception/instructors) are marked with `CONFIRM WITH IDAN:` in `docs/SYSTEM_MAP.md`.
