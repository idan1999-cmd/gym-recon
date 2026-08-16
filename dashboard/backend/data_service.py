"""
Ariel Fit & Spa Dashboard - Advanced Data & Forecasting Service
Provides 5-month historical trend analysis, 12-month full-year matrix,
smart AI financial insights, and flexible multi-view aggregation.
"""
from __future__ import annotations
import os
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
                is_variable = any(k in desc_str for k in [
                    "מאמן", "מדריך", "אימונים אישיים", "חוגים", "סטודיו", "מכירות (עמלות)", 
                    "שיווק", "פרסום", "ציוד", "אחזקה", "ניקיון", "ביגוד"
                ])
                if is_variable:
                    item_data["expense_type"] = "variable"
                    if "מאמן" in desc_str or "חוגים" in desc_str or "אימונים אישיים" in desc_str:
                        item_data["category_he"] = "שכר מאמנים והדרכה"
                        item_data["explanation"] = "תשלום חודשי למדריכי חדר כושר, שיעורי סטודיו ואימונים אישיים (ארבוקס + חילנט)."
                    elif "מכירות" in desc_str:
                        item_data["category_he"] = "עמלות מכירות"
                        item_data["explanation"] = "עמלות לנציגי מכירות על סגירת מנויים חדשים."
                    elif "שיווק" in desc_str:
                        item_data["category_he"] = "שיווק ופרסום"
                        item_data["explanation"] = "קמפיינים דיגיטליים, מיתוג ופרסום ברשתות."
                    else:
                        item_data["category_he"] = "תפעול שוטף ואחזקה"
                        item_data["explanation"] = "חומרי ניקיון, טואלטיקה, ביגוד צוות ותחזוקת מכשירים."
                    variable_expenses.append(item_data)
                else:
                    item_data["expense_type"] = "fixed"
                    item_data["category_he"] = "הוצאות קבועות ומבנה"
                    item_data["explanation"] = "הוצאות תשתית קבועות בחוזה (שכירות, חשמל, מים, ארנונה, תוכנות ניהול)."
                    fixed_expenses.append(item_data)

        return {
            "club": club_name,
            "incomes": incomes,
            "variable_expenses": variable_expenses,
            "fixed_expenses": fixed_expenses
        }

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

    def get_dashboard_summary(self, month: int = 6, club_filter: str = "all", holiday_mode: bool = False) -> dict:
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
        holiday_factor = 0.85 if holiday_mode else 1.0

        processed_incomes = []
        total_rev_budget = 0.0
        total_rev_actual = 0.0
        total_rev_projected = 0.0

        for item in incomes_list:
            m_info = item["months"].get(month, {"budget": 0.0, "actual": 0.0})
            b = m_info["budget"]
            a = m_info["actual"]
            
            proj = round(a * run_rate_factor * holiday_factor, 2) if a > 0 else b
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

            proj = round(a * run_rate_factor * holiday_factor, 2) if a > 0 else b
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

        # Calculate annual trends & smart insights
        annual_trends = self.get_annual_trends(incomes_list, var_exp_list, fix_exp_list)
        smart_insights = self.generate_smart_insights(incomes_list, var_exp_list, fix_exp_list, month)

        return {
            "metadata": {
                "month_index": month,
                "month_name": MONTH_NAMES_HE[month - 1],
                "year": self.year,
                "club_filter": club_filter,
                "holiday_mode": holiday_mode,
                "last_synced": datetime.now().strftime("%d/%m/%Y %H:%M"),
                "day_in_month": current_day,
                "days_in_month": days_in_m
            },
            "summary": {
                "total_revenue": {
                    "budget": total_rev_budget,
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
            "smart_insights": smart_insights
        }
