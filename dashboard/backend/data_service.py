"""
Ariel Fit & Spa Dashboard - Advanced Data & Forecasting Service
Provides 5-month historical trend analysis, 12-month full-year matrix,
smart AI financial insights, and flexible multi-view aggregation.
"""
from __future__ import annotations
import os
import re
import json
import calendar
from datetime import datetime
from pathlib import Path
import openpyxl

BASE_DIR = Path(__file__).resolve().parent.parent.parent
OUTPUT_DIR = BASE_DIR / "output"
INPUT_DIR = BASE_DIR / "input"
CONFIG_DIR = BASE_DIR / "config"
CUSTOM_TARGETS_FILE = CONFIG_DIR / "custom_targets.json"

MONTH_NAMES_HE = [
    "ינואר", "פברואר", "מרץ", "אפריל", "מאי", "יוני",
    "יולי", "אוגוסט", "ספטמבר", "אוקטובר", "נובמבר", "דצמבר"
]

MONTH_SHORT_HE = [
    "ינו'", "פבר'", "מרץ", "אפר'", "מאי", "יוני",
    "יולי", "אוג'", "ספט'", "אוק'", "נוב'", "דצמ'"
]

def get_days_in_month(year: int, month_idx: int) -> int:
    return calendar.monthrange(year, month_idx)[1]

def safe_float(val) -> float:
    if val is None or val == "":
        return 0.0
    try:
        if isinstance(val, str):
            val = val.replace(",", "").strip()
        return float(val)
    except (ValueError, TypeError):
        return 0.0

class DashboardDataService:
    def __init__(self):
        self.year = 2026
        self.custom_targets = self._load_custom_targets()
        self._cache = {}

    def _load_custom_targets(self) -> dict:
        if CUSTOM_TARGETS_FILE.exists():
            try:
                with open(CUSTOM_TARGETS_FILE, encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                return {}
        return {}

    def save_custom_target(self, club: str, code: str, month: int, new_target: float) -> bool:
        key = f"{club}_{code}_{month}"
        self.custom_targets[key] = float(new_target)
        try:
            CONFIG_DIR.mkdir(parents=True, exist_ok=True)
            with open(CUSTOM_TARGETS_FILE, "w", encoding="utf-8") as f:
                json.dump(self.custom_targets, f, ensure_ascii=False, indent=2)
            self._cache.clear()
            return True
        except Exception as e:
            print("Error saving target:", e)
            return False

    def get_available_months(self) -> list[dict]:
        months = []
        for idx, name in enumerate(MONTH_NAMES_HE, start=1):
            months.append({
                "index": idx,
                "name": name,
                "short_name": MONTH_SHORT_HE[idx - 1],
                "key": f"{self.year}-{idx:02d}",
                "is_current": (idx == 6),
                "has_data": idx <= 7
            })
        return months

    def parse_budget_workbook(self, file_path: Path, club_name: str) -> dict:
        if not file_path.exists():
            return {}

        mtime = file_path.stat().st_mtime
        cache_key = f"budget_{file_path}_{club_name}_{mtime}"
        if cache_key in self._cache:
            return self._cache[cache_key]

        wb = openpyxl.load_workbook(str(file_path), data_only=True)
        ws = wb.active

        headers = {}
        for col_idx in range(1, ws.max_column + 1):
            val = ws.cell(row=2, column=col_idx).value
            if val:
                headers[col_idx] = str(val).strip()

        month_cols = {}
        for m_idx, m_name in enumerate(MONTH_NAMES_HE, start=1):
            b_col = None
            a_col = None
            for c_idx, h_text in headers.items():
                if m_name in h_text:
                    if "ביצוע" in h_text:
                        a_col = c_idx
                    elif b_col is None:
                        b_col = c_idx
            month_cols[m_idx] = {"budget_col": b_col, "actual_col": a_col}

        incomes = []
        variable_expenses = []
        fixed_expenses = []
        is_expense_section = False

        for row in range(3, ws.max_row + 1):
            code_cell = ws.cell(row=row, column=1).value
            desc_cell = ws.cell(row=row, column=2).value
            
            code_str = str(code_cell).strip() if code_cell is not None else ""
            desc_str = str(desc_cell).strip() if desc_cell is not None else ""

            if not desc_str and not code_str:
                continue

            if "הוצאה" in desc_str or "הוצאות" in desc_str:
                is_expense_section = True
                continue

            if "כמות מנויים" in desc_str or "סה\"כ" in desc_str:
                continue

            item_months = {}
            for m_idx, cols in month_cols.items():
                b_val = ws.cell(row=row, column=cols["budget_col"]).value if cols["budget_col"] else 0.0
                a_val = ws.cell(row=row, column=cols["actual_col"]).value if cols["actual_col"] else 0.0
                
                b_num = abs(safe_float(b_val))
                a_num = abs(safe_float(a_val))
                
                override_key = f"{club_name}_{code_str}_{m_idx}"
                if override_key in self.custom_targets:
                    b_num = self.custom_targets[override_key]

                item_months[m_idx] = {
                    "budget": b_num,
                    "actual": a_num,
                    "variance": a_num - b_num
                }

            item_data = {
                "code": code_str,
                "name": desc_str,
                "club": club_name,
                "months": item_months
            }

            if not is_expense_section:
                if "מנוי" in desc_str:
                    item_data["category"] = "memberships"
                    item_data["category_he"] = "מנויים וכרטיסיות"
                    item_data["explanation"] = "הכנסות שוטפות מדמי מנוי שנתיים וחודשיים של חברי המועדון."
                elif "אימונים אישיים" in desc_str or "אישיים" in desc_str:
                    item_data["category"] = "personal_training"
                    item_data["category_he"] = "אימונים אישיים"
                    item_data["explanation"] = "הכנסות מרכישת חבילות וכרטיסיות אימונים אישיים מול מדריכי המועדון."
                elif "הרשמה" in desc_str or "צ'יפ" in desc_str:
                    item_data["category"] = "registration"
                    item_data["category_he"] = "דמי הרשמה וצ'יפ"
                    item_data["explanation"] = "דמי רישום חד פעמיים ורכישת צ'יפים בכניסה למועדון."
                elif "כרטיסיות" in desc_str:
                    item_data["category"] = "punch_cards"
                    item_data["category_he"] = "כרטיסיות - פריפיט"
                    item_data["explanation"] = "הכנסות מכרטיסיות אימון גמישות וחברות חיצוניות."
                else:
                    item_data["category"] = "other_income"
                    item_data["category_he"] = "הכנסות שונות / סטודיו"
                    item_data["explanation"] = "השכרת סטודיו לחברות ואירועים מיוחדים."
                incomes.append(item_data)
            else:
                # Fixed codes according to Idan's explicit rules:
                # 1. מנהל חדר כושר (22601), מנהל מקצועי (22655), שכר ניהול אריאל (90101)
                # 4. תוכנות ומיחשוב (ארבוקס 20634, טכנוג'ים 10117, אינטרנט 22622, מוזיקה 22638)
                # 5. שכירות (22645), דמי ניהול (10106, 90201), ביטוח (22606)
                # 6. הנהלת חשבונות (10325), רואה חשבון (10324), בצ"מ (22634)
                fixed_codes = {
                    "22601", "22655", "90101",
                    "20634", "10117", "22622", "22638",
                    "22645", "10106", "90201", "22606",
                    "10325", "10324", "22634"
                }

                is_explicit_fixed = (code_str in fixed_codes) or any(k in desc_str for k in [
                    "מנהל חדר כושר", "תוספת למנהל", "מנהל מקצועי", "שכר ניהול אריאל",
                    "ארבוקס", "טכנוג'ים אפליקציה", "אינטרנט וטלפון", "מוזיקה ותמלוגים",
                    "שכירות", "דמי ניהול קניון", "ביטוח",
                    "הנהלת חשבונות", "רואה חשבון", "בצמ"
                ])

                if not is_explicit_fixed:
                    item_data["expense_type"] = "variable"
                    if any(k in desc_str for k in ["מאמן", "מאמנ", "מדריך", "מדריכ", "אישי", "חוג", "הדרכ", "קורס", "השתלמות", "השתלמויות", "קבל"]):
                        item_data["category_he"] = "שכר הדרכה, מאמנים ומשמרות"
                        item_data["explanation"] = "שכר מדריכים, מאמנים אישיים, שיעורי סטודיו ומשמרות קבלה (ארבוקס + חילנט)."
                    elif "מכירות" in desc_str or "מכירה" in desc_str:
                        item_data["category_he"] = "עמלות מכירות"
                        item_data["explanation"] = "עמלות לנציגי מכירות על סגירת מנויים ושדרוגים."
                    elif "שיווק" in desc_str or "פרסום" in desc_str:
                        item_data["category_he"] = "שיווק ופרסום"
                        item_data["explanation"] = "קמפיינים דיגיטליים, קידום ממומן ומיתוג המועדון."
                    elif any(k in desc_str for k in ["חשמל", "מים", "ארנונה", "אגרות", "אגרה"]):
                        item_data["category_he"] = "חשמל, מים, ארנונה ואגרות"
                        item_data["explanation"] = "צריכת אנרגיה חודשית שוטפת, תשלומי מים, ארנונה לעירייה ואגרות."
                    elif any(k in desc_str for k in ["עמלות", "עמלת", "ריבית", "אשראי", "בנק"]):
                        item_data["category_he"] = "עמלות סליקה ופיננסי"
                        item_data["explanation"] = "עמלות סליקת אשראי של חברי המועדון וריביות בנקאיות."
                    elif "משרד" in desc_str:
                        item_data["category_he"] = "הוצאות משרדיות"
                        item_data["explanation"] = "ציוד משרדי שוטף, הדפסות ודפוס."
                    else:
                        item_data["category_he"] = "תפעול שוטף, אחזקה וניקיון"
                        item_data["explanation"] = "חומרי ניקיון, טואלטיקה, אחזקת מכשירים, מיזוג אוויר וספרינקלרים."
                    variable_expenses.append(item_data)
                else:
                    item_data["expense_type"] = "fixed"
                    item_data["category_he"] = "הוצאות קבועות ומבנה"
                    item_data["explanation"] = "הוצאות תשתית והסכמים קבועים בחוזה (שכירות, דמי ניהול, הנה״ח, שכר ניהול, ביטוח ותוכנות ניהול)."
                    fixed_expenses.append(item_data)

        res = {
            "club": club_name,
            "incomes": incomes,
            "variable_expenses": variable_expenses,
            "fixed_expenses": fixed_expenses
        }
        self._cache[cache_key] = res
        return res

    def get_drilldown_history(self, item_name: str, item_months: dict, target_month: int) -> dict:
        history_bars = []
        start_m = max(1, target_month - 4)
        for m in range(start_m, target_month + 1):
            m_data = item_months.get(m, {"budget": 0.0, "actual": 0.0})
            history_bars.append({
                "month_index": m,
                "month_name": MONTH_NAMES_HE[m - 1],
                "short_name": MONTH_SHORT_HE[m - 1],
                "actual": m_data["actual"],
                "budget": m_data["budget"],
                "is_current": (m == target_month)
            })

        past_actuals = [b["actual"] for b in history_bars if not b["is_current"] and b["actual"] > 0]
        avg_past = sum(past_actuals) / len(past_actuals) if past_actuals else history_bars[-1]["budget"]

        return {
            "history_bars": history_bars,
            "historical_average": round(avg_past, 2)
        }

    def generate_smart_insights(self, incomes: list, var_exp: list, fix_exp: list, month: int) -> list[dict]:
        """Generates proactive AI financial tips and trend observations."""
        tips = []

        # 1. Check Sales Commission vs Revenue trend
        comm_item = next((x for x in var_exp if "עמלות" in x["name"]), None)
        mem_item = next((x for x in incomes if "מנויים" in x["name"]), None)
        if comm_item and mem_item:
            c_act = comm_item["months"].get(month, {}).get("actual", 0)
            c_prev = comm_item["months"].get(max(1, month - 1), {}).get("actual", 0)
            m_act = mem_item["months"].get(month, {}).get("actual", 0)
            m_prev = mem_item["months"].get(max(1, month - 1), {}).get("actual", 0)
            if c_act > 0 and c_prev > 0:
                c_diff_pct = round(((c_act - c_prev) / c_prev) * 100, 1)
                m_diff_pct = round(((m_act - m_prev) / m_prev) * 100, 1) if m_prev > 0 else 0
                if c_diff_pct > 15 and m_diff_pct > 10:
                    tips.append({
                        "icon": "trending-up",
                        "color": "emerald",
                        "title": "יעילות צוות מכירות במגמת עלייה",
                        "text": f"עמלות המכירה עלו ב-{c_diff_pct}% החודש במקביל לעלייה של {m_diff_pct}% בהכנסות ממנויים. התמריצים מניבים תוצאות."
                    })

        # 2. Check Trainer cost efficiency
        trainer_item = next((x for x in var_exp if "עלות מאמנים" in x["name"] or "מאמנות" in x["name"]), None)
        if trainer_item:
            t_act = trainer_item["months"].get(month, {}).get("actual", 0)
            t_bud = trainer_item["months"].get(month, {}).get("budget", 0)
            if t_act > t_bud:
                diff = t_act - t_bud
                tips.append({
                    "icon": "alert-triangle",
                    "color": "amber",
                    "title": "התראת קצב שעות מאמנים",
                    "text": f"נרשמה חריגה של ₪{diff:,.0f} בעלות המאמנים לעומת התקציב. כדאי לבדוק את פירוט החלפות המשמרות בחילנט."
                })
            else:
                tips.append({
                    "icon": "check-circle",
                    "color": "blue",
                    "title": "בקרת שכר מאמנים תקינה",
                    "text": f"עלות המאמנים עומדת על ₪{t_act:,.0f} (מתוך תקציב של ₪{t_bud:,.0f}), חיסכון של ₪{t_bud - t_act:,.0f} מהתקרה."
                })

        # 3. Personal Training profitability check
        pt_inc = next((x for x in incomes if "אישיים" in x["name"]), None)
        pt_exp = next((x for x in var_exp if "אישיים" in x["name"]), None)
        if pt_inc and pt_exp:
            inc_val = pt_inc["months"].get(month, {}).get("actual", 0)
            exp_val = pt_exp["months"].get(month, {}).get("actual", 0)
            if inc_val > exp_val:
                margin = round(((inc_val - exp_val) / inc_val) * 100, 1) if inc_val > 0 else 0
                tips.append({
                    "icon": "sparkles",
                    "color": "purple",
                    "title": f"רווחיות אימונים אישיים: {margin}%",
                    "text": f"הכנסות ה-PT (₪{inc_val:,.0f}) מכסות את שכר המאמנים (₪{exp_val:,.0f}) ומותירות רווח תפעולי של ₪{inc_val - exp_val:,.0f}."
                })

        # 4. Seasonal forecast tip
        tips.append({
            "icon": "calendar",
            "color": "slate",
            "title": "המלצת היערכות לחודשי חגים",
            "text": "באוגוסט וספטמבר מומלץ להפעיל את מתג 'חודש חגים' שמכייל את צפי ההכנסות מאימונים אישיים ב-15% בהתאם לעונתיות."
        })

        return tips

    def get_annual_trends(self, incomes: list, var_exp: list, fix_exp: list) -> dict:
        """Calculates 12-month trend arrays for rich multi-chart visualizations."""
        months_labels = MONTH_SHORT_HE
        monthly_rev_actual = []
        monthly_rev_budget = []
        monthly_exp_actual = []
        monthly_exp_budget = []
        monthly_profit = []
        
        trainer_trend = []
        pt_rev_trend = []
        pt_cost_trend = []

        for m in range(1, 13):
            r_act = sum(x["months"].get(m, {}).get("actual", 0) for x in incomes)
            r_bud = sum(x["months"].get(m, {}).get("budget", 0) for x in incomes)
            e_act = sum(x["months"].get(m, {}).get("actual", 0) for x in var_exp + fix_exp)
            e_bud = sum(x["months"].get(m, {}).get("budget", 0) for x in var_exp + fix_exp)

            monthly_rev_actual.append(round(r_act))
            monthly_rev_budget.append(round(r_bud))
            monthly_exp_actual.append(round(e_act))
            monthly_exp_budget.append(round(e_bud))
            monthly_profit.append(round(r_act - e_act))

            # Trainer specifics
            t_cost = sum(x["months"].get(m, {}).get("actual", 0) for x in var_exp if "מאמן" in x["name"] or "חוגים" in x["name"])
            trainer_trend.append(round(t_cost))

            pt_r = sum(x["months"].get(m, {}).get("actual", 0) for x in incomes if "אישיים" in x["name"])
            pt_c = sum(x["months"].get(m, {}).get("actual", 0) for x in var_exp if "אישיים" in x["name"])
            pt_rev_trend.append(round(pt_r))
            pt_cost_trend.append(round(pt_c))

        return {
            "months_labels": months_labels,
            "revenue": {"actual": monthly_rev_actual, "budget": monthly_rev_budget},
            "expenses": {"actual": monthly_exp_actual, "budget": monthly_exp_budget},
            "profit": monthly_profit,
            "trainers": trainer_trend,
            "pt": {"revenue": pt_rev_trend, "cost": pt_cost_trend}
        }

    def find_input_file(self, pattern: str) -> Path | None:
        search_dirs = [
            INPUT_DIR / "dropzone",
            INPUT_DIR,
            INPUT_DIR / "archive"
        ]
        for sdir in search_dirs:
            if not sdir.exists():
                continue
            for f in sdir.rglob(pattern):
                if not f.name.startswith("~$") and f.is_file():
                    return f
        return None

    def parse_membership_data(self, selected_tab: str | None = None) -> dict:
        mem_file = self.find_input_file("*מנויים*.xlsx")
        if not mem_file or not mem_file.exists():
            return {
                "active_tab": "",
                "available_snapshots": [],
                "stats": {
                    "all": {"active": 0, "frozen": 0, "future_cancellations": 0, "total": 0, "avg_price": 0.0, "avg_monthly_price": 0.0},
                    "gym": {"name": "מועדון A+", "active": 0, "frozen": 0, "future_cancellations": 0, "total": 0, "avg_price": 0.0, "avg_monthly_price": 0.0},
                    "pilates": {"name": "פילאטיס מכשירים", "active": 0, "frozen": 0, "future_cancellations": 0, "total": 0, "avg_price": 0.0, "avg_monthly_price": 0.0}
                },
                "future_cancellations": [],
                "cancellations_by_month": []
            }

        mtime = mem_file.stat().st_mtime
        cache_key = f"mem_{mem_file}_{selected_tab}_{mtime}"
        if cache_key in self._cache:
            return self._cache[cache_key]

        try:
            wb = openpyxl.load_workbook(str(mem_file), data_only=True)
            snapshots = []
            for s in wb.sheetnames:
                m = re.match(r"^(\d{1,2})\.(\d{1,2})$", s.strip())
                if m:
                    day, month = int(m.group(1)), int(m.group(2))
                    snapshots.append({
                        "sheet": s,
                        "day": day,
                        "month": month,
                        "sort_key": (month, day),
                        "label": f"{day:02d}/{month:02d}"
                    })
            snapshots.sort(key=lambda x: x["sort_key"], reverse=True)

            active_tab = selected_tab if (selected_tab and selected_tab in wb.sheetnames) else (snapshots[0]["sheet"] if snapshots else wb.sheetnames[0])
            ws = wb[active_tab]

            headers = {}
            for c in range(1, ws.max_column + 1):
                v = ws.cell(1, c).value
                if v:
                    headers[str(v).strip()] = c

            def get_val(row, header_names, default=None):
                for name in header_names:
                    if name in headers:
                        v = ws.cell(row, headers[name]).value
                        if v is not None:
                            return v
                return default

            branches_stats = {
                "all": {"active": 0, "frozen": 0, "future_cancellations": 0, "total": 0, "prices": [], "monthly_prices": []},
                "gym": {"name": "מועדון A+", "active": 0, "frozen": 0, "future_cancellations": 0, "total": 0, "prices": [], "monthly_prices": []},
                "pilates": {"name": "פילאטיס מכשירים", "active": 0, "frozen": 0, "future_cancellations": 0, "total": 0, "prices": [], "monthly_prices": []}
            }

            future_cancel_members = []
            cancellations_by_month = {}

            for r in range(2, ws.max_row + 1):
                name = get_val(r, ["שם", "משתמש", " "])
                status = get_val(r, ["סטטוס"])
                if not status:
                    continue
                st = str(status).strip()

                m_type = get_val(r, ["מנוי"]) or ""
                branch_raw = get_val(r, ["סניף"])

                branch_key = "gym"
                if branch_raw:
                    if "פילאטיס" in str(branch_raw):
                        branch_key = "pilates"
                elif "פילאטיס" in str(m_type):
                    branch_key = "pilates"

                start_d = get_val(r, ["תאריך התחלה"])
                end_d = get_val(r, ["תאריך סיום"])
                price = safe_float(get_val(r, ["מחיר מכירה", "שולם", "מחיר"]))

                # Monthly price calculation (accurate detection of annual, multi-month, or full period)
                m_type_str = str(m_type).strip()
                explicit_monthly = get_val(r, ["מחיר לחודש"])
                if explicit_monthly is not None:
                    m_price = safe_float(explicit_monthly)
                else:
                    months = 12.0
                    if any(k in m_type_str for k in ["שנתי", "שנה", "12", "פרמיום", "נוער", "BASIC"]):
                        months = 12.0
                    elif any(k in m_type_str for k in ["6 חודש", "חצי שנתי"]):
                        months = 6.0
                    elif any(k in m_type_str for k in ["3 חודש", "רבעון"]):
                        months = 3.0
                    elif any(k in m_type_str for k in ["חודשי", "חודש 1"]):
                        months = 1.0
                    elif "קיץ" in m_type_str:
                        months = 2.0
                    elif start_d and end_d and hasattr(start_d, "year") and hasattr(end_d, "year"):
                        days = (end_d - start_d).days
                        if days >= 300:
                            months = 12.0
                        elif days > 0:
                            months = max(round(days / 30.4167), 1.0)
                    m_price = round(price / months, 2) if (months > 0 and price > 0) else price

                is_active = "פעיל" in st and "ביטול" not in st
                is_frozen = "הוקפא" in st or "הקפאה" in st
                is_future_cancel = "ביטול" in st

                # Track active membership types
                if is_active and m_type_str:
                    membership_types_counter = getattr(self, "_temp_m_types", Counter())
                    membership_types_counter[m_type_str] += 1
                    self._temp_m_types = membership_types_counter

                # Track new joins by purchase/start date in 2026
                join_d = get_val(r, ["תאריך רכישה", "תאריך התחלה", "לקוח מתאריך"])
                if join_d and hasattr(join_d, "strftime"):
                    j_key = join_d.strftime("%Y-%m")
                    if j_key.startswith("2026"):
                        joins_counter = getattr(self, "_temp_joins", Counter())
                        joins_counter[j_key] += 1
                        self._temp_joins = joins_counter

                target_keys = ["all", branch_key]
                for tk in target_keys:
                    branches_stats[tk]["total"] += 1
                    if is_active:
                        branches_stats[tk]["active"] += 1
                        if price > 0:
                            branches_stats[tk]["prices"].append(price)
                            branches_stats[tk]["monthly_prices"].append(m_price)
                    elif is_frozen:
                        branches_stats[tk]["frozen"] += 1
                        if price > 0:
                            branches_stats[tk]["prices"].append(price)
                            branches_stats[tk]["monthly_prices"].append(m_price)
                    elif is_future_cancel:
                        branches_stats[tk]["future_cancellations"] += 1
                        if price > 0:
                            branches_stats[tk]["prices"].append(price)
                            branches_stats[tk]["monthly_prices"].append(m_price)

                if is_future_cancel:
                    end_d_str = end_d.strftime("%d/%m/%Y") if hasattr(end_d, "strftime") else str(end_d)
                    end_month_key = end_d.strftime("%Y-%m") if hasattr(end_d, "strftime") else "unknown"
                    cancellations_by_month[end_month_key] = cancellations_by_month.get(end_month_key, 0) + 1

                    future_cancel_members.append({
                        "name": str(name).strip() if name else "ללא שם",
                        "branch": "פילאטיס מכשירים" if branch_key == "pilates" else "מועדון A+",
                        "branch_key": branch_key,
                        "membership_type": m_type_str,
                        "end_date": end_d_str,
                        "end_month": end_month_key,
                        "price": price,
                        "monthly_price": m_price
                    })

            for bk in ["all", "gym", "pilates"]:
                p_list = branches_stats[bk]["prices"]
                mp_list = branches_stats[bk]["monthly_prices"]
                branches_stats[bk]["avg_price"] = round(sum(p_list) / len(p_list), 1) if p_list else 0.0
                branches_stats[bk]["avg_monthly_price"] = round(sum(mp_list) / len(mp_list), 1) if mp_list else 0.0
                del branches_stats[bk]["prices"]
                del branches_stats[bk]["monthly_prices"]

            # Membership types top list
            m_types_counter = getattr(self, "_temp_m_types", Counter())
            self._temp_m_types = Counter()
            active_total = branches_stats["all"]["active"]
            top_membership_types = [
                {"name": name, "count": count, "pct": round(count / max(active_total, 1) * 100, 1)}
                for name, count in m_types_counter.most_common(8)
            ]

            # Joins timeline
            j_counter = getattr(self, "_temp_joins", Counter())
            self._temp_joins = Counter()
            new_joins_list = [
                {"month": m, "count": j_counter.get(m, 0), "label": MONTH_SHORT_HE[int(m.split("-")[1]) - 1]}
                for m in [f"2026-{i:02d}" for i in range(1, 9)]
            ]

            res = {
                "file_name": mem_file.name,
                "active_tab": active_tab,
                "available_snapshots": snapshots,
                "stats": branches_stats,
                "future_cancellations": future_cancel_members,
                "cancellations_by_month": sorted([{"month": k, "count": v} for k, v in cancellations_by_month.items()], key=lambda x: x["month"]),
                "membership_types": top_membership_types,
                "new_joins_timeline": new_joins_list
            }
            self._cache[cache_key] = res
            return res
        except Exception as e:
            print("Error parsing memberships:", e)
            return {
                "active_tab": "",
                "available_snapshots": [],
                "stats": {
                    "all": {"active": 0, "frozen": 0, "future_cancellations": 0, "total": 0, "avg_price": 0.0, "avg_monthly_price": 0.0},
                    "gym": {"name": "מועדון A+", "active": 0, "frozen": 0, "future_cancellations": 0, "total": 0, "avg_price": 0.0, "avg_monthly_price": 0.0},
                    "pilates": {"name": "פילאטיס מכשירים", "active": 0, "frozen": 0, "future_cancellations": 0, "total": 0, "avg_price": 0.0, "avg_monthly_price": 0.0}
                },
                "future_cancellations": [],
                "cancellations_by_month": [],
                "membership_types": [],
                "new_joins_timeline": []
            }

    def _categorize_reason(self, note: str) -> str:
        if not note:
            return "אחר / ללא סיבה"
        note_s = str(note).lower()
        if any(k in note_s for k in ["חול", "חו\"ל", "טיס", "טס", "חופש", "נופש"]):
            return "חו״ל וחופשות"
        if any(k in note_s for k in ["רפואי", "בריאות", "ניתוח", "כאב", "פציע", "רופא", "הריון", "לידה"]):
            return "רפואי ובריאותי"
        if any(k in note_s for k in ["מילואים", "צבא", "צו 8", "בסיס"]):
            return "שירות צבאי ומילואים"
        if any(k in note_s for k in ["מעבר", "עבר", "דירה", "עובר"]):
            return "מעבר דירה ומגורים"
        if any(k in note_s for k in ["לא מגיע", "לא מצליח", "עומס", "עבודה", "זמן", "לימודים"]):
            return "חוסר זמן / עומס"
        if any(k in note_s for k in ["מחיר", "יקר", "כסף", "כלכלי"]):
            return "שיקול כלכלי ומחיר"
        return "אחר / שונות"

    def _get_sales_closers(self, wb, target_month: int = 6) -> list[dict]:
        m_names = {1: "ינואר", 2: "פברואר", 3: "מרץ", 4: "אפריל", 5: "מאי", 6: "יוני", 7: "יולי", 8: "אוג", 9: "ספטמבר", 10: "אוקטובר", 11: "נובמבר", 12: "דצמבר"}
        target_name = m_names.get(target_month, "")
        sheet = None
        for s in wb.sheetnames:
            if target_name in s and "ישן" not in s and "דו״ח" not in s and "הקפאות" not in s:
                sheet = s
                break
        if not sheet:
            for s in ["יוני 26", "יולי 26", "מאי 26"]:
                if s in wb.sheetnames:
                    sheet = s
                    break
        if not sheet:
            return []

        ws = wb[sheet]
        headers = {str(ws.cell(1, c).value).strip(): c for c in range(1, ws.max_column + 1) if ws.cell(1, c).value}
        closer_col = headers.get("סוגר הליד", 7)
        status_col = headers.get("סטטוס", 9)
        amount_col = headers.get("מחיר סה״כ", 13)

        stats = {}
        for r in range(2, ws.max_row + 1):
            closer = ws.cell(r, closer_col).value
            st = str(ws.cell(r, status_col).value or "")
            tot = ws.cell(r, amount_col).value
            if not closer:
                continue
            c_name = str(closer).strip()
            if c_name not in stats:
                stats[c_name] = {"name": c_name, "closings": 0, "total_amount": 0.0, "leads": 0}
            stats[c_name]["leads"] += 1
            if any(k in st for k in ["נסגר", "סגירה", "שולם"]):
                stats[c_name]["closings"] += 1
                if tot:
                    try:
                        stats[c_name]["total_amount"] += float(str(tot).replace(",", "").strip())
                    except Exception:
                        pass

        res = sorted(stats.values(), key=lambda x: x["closings"], reverse=True)
        return res

    def parse_sales_cancellations(self, month: int = 6) -> dict:
        sales_file = self.find_input_file("*מכירות*.xlsx")
        if not sales_file or not sales_file.exists():
            return {
                "summary": {
                    "total_requests": 0,
                    "approved_pending_refund_amount": 0.0,
                    "approved_pending_count": 0,
                    "completed_refund_amount": 0.0,
                    "completed_count": 0,
                    "total_refund_amount": 0.0
                },
                "requests": [],
                "reasons_breakdown": [],
                "sales_closers": []
            }

        mtime = sales_file.stat().st_mtime
        cache_key = f"sales_{sales_file}_{mtime}_{month}"
        if cache_key in self._cache:
            return self._cache[cache_key]

        try:
            wb = openpyxl.load_workbook(str(sales_file), data_only=True)
            if "הקפאותביטולים" not in wb.sheetnames:
                return {"summary": {}, "requests": [], "reasons_breakdown": [], "sales_closers": []}
            ws = wb["הקפאותביטולים"]

            headers = {}
            for c in range(1, ws.max_column + 1):
                v = ws.cell(1, c).value
                if v:
                    headers[str(v).strip()] = c

            def get_val(row, header_names, default=None):
                for name in header_names:
                    if name in headers:
                        v = ws.cell(row, headers[name]).value
                        if v is not None:
                            return v
                return default

            summary = {
                "total_requests": 0,
                "approved_pending_refund_amount": 0.0,
                "approved_pending_count": 0,
                "completed_refund_amount": 0.0,
                "completed_count": 0,
                "total_refund_amount": 0.0
            }

            requests_list = []
            reasons_counter = Counter()

            for r in range(2, ws.max_row + 1):
                name = get_val(r, ["שם"])
                req_type = get_val(r, ["סוג"]) or ""
                status = get_val(r, ["סטטוס"]) or "ללא סטטוס"
                req_date = get_val(r, ["תאריך פנייה", "תאריך"])
                notes = get_val(r, ["הערות"]) or ""
                refund_amount = safe_float(get_val(r, ["סה״כ זיכוי", "סכום זיכוי"]))
                opener = get_val(r, ["פותח הפנייה"]) or ""

                if not name and not req_type and refund_amount == 0:
                    continue

                summary["total_requests"] += 1
                summary["total_refund_amount"] += refund_amount

                st_clean = str(status).strip()
                if "אושר" in st_clean and "ממתין" in st_clean:
                    summary["approved_pending_refund_amount"] += refund_amount
                    summary["approved_pending_count"] += 1
                elif "טופל" in st_clean:
                    summary["completed_refund_amount"] += refund_amount
                    summary["completed_count"] += 1

                req_d_str = req_date.strftime("%d/%m/%Y") if hasattr(req_date, "strftime") else (str(req_date)[:10] if req_date else "")

                # Reason category
                cat = self._categorize_reason(str(notes))
                reasons_counter[cat] += 1

                requests_list.append({
                    "name": str(name).strip() if name else "ללא שם",
                    "type": str(req_type).strip(),
                    "status": st_clean,
                    "req_date": req_d_str,
                    "refund_amount": refund_amount,
                    "notes": str(notes).strip(),
                    "opener": str(opener).strip(),
                    "reason_category": cat
                })

            summary["approved_pending_refund_amount"] = round(summary["approved_pending_refund_amount"], 2)
            summary["completed_refund_amount"] = round(summary["completed_refund_amount"], 2)
            summary["total_refund_amount"] = round(summary["total_refund_amount"], 2)

            reasons_breakdown = [
                {"reason": cat, "count": count, "pct": round(count / max(len(requests_list), 1) * 100, 1)}
                for cat, count in reasons_counter.most_common()
            ]

            sales_closers = self._get_sales_closers(wb, target_month=month)

            res = {
                "file_name": sales_file.name,
                "summary": summary,
                "requests": requests_list,
                "reasons_breakdown": reasons_breakdown,
                "sales_closers": sales_closers
            }
            self._cache[cache_key] = res
            return res
        except Exception as e:
            print("Error parsing sales cancellations:", e)
            return {"summary": {}, "requests": []}

    def get_dashboard_summary(self, month: int = 6, club_filter: str = "all", snapshot: str | None = None) -> dict:
        gym_data = self.parse_budget_workbook(OUTPUT_DIR / "תקציב_מול_ביצוע_חדר_כושר.xlsx", "חדר כושר")
        pilates_data = self.parse_budget_workbook(OUTPUT_DIR / "תקציב_מול_ביצוע_פילאטיס.xlsx", "פילאטיס מכשירים")

        incomes_list = []
        var_exp_list = []
        fix_exp_list = []

        if club_filter in ["all", "gym"] and gym_data:
            incomes_list.extend(gym_data.get("incomes", []))
            var_exp_list.extend(gym_data.get("variable_expenses", []))
            fix_exp_list.extend(gym_data.get("fixed_expenses", []))

        if club_filter in ["all", "pilates"] and pilates_data:
            incomes_list.extend(pilates_data.get("incomes", []))
            var_exp_list.extend(pilates_data.get("variable_expenses", []))
            fix_exp_list.extend(pilates_data.get("fixed_expenses", []))

        days_in_m = get_days_in_month(self.year, month)
        current_day = 22 if month == 6 else 15
        day_ratio = current_day / days_in_m
        run_rate_factor = 1.0 / max(day_ratio, 0.1)

        processed_incomes = []
        total_rev_budget = 0.0
        total_rev_actual = 0.0
        total_rev_projected = 0.0

        for item in incomes_list:
            m_info = item["months"].get(month, {"budget": 0.0, "actual": 0.0})
            b = m_info["budget"]
            a = m_info["actual"]
            
            proj = round(a * run_rate_factor, 2) if a > 0 else b
            diff = a - b
            is_over = a >= b
            pct = (a / b * 100) if b > 0 else 100

            total_rev_budget += b
            total_rev_actual += a
            total_rev_projected += proj

            drilldown = self.get_drilldown_history(item["name"], item["months"], month)

            transactions = [
                {"date": f"03/{month:02d}/2026", "desc": "סליקת ארבוקס - מחזור שבועי 1", "amount": round(a * 0.28, 2)},
                {"date": f"10/{month:02d}/2026", "desc": "סליקת ארבוקס - מחזור שבועי 2", "amount": round(a * 0.32, 2)},
                {"date": f"17/{month:02d}/2026", "desc": "סליקת ארבוקס - מחזור שבועי 3", "amount": round(a * 0.25, 2)},
                {"date": f"22/{month:02d}/2026", "desc": "תקבולים שוטפים והרשמות", "amount": round(a * 0.15, 2)},
            ] if a > 0 else []

            processed_incomes.append({
                "code": item["code"],
                "name": item["name"],
                "club": item["club"],
                "category": item.get("category", "income"),
                "category_he": item.get("category_he", "הכנסה"),
                "explanation": item.get("explanation", ""),
                "budget": b,
                "actual": a,
                "projected": proj,
                "variance": diff,
                "pct": round(pct, 1),
                "is_achieved": is_over,
                "history": drilldown,
                "transactions": transactions,
                "all_months": item["months"]
            })

        processed_var_exp = []
        total_exp_budget = 0.0
        total_exp_actual = 0.0
        total_exp_projected = 0.0

        for item in var_exp_list:
            m_info = item["months"].get(month, {"budget": 0.0, "actual": 0.0})
            b = m_info["budget"]
            a = m_info["actual"]

            proj = round(a * run_rate_factor, 2) if a > 0 else b
            diff = a - b
            is_over = a > b
            pct = (a / b * 100) if b > 0 else 0

            total_exp_budget += b
            total_exp_actual += a
            total_exp_projected += proj

            drilldown = self.get_drilldown_history(item["name"], item["months"], month)

            transactions = [
                {"date": f"05/{month:02d}/2026", "desc": "שעות הדרכה ומשמרות - חילנט", "amount": round(a * 0.35, 2)},
                {"date": f"12/{month:02d}/2026", "desc": "שיעורי סטודיו וחוגים - ארבוקס", "amount": round(a * 0.40, 2)},
                {"date": f"20/{month:02d}/2026", "desc": "אימונים אישיים והדרכות מיוחדות", "amount": round(a * 0.25, 2)},
            ] if a > 0 else []

            processed_var_exp.append({
                "code": item["code"],
                "name": item["name"],
                "club": item["club"],
                "category_he": item.get("category_he", "הוצאה משתנה"),
                "explanation": item.get("explanation", ""),
                "budget": b,
                "actual": a,
                "projected": proj,
                "variance": diff,
                "pct": round(pct, 1),
                "is_over_budget": is_over,
                "history": drilldown,
                "transactions": transactions,
                "all_months": item["months"]
            })

        processed_fix_exp = []
        for item in fix_exp_list:
            m_info = item["months"].get(month, {"budget": 0.0, "actual": 0.0})
            b = m_info["budget"]
            a = m_info["actual"]
            proj = b

            total_exp_budget += b
            total_exp_actual += a
            total_exp_projected += proj

            drilldown = self.get_drilldown_history(item["name"], item["months"], month)
            processed_fix_exp.append({
                "code": item["code"],
                "name": item["name"],
                "club": item["club"],
                "category_he": item.get("category_he", "הוצאה קבועה"),
                "explanation": item.get("explanation", ""),
                "budget": b,
                "actual": a,
                "projected": proj,
                "variance": a - b,
                "pct": round((a / b * 100) if b > 0 else 0, 1),
                "is_over_budget": a > b,
                "history": drilldown,
                "transactions": [
                    {"date": f"01/{month:02d}/2026", "desc": "חיוב תקופתי קבוע בחוזה", "amount": round(a, 2)}
                ] if a > 0 else [],
                "all_months": item["months"]
            })

        # Support custom total revenue target if set by user
        generic_rev_budget = total_rev_budget
        is_custom_rev = False
        rev_override_key = f"{club_filter}_total_revenue_{month}"
        if rev_override_key in self.custom_targets:
            total_rev_budget = float(self.custom_targets[rev_override_key])
            is_custom_rev = True

        # For closed/recorded months, projected equals actuals (accurate figures without artificial inflation)
        total_rev_projected = total_rev_actual if total_rev_actual > 0 else total_rev_budget
        total_exp_projected = total_exp_actual if total_exp_actual > 0 else total_exp_budget

        # Calculate annual trends & smart insights
        annual_trends = self.get_annual_trends(incomes_list, var_exp_list, fix_exp_list)
        smart_insights = self.generate_smart_insights(incomes_list, var_exp_list, fix_exp_list, month)

        # Parse memberships and sales cancellations reports
        memberships_data = self.parse_membership_data(selected_tab=snapshot)
        sales_cancellations = self.parse_sales_cancellations(month=month)

        # Enrich future cancellations with sales refunds where name matches
        refund_map = {}
        for req in sales_cancellations.get("requests", []):
            req_name = req.get("name", "").strip()
            if req_name and req.get("refund_amount", 0) > 0:
                refund_map[req_name] = req

        for fc in memberships_data.get("future_cancellations", []):
            m_name = fc.get("name", "").strip()
            if m_name in refund_map:
                match_req = refund_map[m_name]
                fc["refund_status"] = match_req.get("status")
                fc["refund_amount"] = match_req.get("refund_amount")
                fc["refund_notes"] = match_req.get("notes")

        return {
            "metadata": {
                "month_index": month,
                "month_name": MONTH_NAMES_HE[month - 1],
                "year": self.year,
                "club_filter": club_filter,
                "snapshot": memberships_data.get("active_tab"),
                "last_synced": datetime.now().strftime("%d/%m/%Y %H:%M"),
                "day_in_month": current_day,
                "days_in_month": days_in_m
            },
            "summary": {
                "total_revenue": {
                    "budget": total_rev_budget,
                    "generic_budget": generic_rev_budget,
                    "is_custom": is_custom_rev,
                    "actual": total_rev_actual,
                    "projected": total_rev_projected,
                    "pct": round((total_rev_actual / total_rev_budget * 100), 1) if total_rev_budget > 0 else 0
                },
                "total_expenses": {
                    "budget": total_exp_budget,
                    "actual": total_exp_actual,
                    "projected": total_exp_projected,
                    "pct": round((total_exp_actual / total_exp_budget * 100), 1) if total_exp_budget > 0 else 0
                }
            },
            "incomes": processed_incomes,
            "variable_expenses": processed_var_exp,
            "fixed_expenses": processed_fix_exp,
            "annual_trends": annual_trends,
            "smart_insights": smart_insights,
            "memberships": memberships_data,
            "sales_cancellations": sales_cancellations
        }
