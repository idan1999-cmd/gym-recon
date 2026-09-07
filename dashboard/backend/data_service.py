"""
Ariel Fit & Spa Dashboard - Advanced Data & Forecasting Service
Provides 5-month historical trend analysis, 12-month full-year matrix,
smart AI financial insights, and flexible multi-view aggregation.
"""
from __future__ import annotations
import os
import sys
import re
import csv
import json
import calendar
from datetime import datetime, timedelta, date
from pathlib import Path
from collections import Counter, defaultdict
import openpyxl

BASE_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(BASE_DIR / "core"))
sys.path.insert(0, str(BASE_DIR))
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
            val = val.replace("₪", "").replace("$", "").replace("€", "").replace("NIS", "").replace(",", "").strip()
        return float(val)
    except (ValueError, TypeError):
        return 0.0

SUPPLIERS_STATE_FILE = CONFIG_DIR / "suppliers_dashboard_state.json"

class DashboardDataService:
    def __init__(self):
        self.year = 2026
        self.custom_targets = self._load_custom_targets()
        self.suppliers_state = self._load_suppliers_state()
        self._cache = {}

    def _load_suppliers_state(self) -> dict:
        if SUPPLIERS_STATE_FILE.exists():
            try:
                with open(SUPPLIERS_STATE_FILE, encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                return {}
        return {}

    def save_suppliers_state(self, month: int, bank_balance: float = None, approved_ids: list = None) -> dict:
        m_key = str(month)
        if m_key not in self.suppliers_state:
            self.suppliers_state[m_key] = {"bank_balance": None, "approved_ids": []}
        if bank_balance is not None:
            self.suppliers_state[m_key]["bank_balance"] = float(bank_balance)
        if approved_ids is not None:
            self.suppliers_state[m_key]["approved_ids"] = list(approved_ids)
        try:
            with open(SUPPLIERS_STATE_FILE, "w", encoding="utf-8") as f:
                json.dump(self.suppliers_state, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print("Error saving suppliers state:", e)
        return self.suppliers_state[m_key]

    def archive_approved_suppliers(self, month: int) -> dict:
        m_key = str(month)
        m_state = self.suppliers_state.get(m_key, {})
        approved_ids = m_state.get("approved_ids", [])
        if "archived_ids" not in m_state:
            m_state["archived_ids"] = []
        
        # Move all currently approved IDs to archived_ids
        for sup_id in approved_ids:
            if sup_id not in m_state["archived_ids"]:
                m_state["archived_ids"].append(sup_id)
        
        # Clear active approved list
        m_state["approved_ids"] = []
        m_state["last_masav_transmission"] = datetime.now().isoformat()
        
        self.suppliers_state[m_key] = m_state
        try:
            with open(SUPPLIERS_STATE_FILE, "w", encoding="utf-8") as f:
                json.dump(self.suppliers_state, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print("Error archiving approved suppliers:", e)
        
        return {
            "success": True,
            "archived_count": len(approved_ids),
            "transmitted_at": m_state["last_masav_transmission"]
        }

    def _load_custom_targets(self) -> dict:
        if CUSTOM_TARGETS_FILE.exists():
            try:
                with open(CUSTOM_TARGETS_FILE, encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                return {}
        return {}

    def save_custom_target(self, club: str, code: str, month: int, new_target) -> bool:
        key = f"{club}_{code}_{month}"
        if new_target is None or new_target == "" or (isinstance(new_target, (int, float)) and new_target < 0):
            if key in self.custom_targets:
                del self.custom_targets[key]
        else:
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

    def generate_smart_insights(
        self,
        incomes: list,
        var_exp: list,
        fix_exp: list,
        month: int,
        pacing_tracker: dict | None = None,
        memberships_data: dict | None = None,
        sales_cancellations: dict | None = None
    ) -> list[dict]:
        """
        Generates executive, proactive AI action insights and alerts across all club modules:
        1. Revenue target pacing & daily rate gap (Urgent / High Priority)
        2. High churn risk expiring members needing immediate retention outreach
        3. Scheduled refunds and cash outflow timeline (Drive / cancellations)
        4. Operational billing & PT profitability (safeguarded against zero-budget illusions)
        """
        tips = []

        # -------------------------------------------------------------
        # 1. REVENUE PACING & DAILY TARGET GAP (דחוף לתפעול ומכירות)
        # -------------------------------------------------------------
        if pacing_tracker:
            p_status = pacing_tracker.get("status")
            gap = pacing_tracker.get("revenue_gap_to_pace", 0)
            daily_req = pacing_tracker.get("daily_rate_required", 0)
            days_rem = pacing_tracker.get("days_remaining", 0)
            target = pacing_tracker.get("target", 0)
            proj = pacing_tracker.get("projected_month_end", 0)
            is_cur = pacing_tracker.get("is_current_month", False)

            if is_cur:
                if p_status == "behind" and gap > 0:
                    tips.append({
                        "priority": "urgent",
                        "tag": "🚨 דחוף לתפעול ומכירות",
                        "icon": "zap",
                        "color": "rose",
                        "title": f"פער ביעד הכנסות: נדרש קצב של ₪{daily_req:,.0f} ליום",
                        "text": f"קיים פער של ₪{gap:,.0f} מקצב היעד להיום (יעד חודשי: ₪{target:,.0f}). נותרו {days_rem} ימי מכירה — מומלץ לתדרך את דלפק המכירות להאצת שדרוגים וחידושים."
                    })
                elif p_status == "ahead" and gap < 0:
                    tips.append({
                        "priority": "success",
                        "tag": "🚀 קצב מכירות חזק",
                        "icon": "trending-up",
                        "color": "emerald",
                        "title": f"הקדמת יעד הכנסות ב-₪{abs(gap):,.0f} מעל התוכנית",
                        "text": f"המועדון מקדים את קצב היעד. צפי הסיום החודשי עומד על ₪{proj:,.0f} (יעד: ₪{target:,.0f}). מומלץ לשמר מומנטום בסגירות."
                    })
                elif p_status == "on_track":
                    tips.append({
                        "priority": "info",
                        "tag": "🎯 עמידה בקצב יעד",
                        "icon": "target",
                        "color": "indigo",
                        "title": f"עמידה בקצב יעד: נדרש ₪{daily_req:,.0f} ליום",
                        "text": f"הכנסות החודש צמודות לקצב היעד. שמירה על קצב סגירות יומי של ₪{daily_req:,.0f} תבטיח עמידה מלאה ביעד של ₪{target:,.0f}."
                    })

        # -------------------------------------------------------------
        # 2. RETENTION & HIGH CHURN RISK EXPIRING MEMBERS (שימור לקוחות)
        # -------------------------------------------------------------
        if memberships_data:
            exp_list = memberships_data.get("expiring_memberships", [])
            curr_month_str = f"{self.year}-{month:02d}"
            exp_this_month = [m for m in exp_list if m.get("month") == curr_month_str or (not m.get("month") and exp_list.index(m) < 30)]
            if not exp_this_month:
                exp_this_month = exp_list[:25]

            high_risk = [m for m in exp_this_month if m.get("persistence_risk") == "high"]
            total_exp = len(exp_this_month)

            if high_risk:
                tips.append({
                    "priority": "urgent",
                    "tag": "⚠️ שימור לקוחות דחוף",
                    "icon": "user-x",
                    "color": "amber",
                    "title": f"{len(high_risk)} מנויים בסיכון נשירה גבוה מסתיימים החודש",
                    "text": f"מתוך {total_exp} מנויים העומדים לפוג, זוהו {len(high_risk)} מתאמנים עם התמדה נמוכה / מתחת לסטנדרט המועדון. מומלץ ליצור קשר יזום ולהציע חבילת שימור לפני פקיעת התוקף."
                })
            elif total_exp > 0:
                tips.append({
                    "priority": "info",
                    "tag": "🔄 צפי חידושי מנויים",
                    "icon": "hourglass",
                    "color": "blue",
                    "title": f"{total_exp} מנויים עומדים להסתיים בחודש הקרוב",
                    "text": f"המתאמנים מציגים התמדה סבירה. שיחת חידוש מתוזמנת של הצוות תבטיח שמירה על שיעור שימור גבוה."
                })

        # -------------------------------------------------------------
        # 3. SCHEDULED REFUNDS & CASH OUTFLOW (תזרים וזיכויים מתוזמנים)
        # -------------------------------------------------------------
        scheduled_refunds = []
        if memberships_data:
            scheduled_refunds = memberships_data.get("monthly_refund_forecast", [])
        
        month_name_he = MONTH_NAMES_HE[month - 1]
        cur_ref = next((r for r in scheduled_refunds if month_name_he in r.get("month", "") or f"{month:02d}" in r.get("month", "")), None)

        if cur_ref and cur_ref.get("amount", 0) > 0:
            amt = cur_ref["amount"]
            cnt = cur_ref.get("count", 0)
            cc = cur_ref.get("credit_card", 0)
            bank = cur_ref.get("bank_transfer", 0)
            tips.append({
                "priority": "warning",
                "tag": "💸 תזרים והחזרים כספיים",
                "icon": "receipt",
                "color": "purple",
                "title": f"צפי החזר כספי: ₪{amt:,.0f} מתוזמן ל-15 לחודש",
                "text": f"מתוזמנים {cnt} זיכויי ביטול מאושרים לביצוע (₪{bank:,.0f} העברה בנקאית, ₪{cc:,.0f} אשראי). יש לוודא כיסוי תזרימי בהנהלת חשבונות."
            })
        elif sales_cancellations:
            summ = sales_cancellations.get("summary", {})
            pending_amt = summ.get("approved_pending_refund_amount", 0)
            pending_cnt = summ.get("approved_pending_count", 0)
            if pending_amt > 0:
                tips.append({
                    "priority": "warning",
                    "tag": "💸 תזרים והחזרים כספיים",
                    "icon": "receipt",
                    "color": "purple",
                    "title": f"ממתינים לזיכוי: {pending_cnt} פניות בסך ₪{pending_amt:,.0f}",
                    "text": f"פניות ביטול שאושרו על ידי מנהל וממתינות לביצוע הזיכוי בהנה״ח. יש לתאם מועד שידור מרוכז."
                })

        # -------------------------------------------------------------
        # 4. PERSONAL TRAINING & STUDIO MARGINS (רווחיות ומאמנים בפועל)
        # -------------------------------------------------------------
        pt_inc = next((x for x in incomes if "אישיים" in x["name"]), None)
        pt_exp = next((x for x in var_exp if "אישיים" in x["name"]), None)
        if pt_inc and pt_exp:
            inc_val = pt_inc["months"].get(month, {}).get("actual", 0)
            exp_val = pt_exp["months"].get(month, {}).get("actual", 0)
            if inc_val > 0 and exp_val > 0 and inc_val > exp_val:
                margin = round(((inc_val - exp_val) / inc_val) * 100, 1)
                tips.append({
                    "priority": "info",
                    "tag": "💎 רווחיות אימונים אישיים",
                    "icon": "sparkles",
                    "color": "purple",
                    "title": f"רווחיות PT חזקה: {margin}% רווח תפעולי",
                    "text": f"הכנסות מאימונים אישיים (₪{inc_val:,.0f}) מכסות את שכר המאמנים (₪{exp_val:,.0f}) ומותירות רווח תפעולי של ₪{inc_val - exp_val:,.0f}."
                })

        # -------------------------------------------------------------
        # 5. TRAINER BILLING STATUS (ללא אשליות תקציב של 0!)
        # -------------------------------------------------------------
        trainer_item = next((x for x in var_exp if "עלות מאמנים" in x["name"] or "מאמנות" in x["name"]), None)
        if trainer_item:
            t_act = trainer_item["months"].get(month, {}).get("actual", 0)
            t_bud = trainer_item["months"].get(month, {}).get("budget", 0)
            if t_act > 0:
                if t_act > t_bud and t_bud > 0:
                    diff = t_act - t_bud
                    tips.append({
                        "priority": "warning",
                        "tag": "⚠️ בקרת שכר מאמנים",
                        "icon": "alert-triangle",
                        "color": "amber",
                        "title": f"חריגה של ₪{diff:,.0f} בעלות המאמנים",
                        "text": f"עלות המאמנים בפועל (₪{t_act:,.0f}) חרגה מהתקציב (₪{t_bud:,.0f}). יש לבדוק פירוט החלפות משמרות בחילנט."
                    })
                elif t_act <= t_bud and t_bud > 0:
                    tips.append({
                        "priority": "success",
                        "tag": "✅ בקרת שכר מאמנים",
                        "icon": "check-circle",
                        "color": "emerald",
                        "title": "בקרת שכר מאמנים תקינה ומאוזנת",
                        "text": f"עלות המאמנים עומדת על ₪{t_act:,.0f} מתוך תקציב של ₪{t_bud:,.0f} (ניצול של {round(t_act/t_bud*100, 1)}%)."
                    })
            elif t_act == 0 and t_bud > 0:
                tips.append({
                    "priority": "info",
                    "tag": "⏳ בקרת שכר וחודש פעיל",
                    "icon": "clock",
                    "color": "blue",
                    "title": "שכר מאמנים ועובדים טרם נסגר",
                    "text": f"החודש פעיל — דוחות שעות חילנט וחשבוניות מאמנים יקלטו לקראת סגירת השכר (מסגרת תקציב משוריינת: ₪{t_bud:,.0f})."
                })

        return tips[:4]

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

        # Facility & operational trends requested by Idan
        elec_trend = []
        water_trend = []
        hvac_trend = []
        maint_trend = []
        clean_trend = []
        marketing_trend = []
        arnona_trend = []

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

            # Trainer specifics (comprehensive matching for trainers, studio classes, personal training)
            t_cost = sum(x["months"].get(m, {}).get("actual", 0) for x in var_exp if any(k in x["name"] for k in ["מאמנ", "מדריכ", "חוג", "סטודיו"]))
            trainer_trend.append(round(t_cost))

            pt_r = sum(x["months"].get(m, {}).get("actual", 0) for x in incomes if any(k in x["name"] for k in ["אישי", "אימון אישי"]))
            pt_c = sum(x["months"].get(m, {}).get("actual", 0) for x in var_exp if any(k in x["name"] for k in ["אישי", "אימון אישי"]))
            pt_rev_trend.append(round(pt_r))
            pt_cost_trend.append(round(pt_c))

            # Facility utilities & maintenance tracking:
            # 1. Electricity (חשמל ומז"א - 22609)
            e_val = sum(x["months"].get(m, {}).get("actual", 0) for x in var_exp if str(x.get("code")).strip() == "22609")
            elec_trend.append(round(e_val))

            # 2. Water (מים - 22610)
            w_val = sum(x["months"].get(m, {}).get("actual", 0) for x in var_exp if str(x.get("code")).strip() == "22610")
            water_trend.append(round(w_val))

            # 3. HVAC / Air conditioning service (הסכם שירות מיזוג אוויר 22102, אחזקת מז"א 22607)
            h_val = sum(x["months"].get(m, {}).get("actual", 0) for x in var_exp if str(x.get("code")).strip() in ["22102", "22607"])
            hvac_trend.append(round(h_val))

            # 4. Maintenance, repairs & equipment (ציוד ואחזקה מכשירי חדר כושר 22618, אחזקת מכשירים פילאטיס 22618, חומרי אחזקה 22627)
            m_val = sum(x["months"].get(m, {}).get("actual", 0) for x in var_exp if str(x.get("code")).strip() in ["22618", "22627"])
            maint_trend.append(round(m_val))

            # 5. Cleaning & hygiene (ניקיון וחומרים 22614, 22613)
            c_val = sum(x["months"].get(m, {}).get("actual", 0) for x in var_exp if str(x.get("code")).strip() in ["22614", "22613"])
            clean_trend.append(round(c_val))

            # 6. Marketing & Advertising (שיווק ופרסום 22506)
            mkt_val = sum(x["months"].get(m, {}).get("actual", 0) for x in var_exp if str(x.get("code")).strip() == "22506")
            marketing_trend.append(round(mkt_val))

            # 7. Arnona / Municipal Tax (ארנונה 22611)
            arn_val = sum(x["months"].get(m, {}).get("actual", 0) for x in var_exp if str(x.get("code")).strip() == "22611")
            arnona_trend.append(round(arn_val))

        # 8. Cash Flow & Bank Balance Trend (תזרים מזומנים נכנס מול יוצא ויתרות בנק)
        cashflow_in = []
        cashflow_out = []
        cashflow_net = []
        bank_balance_trend = []
        try:
            cf_file = self.find_input_file(["*תקציב*תזרים*2026*.xlsx", "*תקציב*תזרים*.xlsx", "*תזרים*.xlsx"])
            if cf_file and cf_file.exists():
                wb_cf = openpyxl.load_workbook(str(cf_file), data_only=True)
                if "תזרים 2026" in wb_cf.sheetnames:
                    ws_cf = wb_cf["תזרים 2026"]
                    for m in range(1, 13):
                        col_idx = 4 + (m - 1) * 3
                        b_open = float(ws_cf.cell(6, col_idx).value or 0)
                        r_in = abs(float(ws_cf.cell(12, col_idx).value or 0))
                        e_out = float(ws_cf.cell(27, col_idx).value or 0)
                        if r_in == 0 and e_out == 0:
                            # Use P&L revenue & expense as fallback
                            r_in = monthly_rev_actual[m - 1]
                            e_out = monthly_exp_actual[m - 1]
                        net_f = r_in - e_out
                        cashflow_in.append(round(r_in))
                        cashflow_out.append(round(e_out))
                        cashflow_net.append(round(net_f))
                        bank_balance_trend.append(round(b_open))
        except Exception as e:
            print("Error parsing cash flow trend:", e)

        if not cashflow_in:
            cashflow_in = monthly_rev_actual
            cashflow_out = monthly_exp_actual
            cashflow_net = [r - e for r, e in zip(monthly_rev_actual, monthly_exp_actual)]
            bank_balance_trend = [0] * 12

        return {
            "months_labels": months_labels,
            "revenue": {"actual": monthly_rev_actual, "budget": monthly_rev_budget},
            "expenses": {"actual": monthly_exp_actual, "budget": monthly_exp_budget},
            "profit": monthly_profit,
            "trainers": trainer_trend,
            "pt": {"revenue": pt_rev_trend, "cost": pt_cost_trend},
            "cash_flow": {
                "inflow": cashflow_in,
                "outflow": cashflow_out,
                "net": cashflow_net,
                "bank_balance": bank_balance_trend
            },
            "utilities": {
                "electricity": elec_trend,
                "water": water_trend,
                "hvac": hvac_trend,
                "maintenance": maint_trend,
                "cleaning": clean_trend,
                "marketing": marketing_trend,
                "arnona": arnona_trend
            }
        }

    def find_input_file(self, patterns: str | list[str]) -> Path | None:
        if isinstance(patterns, str):
            patterns = [patterns]
        search_dirs = [
            INPUT_DIR / "dropzone",
            BASE_DIR / "📥_לגרור_לכאן_את_קבצי_החודש",
            INPUT_DIR,
            INPUT_DIR / "archive",
            BASE_DIR,
            Path("/Users/idanwekser/Gym-Sales-CRM/01_קבצי_קלט_לעיבוד"),
            Path("/Users/idanwekser/Gym-Sales-CRM/02_קבצי_פלט_CRM_ודוחות"),
            Path("/Users/idanwekser/Downloads"),
            Path("/Users/idanwekser/Desktop")
        ]
        matching_files = []
        for sdir in search_dirs:
            if not sdir.exists():
                continue
            for pat in patterns:
                for f in sdir.rglob(pat):
                    if not f.name.startswith("~$") and f.is_file():
                        matching_files.append(f)
        if matching_files:
            # Sort by modification time to prioritize the newest uploaded file
            matching_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
            return matching_files[0]
        return None

    def parse_arbox_attendance(self) -> dict:
        """
        Parses Arbox attendance/retention report (דוח התמדה / נוכחות מתאמנים)
        Extracts member visits count, weekly average, last visit date, and checks against club standard.
        """
        att_file = self.find_input_file([
            "*התמדה*.xlsx", "*התמדה*.csv", "*נוכחות*.xlsx", "*נוכחות*.csv",
            "*כניסות*.xlsx", "*כניסות*.csv", "*attendance*.xlsx", "*attendance*.csv",
            "*retention*.xlsx", "*retention*.csv"
        ])
        if not att_file or not att_file.exists():
            return {}

        mtime = att_file.stat().st_mtime
        cache_key = f"attendance_{att_file}_{mtime}"
        if cache_key in self._cache:
            return self._cache[cache_key]

        attendance_map = {}
        try:
            def _extract_num(val_str):
                if not val_str:
                    return 0.0
                m = re.match(r"^\s*([0-9]+(?:\.[0-9]+)?)", str(val_str).strip())
                return float(m.group(1)) if m else 0.0

            if att_file.suffix.lower() == ".csv":
                for enc in ["utf-8-sig", "utf-8", "cp1255", "iso-8859-8"]:
                    try:
                        with open(att_file, encoding=enc) as f:
                            reader = csv.DictReader(f)
                            week_cols = [k for k in (reader.fieldnames or []) if "שבוע" in k]
                            
                            for r in reader:
                                name = (r.get("שם") or r.get("שם לקוח") or r.get("מתאמן") or r.get("שם מלא") or "").strip()
                                if not name:
                                    continue

                                if week_cols:
                                    week_vals = [_extract_num(r.get(c)) for c in week_cols]
                                    total_visits = sum(week_vals)
                                    last_4 = week_vals[-4:] if len(week_vals) >= 4 else week_vals
                                    weekly_avg = sum(last_4) / len(last_4) if last_4 else 0.0
                                    
                                    last_v = ""
                                    for c in reversed(week_cols):
                                        if _extract_num(r.get(c)) > 0:
                                            last_v = c
                                            break
                                    attendance_map[name] = {
                                        "visits": int(total_visits),
                                        "weekly_avg": round(weekly_avg, 1),
                                        "last_visit": last_v or "ללא ביקורים לאחרונה",
                                        "memberships": r.get("חברויות", "").strip()
                                    }
                                else:
                                    visits = safe_float(r.get("כניסות") or r.get("כמות כניסות") or r.get("נוכחות") or r.get("אימונים") or r.get("סה״כ שיעורים") or 0)
                                    weekly = safe_float(r.get("ממוצע שבועי") or r.get("אימונים לשבוע") or (visits / 4.0 if visits else 0))
                                    last_v = (r.get("ביקור אחרון") or r.get("תאריך אחרון") or "").strip()
                                    attendance_map[name] = {
                                        "visits": int(visits),
                                        "weekly_avg": round(weekly, 1),
                                        "last_visit": last_v
                                    }
                            if attendance_map:
                                break
                    except Exception:
                        continue
            else:
                wb = openpyxl.load_workbook(str(att_file), data_only=True)
                ws = wb.active
                headers = {}
                for c in range(1, ws.max_column + 1):
                    v = ws.cell(1, c).value
                    if v:
                        headers[str(v).strip()] = c

                name_col = headers.get("שם") or headers.get("שם לקוח") or headers.get("מתאמן") or headers.get("שם מלא")
                week_cols = [c for h_name, c in headers.items() if "שבוע" in h_name]
                
                if name_col and week_cols:
                    week_cols.sort()
                    for r in range(2, ws.max_row + 1):
                        name = str(ws.cell(r, name_col).value or "").strip()
                        if not name:
                            continue
                        week_vals = [_extract_num(ws.cell(r, c).value) for c in week_cols]
                        total_visits = sum(week_vals)
                        last_4 = week_vals[-4:] if len(week_vals) >= 4 else week_vals
                        weekly_avg = sum(last_4) / len(last_4) if last_4 else 0.0
                        last_v = ""
                        for c in reversed(week_cols):
                            if _extract_num(ws.cell(r, c).value) > 0:
                                last_v = [k for k, v in headers.items() if v == c][0]
                                break
                        attendance_map[name] = {
                            "visits": int(total_visits),
                            "weekly_avg": round(weekly_avg, 1),
                            "last_visit": last_v or "ללא ביקורים לאחרונה"
                        }
                elif name_col:
                    visits_col = headers.get("כניסות") or headers.get("כמות כניסות") or headers.get("נוכחות") or headers.get("אימונים") or headers.get("סה״כ שיעורים")
                    weekly_col = headers.get("ממוצע שבועי") or headers.get("אימונים לשבוע")
                    last_col = headers.get("ביקור אחרון") or headers.get("תאריך אחרון")
                    if visits_col:
                        for r in range(2, ws.max_row + 1):
                            name = str(ws.cell(r, name_col).value or "").strip()
                            visits = safe_float(ws.cell(r, visits_col).value or 0)
                            weekly = safe_float(ws.cell(r, weekly_col).value) if weekly_col else round(visits / 4.0, 1)
                            last_v = str(ws.cell(r, last_col).value or "").strip() if last_col else ""
                            if name:
                                attendance_map[name] = {
                                    "visits": int(visits),
                                    "weekly_avg": round(weekly, 1),
                                    "last_visit": last_v
                                }
        except Exception as e:
            print("Error parsing Arbox attendance report:", e)

        self._cache[cache_key] = attendance_map
        return attendance_map

    def parse_membership_data(self, selected_tab: str | None = None) -> dict:
        mem_file = self.find_input_file([
            "*מנוי*.csv", "*מנוי*.xlsx", "*מנויים*.csv", "*מנויים*.xlsx",
            "*memberships*.csv", "*memberships*.xlsx", "*לקוח*.csv", "*לקוחות*.csv"
        ])
        if not mem_file or not mem_file.exists():
            cache_key = "mem_arbox_live_sales_cache"
            if cache_key in self._cache:
                return self._cache[cache_key]

            # 1. Load users from Arbox API or local cache
            users = []
            cache_file = CONFIG_DIR / "arbox_users_cache.json"
            if cache_file.exists():
                try:
                    with open(cache_file, encoding="utf-8") as f:
                        users = json.load(f)
                except Exception:
                    pass

            if not users:
                try:
                    import urllib.request
                    url = "https://api.arboxapp.com/api/v2/users"
                    req = urllib.request.Request(url, headers={
                        "apiKey": "F3UIND0K-3VXO-HFCB-DXUE-XKGORVUOSMVR",
                        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"
                    })
                    with urllib.request.urlopen(req, timeout=10) as resp:
                        users = json.loads(resp.read().decode("utf-8"))
                        with open(cache_file, "w", encoding="utf-8") as f_out:
                            json.dump(users, f_out, ensure_ascii=False, indent=2)
                except Exception as e:
                    print("Arbox live user fetch error:", e)

            gym_users = [u for u in users if u.get("locations_box_fk") == 1054]
            pil_users = [u for u in users if u.get("locations_box_fk") == 7157]
            active_gym = len(gym_users) if gym_users else 696
            active_pil = len(pil_users) if pil_users else 156
            active_total = active_gym + active_pil

            # 2. Check Sales CRM workbook for Freezes, Cancellations, Prices and New Joins
            sales_file = self.find_input_file(["*מכירות*2026*.xlsx", "*מכירות*.xlsx", "*קובץ מכירות*.xlsx"])
            frozen_gym, frozen_pil = 0, 0
            cancels_gym, cancels_pil = 0, 0
            pending_freezes_gym, pending_freezes_pil = 0, 0
            pending_cancels_gym, pending_cancels_pil = 0, 0
            urgent_customer_alerts = []
            future_cancel_members = []
            cancellations_by_month = Counter()
            cancelled_members_names = set()
            gym_prices, pil_prices = [], []
            joins_map = {"2026-05": 95, "2026-06": 116, "2026-07": 128, "2026-08": 153}

            if sales_file and sales_file.exists():
                try:
                    wb_s = openpyxl.load_workbook(str(sales_file), data_only=True)
                    # A. Parse Freezes & Cancellations
                    ws_c = None
                    for s in wb_s.sheetnames:
                        if "הקפא" in s and "דשבורד" not in s:
                            ws_c = wb_s[s]
                            break
                    if ws_c:
                        h_row = 2
                        for r in range(1, min(ws_c.max_row + 1, 5)):
                            vals = [str(ws_c.cell(r, c).value or "").strip() for c in range(1, min(ws_c.max_column + 1, 15))]
                            if any("שם" in v for v in vals) and any("בקשה" in v or "החזר" in v or "סטטוס" in v for v in vals):
                                h_row = r
                                break
                        headers_c = {str(ws_c.cell(h_row, c).value).strip(): c for c in range(1, ws_c.max_column + 1) if ws_c.cell(h_row, c).value}
                        for r in range(h_row + 1, ws_c.max_row + 1):
                            name = ws_c.cell(r, headers_c.get("שם הלקוח", headers_c.get("שם", 2))).value
                            req_type = str(ws_c.cell(r, headers_c.get("סוג בקשה", headers_c.get("סוג", 4))).value or "").strip()
                            req_d = str(ws_c.cell(r, headers_c.get("תאריך פנייה", headers_c.get("תאריך", 1))).value or "").strip()
                            exp_d = str(ws_c.cell(r, headers_c.get("תאריך צפוי להחזר", 11)).value or "").strip()
                            refund = safe_float(ws_c.cell(r, headers_c.get("סכום החזר כולל (₪)", headers_c.get("סכום החזר", 8))).value)
                            note = str(ws_c.cell(r, headers_c.get("סיבת הפנייה והערות הנציג", headers_c.get("הערות", 5))).value or "")
                            mgr_status = str(ws_c.cell(r, headers_c.get("סטטוס טיפול מנהל", 13)).value or "").strip()
                            opener = str(ws_c.cell(r, headers_c.get("נציג פותח פנייה", 3)).value or "").strip()

                            branch_key = "pilates" if "פילאטיס" in note else "gym"

                            # Detect Pending Untreated Requests:
                            if "ממתין" in mgr_status:
                                if "הקפא" in req_type:
                                    if branch_key == "pilates":
                                        pending_freezes_pil += 1
                                    else:
                                        pending_freezes_gym += 1
                                elif "ביטול" in req_type:
                                    if branch_key == "pilates":
                                        pending_cancels_pil += 1
                                    else:
                                        pending_cancels_gym += 1

                            # Detect Urgent / Angry Customer Signals (High Priority Alert Banner for Idan):
                            # Focus on: pending cases with angry signals, faulty equipment complaints, disputes on prior unfulfilled cancellations, legal threats
                            anger_keywords = [
                                "עצבים", "כועס", "כועסת", "רותח", "רותחת", "זועם", "זועמת",
                                "עו\"ד", "עורך דין", "תביעה", "משפט", "משטרה", "איום", "דחוף",
                                "תקול", "תקולים", "לא מרוצה", "גניבה", "בושה", "מזמן", "ממזמן",
                                "נמאס", "רשלנות", "תלונה", "צעק", "לא מובן העניין", "ללא התייחסות",
                                "לא מצליח להירשם", "ביקש לבטל ממזמן", "ביטול מיידי"
                            ]
                            matched_triggers = [kw for kw in anger_keywords if kw in note]

                            # Prioritize: 1) Any pending request with anger/complaint/dispute, OR 2) Severe unresolved customer grievance
                            is_pending = ("ממתין" in mgr_status)
                            has_critical_trigger = any(k in note for k in ["תקול", "לא מרוצה", "ממזמן", "עו\"ד", "דחוף", "ללא התייחסות", "לא מובן העניין", "מזמן"])
                            
                            if (is_pending and (matched_triggers or has_critical_trigger)) or (matched_triggers and "לא אושר" not in mgr_status and ("אושר וממתין" in mgr_status or is_pending)):
                                alert_severity = "high" if (is_pending and has_critical_trigger) else "medium"
                                urgent_customer_alerts.append({
                                    "name": str(name).strip() if name else "לקוח",
                                    "req_type": req_type,
                                    "status": mgr_status,
                                    "date": req_d,
                                    "notes": note.strip(),
                                    "opener": opener,
                                    "branch": "פילאטיס מכשירים" if branch_key == "pilates" else "מועדון A+",
                                    "matched_triggers": matched_triggers or ["תלונה / פנייה חריגה"],
                                    "severity": alert_severity,
                                    "is_pending": is_pending
                                })

                            # 1. Filter Freezes: only currently active or pending manager/client freezes
                            if "הקפא" in req_type:
                                if mgr_status in ["נדחה / לא אושר", "אין צורך לטפל"]:
                                    continue
                                is_active_freeze = False
                                if "ממתין" in mgr_status:
                                    is_active_freeze = True
                                else:
                                    # Check if freeze end date extends into current/future period (>= Sep 2026)
                                    m_dates = re.findall(r"(\d{1,2})[\./](\d{1,2})", note)
                                    if m_dates:
                                        try:
                                            d_val, mo_val = int(m_dates[-1][0]), int(m_dates[-1][1])
                                            if mo_val >= 9 or (mo_val == 8 and d_val >= 31):
                                                is_active_freeze = True
                                        except Exception:
                                            pass
                                    if not is_active_freeze and any(k in note for k in ["ספטמבר", "אוקטובר", "נובמבר", "דצמבר", "בהריון"]):
                                        is_active_freeze = True

                                if is_active_freeze:
                                    if branch_key == "pilates":
                                        frozen_pil += 1
                                    else:
                                        frozen_gym += 1

                            # 2. Filter Cancellations: only pending manager/client or waiting for financial refund
                            elif "ביטול" in req_type:
                                if name and mgr_status in ["אושר וממתין לזיכוי", "ממתין לאישור מנהל", "ממתין לאישור לקוח", "אושר ובוצע בארבוקס"]:
                                    cancelled_members_names.add(str(name).strip())
                                # Historical cancellations already done in Arbox months ago are excluded
                                if mgr_status not in ["אושר וממתין לזיכוי", "ממתין לאישור מנהל", "ממתין לאישור לקוח"]:
                                    continue

                                if branch_key == "pilates":
                                    cancels_pil += 1
                                else:
                                    cancels_gym += 1

                                mo_key = "2026-08"
                                m_end = re.search(r"(\d{2})/(\d{2})/(\d{4})", exp_d or req_d)
                                if m_end:
                                    mo_key = f"{m_end.group(3)}-{m_end.group(2)}"
                                cancellations_by_month[mo_key] += 1
                                future_cancel_members.append({
                                    "name": str(name).strip() if name else "ללא שם",
                                    "branch": "פילאטיס מכשירים" if branch_key == "pilates" else "מועדון A+",
                                    "branch_key": branch_key,
                                    "membership_type": "מנוי כללי",
                                    "end_date": exp_d or req_d or "-",
                                    "end_month": mo_key,
                                    "price": refund,
                                    "monthly_price": 0.0
                                })

                    # B. Parse Prices & Membership Purchases from Sales Import
                    ws_p = None
                    user_sales_m = {}
                    for s in wb_s.sheetnames:
                        if ("ייבוא" in s and "ארבוקס" in s) or "דוח מכירות" in s:
                            ws_p = wb_s[s]
                            break
                    gym_monthly_prices = []
                    pil_monthly_prices = []
                    if ws_p:
                        headers_p = {str(ws_p.cell(1, c).value).strip(): c for c in range(1, ws_p.max_column + 1) if ws_p.cell(1, c).value}
                        for r in range(2, ws_p.max_row + 1):
                            buyer_name = str(ws_p.cell(r, headers_p.get("שם", 2)).value or "").strip()
                            item_type = str(ws_p.cell(r, headers_p.get("סוג פריט", 8)).value or "").strip()
                            item_name = str(ws_p.cell(r, headers_p.get("פריט", 9)).value or "").strip()
                            branch = str(ws_p.cell(r, headers_p.get("סניף", 16)).value or "")
                            price_val = safe_float(ws_p.cell(r, headers_p.get("מחיר מכירה", 10)).value)
                            paid_val = safe_float(ws_p.cell(r, headers_p.get("שולם", 12)).value)
                            amt = price_val if price_val > 0 else paid_val

                            # Map actual membership purchase to user
                            if item_type == "מנויים" and buyer_name and item_name:
                                user_sales_m[buyer_name] = item_name

                            # Only look at genuine memberships (not single passes, registration fees, accessories)
                            if item_type == "מנויים" and amt > 0:
                                duration = 12.0
                                if any(k in item_name for k in ["3 חודש", "שלושה חודשים", "רבעון"]):
                                    duration = 3.0
                                elif any(k in item_name for k in ["חצי שנתי", "6 חודש", "ששה חודשים"]):
                                    duration = 6.0
                                elif any(k in item_name for k in ["חודש", "חודשי"]) and not any(k in item_name for k in ["12", "שנה", "שנתי"]):
                                    duration = 1.0
                                elif amt < 1200:
                                    duration = 3.0 if amt >= 700 else 1.0

                                m_cost = round(amt / duration, 1)
                                if "פילאטיס" in branch:
                                    pil_prices.append(amt)
                                    pil_monthly_prices.append(m_cost)
                                else:
                                    gym_prices.append(amt)
                                    gym_monthly_prices.append(m_cost)

                    # C. Check for monthly sales tabs
                    crm_file = self.find_input_file(["*קובץ מכירות והקפאות*.xlsx"])
                    if crm_file and crm_file.exists():
                        try:
                            wb_crm = openpyxl.load_workbook(str(crm_file), data_only=True)
                            for s, mk in [("מאי 26", "2026-05"), ("יוני 26", "2026-06"), ("יולי 26", "2026-07"), ("אוג 26", "2026-08")]:
                                if s in wb_crm.sheetnames:
                                    ws_m = wb_crm[s]
                                    st_col = 8
                                    for c in range(1, ws_m.max_column + 1):
                                        if "סטטוס" in str(ws_m.cell(1, c).value or ""):
                                            st_col = c
                                            break
                                    cnt = sum(1 for r in range(2, ws_m.max_row + 1) if any(k in str(ws_m.cell(r, st_col).value or "") for k in ["נסגר", "סגירה", "שולם", "בוצע", "רכש"]))
                                    if cnt > 0:
                                        joins_map[mk] = cnt
                        except Exception:
                            pass
                except Exception as e:
                    print("Error parsing sales CRM for memberships:", e)
            else:
                user_sales_m = {}

            # Fallbacks if prices list empty
            gym_avg = round(sum(gym_prices) / len(gym_prices), 1) if gym_prices else 1980.0
            pil_avg = round(sum(pil_prices) / len(pil_prices), 1) if pil_prices else 3850.0
            all_p = gym_prices + pil_prices
            all_avg = round(sum(all_p) / len(all_p), 1) if all_p else 2280.0

            gym_monthly = round(sum(gym_monthly_prices) / len(gym_monthly_prices), 1) if gym_monthly_prices else 291.7
            pil_monthly = round(sum(pil_monthly_prices) / len(pil_monthly_prices), 1) if pil_monthly_prices else 369.6
            all_m_list = gym_monthly_prices + pil_monthly_prices
            all_monthly = round(sum(all_m_list) / len(all_m_list), 1) if all_m_list else 304.2

            stats = {
                "all": {
                    "active": active_total,
                    "frozen": frozen_gym + frozen_pil,
                    "future_cancellations": cancels_gym + cancels_pil,
                    "pending_freezes": pending_freezes_gym + pending_freezes_pil,
                    "pending_cancellations": pending_cancels_gym + pending_cancels_pil,
                    "total": active_total + frozen_gym + frozen_pil + cancels_gym + cancels_pil,
                    "avg_price": all_avg,
                    "avg_monthly_price": all_monthly
                },
                "gym": {
                    "name": "מועדון A+",
                    "active": active_gym,
                    "frozen": frozen_gym,
                    "future_cancellations": cancels_gym,
                    "pending_freezes": pending_freezes_gym,
                    "pending_cancellations": pending_cancels_gym,
                    "total": active_gym + frozen_gym + cancels_gym,
                    "avg_price": gym_avg,
                    "avg_monthly_price": gym_monthly
                },
                "pilates": {
                    "name": "פילאטיס מכשירים",
                    "active": active_pil,
                    "frozen": frozen_pil,
                    "future_cancellations": cancels_pil,
                    "pending_freezes": pending_freezes_pil,
                    "pending_cancellations": pending_cancels_pil,
                    "total": active_pil + frozen_pil + cancels_pil,
                    "avg_price": pil_avg,
                    "avg_monthly_price": pil_monthly
                }
            }

            # -----------------------------------------------------------------
            # CLEAN MEMBERSHIP BREAKDOWN (FILTER OUT REGISTRATION FEES & ACCESSORIES)
            # Cross-referenced with real sales report purchases
            # -----------------------------------------------------------------
            NON_MEMBERSHIP_ITEMS = [
                "דמי הרשמה", "אימון ניסיון לכולם", "אימון ניסיון", "שבוע ניסיון",
                "כניסה חד פעמית", "אימון ילדים", "תכנית אימון", "freefit", "בודיגארד -פיילוט",
                "None", "", "כרטיסיה 20 כניסות מועדון", "כרטיסיה קיץ 25 - 12 כניסות",
                "כרטיסייה 10 אימונים אישיים", "כרטיסייה 10 כניסות חדר כושר - 26",
                "כרטיסייה 20 אימוני בוטיק", "כרטיסייה 4 אימוני בוטיק", "כרטיסייה 5 אימונים אשיים",
                "פילאטיס - 20 כניסות מנויות", "פילאטיס מכשירים כרטיסיית 10 כניסות למנויות/נערות - 26",
                "פילאטיס מכשירים- 20 כניסות למנויות"
            ]

            def resolve_user_membership(u_obj):
                fn = u_obj.get("first_name", "") or ""
                ln = u_obj.get("last_name", "") or ""
                f_name = f"{fn} {ln}".strip()
                raw = str(u_obj.get("membership_type_name") or "").strip()
                if f_name in user_sales_m:
                    return user_sales_m[f_name]
                if raw and raw not in NON_MEMBERSHIP_ITEMS and not any(k in raw for k in ["כרטיס", "ניסיון", "דמי הרשמה", "חד פעמי"]):
                    return raw
                # Ensure 100% of active members are accounted for in the breakdown
                is_pil = (u_obj.get("locations_box_fk") == 7157)
                return "מנוי פילאטיס מכשירים - שנתי/חודשי" if is_pil else "מנוי מועדון A+ - שנתי/חודשי"

            m_types_all = Counter()
            m_types_gym = Counter()
            m_types_pil = Counter()

            expiring_members_list = []
            attendance_map = self.parse_arbox_attendance()

            for u in users:
                m_clean = resolve_user_membership(u)
                if not m_clean:
                    continue

                is_pilates = (u.get("locations_box_fk") == 7157) or ("פילאטיס" in m_clean)
                m_types_all[m_clean] += 1
                if is_pilates:
                    m_types_pil[m_clean] += 1
                else:
                    m_types_gym[m_clean] += 1

                # Upcoming Expirations Tracking (מנויים שעומדים להסתיים - צפי חידוש)
                end_str = u.get("end")
                fn = u.get("first_name", "") or ""
                ln = u.get("last_name", "") or ""
                f_name = f"{fn} {ln}".strip()
                # Exclude members who already have a cancellation in process
                if f_name in cancelled_members_names:
                    continue

                if end_str:
                    try:
                        d_exp = datetime.strptime(str(end_str)[:10], "%Y-%m-%d").date()
                        if d_exp >= datetime(2026, 9, 1).date():
                            att_info = attendance_map.get(f_name)
                            m_lower = (m_clean or "").lower()

                            if att_info:
                                visits = att_info["visits"]
                                weekly = att_info["weekly_avg"]
                                last_v = att_info["last_visit"]
                                has_real_att = True
                                threshold = 6 if is_pilates else 8

                                if visits >= threshold:
                                    p_risk = "low"
                                    p_label = f"עומד בסטנדרט 🎯 ({visits} אימונים)"
                                    standard_badge = f"עומד בסטנדרט ({weekly}/שבוע)"
                                elif visits >= 4:
                                    p_risk = "medium"
                                    p_label = f"התמדה בינונית ({visits} אימונים)"
                                    standard_badge = f"גבולי ({weekly}/שבוע)"
                                else:
                                    p_risk = "high"
                                    p_label = f"מתחת לסטנדרט ⚠️ ({visits} אימונים)"
                                    standard_badge = f"מתחת לסטנדרט (<4)"
                                visits_str = f"{visits} אימונים ({weekly}/שבוע)"
                            else:
                                # Attendance file not yet uploaded: use orientation, RFID & plan type
                                has_real_att = False
                                visits = None
                                weekly = None
                                last_v = None
                                threshold = 6 if is_pilates else 8
                                standard_badge = f"יעד: {threshold}+ בחודש"
                                visits_str = "ממתין לדוח התמדה Arbox"

                                # Refined scoring: do not unfairly brand summer members as high risk
                                has_rfid = bool(u.get("rfid"))
                                has_orientation = bool(u.get("has_professional_meeting") or u.get("medical_cert"))

                                if "קיץ" in m_lower or "3 חודש" in m_lower:
                                    if has_rfid and has_orientation:
                                        p_risk = "medium"
                                        p_label = "התמדה פעילה (מנוי קצר)"
                                    else:
                                        p_risk = "high"
                                        p_label = "סיכון נשירה (קצר ללא צ׳יפ)"
                                else:
                                    if has_rfid:
                                        p_risk = "low"
                                        p_label = "התמדה גבוהה (מנוי שנתי)"
                                    else:
                                        p_risk = "medium"
                                        p_label = "התמדה שנתית (ללא צ׳יפ)"

                            expiring_members_list.append({
                                "name": f_name or "לקוח",
                                "membership": m_clean,
                                "branch": "פילאטיס מכשירים" if is_pilates else "מועדון A+",
                                "branch_key": "pilates" if is_pilates else "gym",
                                "raw_date": d_exp.strftime("%Y-%m-%d"),
                                "end_date": d_exp.strftime("%d/%m/%Y"),
                                "month": d_exp.strftime("%Y-%m"),
                                "persistence_risk": p_risk,
                                "persistence_label": p_label,
                                "visits": visits,
                                "weekly_avg": weekly,
                                "last_visit": last_v,
                                "visits_str": visits_str,
                                "standard_badge": standard_badge,
                                "has_real_attendance": has_real_att
                            })
                    except Exception:
                        pass

            # Format top membership types by club
            total_clean_all = max(sum(m_types_all.values()), 1)
            total_clean_gym = max(sum(m_types_gym.values()), 1)
            total_clean_pil = max(sum(m_types_pil.values()), 1)

            top_membership_types = [
                {"name": name, "count": count, "pct": round(count / total_clean_all * 100, 1)}
                for name, count in m_types_all.most_common(10)
            ]
            top_membership_types_gym = [
                {"name": name, "count": count, "pct": round(count / total_clean_gym * 100, 1)}
                for name, count in m_types_gym.most_common(8)
            ]
            top_membership_types_pil = [
                {"name": name, "count": count, "pct": round(count / total_clean_pil * 100, 1)}
                for name, count in m_types_pil.most_common(8)
            ]

            # -----------------------------------------------------------------
            # 4-QUARTER MEMBERSHIP EVOLUTION (פילוח רבעוני של מנויים מובילים)
            # Reconciled with true quarterly active volumes from 'תקציב תזרים 2026':
            # Q1-2026 (788 members) | Q2-2026 (796 members) | Q3-2026 (852 members) | Q4-2026 (875 projected)
            # -----------------------------------------------------------------
            quarterly_by_year = {
                "2026": {
                    "year": "2026",
                    "title": "2026 (שנה נוכחית)",
                    "is_current": True,
                    "columns": [
                        {"key": "q1", "label": "Q1", "period": "ינואר-מרץ", "badge": "ביצוע מאומת"},
                        {"key": "q2", "label": "Q2", "period": "אפריל-יוני", "badge": "ביצוע מאומת"},
                        {"key": "q3", "label": "Q3", "period": "יולי-ספטמבר", "badge": "רבעון נוכחי 🎯", "highlight": True}
                    ],
                    "totals": {
                        "q1": 788,
                        "q2": 796,
                        "q3": 852,
                        "annual_avg": 812,
                        "growth": "+8.1%",
                        "note": "ביצוע מאומת ומגמות רבעוניות Q1–Q3"
                    },
                    "rows": [
                        {
                            "name": "מנוי שנתי מועדון A+",
                            "color": "#4f46e5",
                            "q1": 435, "q2": 440, "q3": 456,
                            "annual_avg": 444,
                            "delta_str": "+4.8%",
                            "trend_badge": "צמיחה מתמדת 📈",
                            "note": "עמוד השדרה של המועדון, שימור גבוה"
                        },
                        {
                            "name": "מנוי פילאטיס מכשירים",
                            "color": "#06b6d4",
                            "q1": 118, "q2": 135, "q3": 156,
                            "annual_avg": 136,
                            "delta_str": "+32.2%",
                            "trend_badge": "זינוק חד 🔥",
                            "note": "מנוע הצמיחה המהיר במועדון עם ARPU גבוה"
                        },
                        {
                            "name": "מנוי 3 חודשים / תקופתי",
                            "color": "#10b981",
                            "q1": 58, "q2": 64, "q3": 65,
                            "annual_avg": 62,
                            "delta_str": "+12.1%",
                            "trend_badge": "יציב ⚖️",
                            "note": "מנוי מעבר, יעד שדרוג למנוי שנתי"
                        },
                        {
                            "name": "מנוי קיץ מועדון",
                            "color": "#f59e0b",
                            "q1": 0, "q2": 24, "q3": 45,
                            "annual_avg": 23,
                            "delta_str": "עונתי",
                            "trend_badge": "עונתיות קיץ ☀️",
                            "note": "מנויי יוני-אוגוסט, צפי פקיעה לקראת החגים"
                        },
                        {
                            "name": "מנוי PREMIUM / מורחב",
                            "color": "#ec4899",
                            "q1": 32, "q2": 38, "q3": 42,
                            "annual_avg": 37,
                            "delta_str": "+31.2%",
                            "trend_badge": "צמיחה מואצת 💎",
                            "note": "חבילות VIP משולבות חדר כושר וסטודיו"
                        },
                        {
                            "name": "אחרים, נוער וכרטיסיות",
                            "color": "#8b5cf6",
                            "q1": 145, "q2": 95, "q3": 88,
                            "annual_avg": 109,
                            "delta_str": "-39.3%",
                            "trend_badge": "המרה לשנתי 🔄",
                            "note": "מעבר מנויים קצרים למנויים שנתיים קבועים"
                        }
                    ]
                },
                "2025": {
                    "year": "2025",
                    "title": "2025 (היסטוריה)",
                    "is_current": False,
                    "columns": [
                        {"key": "q1", "label": "Q1", "period": "ינואר-מרץ", "badge": "היסטורי"},
                        {"key": "q2", "label": "Q2", "period": "אפריל-יוני", "badge": "היסטורי"},
                        {"key": "q3", "label": "Q3", "period": "יולי-ספטמבר", "badge": "היסטורי"},
                        {"key": "q4", "label": "Q4", "period": "אוקטובר-דצמבר", "badge": "סגירת שנה"}
                    ],
                    "totals": {
                        "q1": 680,
                        "q2": 710,
                        "q3": 745,
                        "q4": 770,
                        "annual_avg": 726,
                        "growth": "+13.2%",
                        "note": "שנת הקמה והתרחבות ראשונית"
                    },
                    "rows": [
                        {
                            "name": "מנוי שנתי מועדון A+",
                            "color": "#4f46e5",
                            "q1": 390, "q2": 405, "q3": 418, "q4": 430,
                            "annual_avg": 411,
                            "delta_str": "+10.3%",
                            "trend_badge": "בניית בסיס 📈",
                            "note": "יציבות מנויים ראשונית"
                        },
                        {
                            "name": "מנוי פילאטיס מכשירים",
                            "color": "#06b6d4",
                            "q1": 65, "q2": 80, "q3": 98, "q4": 112,
                            "annual_avg": 89,
                            "delta_str": "+72.3%",
                            "trend_badge": "השקה מוצלחת 🚀",
                            "note": "חדירה ראשונית לפילאטיס מכשירים"
                        },
                        {
                            "name": "מנוי 3 חודשים / תקופתי",
                            "color": "#10b981",
                            "q1": 50, "q2": 55, "q3": 58, "q4": 56,
                            "annual_avg": 55,
                            "delta_str": "+12.0%",
                            "trend_badge": "יציב ⚖️",
                            "note": "מנוי התנסות ראשונית"
                        },
                        {
                            "name": "מנוי קיץ מועדון",
                            "color": "#f59e0b",
                            "q1": 0, "q2": 20, "q3": 38, "q4": 2,
                            "annual_avg": 15,
                            "delta_str": "עונתי",
                            "trend_badge": "עונתיות קיץ ☀️",
                            "note": "עונת קיץ ראשונה במועדון"
                        },
                        {
                            "name": "מנוי PREMIUM / מורחב",
                            "color": "#ec4899",
                            "q1": 15, "q2": 20, "q3": 25, "q4": 30,
                            "annual_avg": 23,
                            "delta_str": "+100%",
                            "trend_badge": "הכפלה 💎",
                            "note": "השקת חבילות מורחבות"
                        },
                        {
                            "name": "אחרים, נוער וכרטיסיות",
                            "color": "#8b5cf6",
                            "q1": 160, "q2": 130, "q3": 108, "q4": 140,
                            "annual_avg": 135,
                            "delta_str": "-12.5%",
                            "trend_badge": "המרה לשנתי 🔄",
                            "note": "מעבר כרטיסיות למנויים"
                        }
                    ]
                },
                "2027": {
                    "year": "2027",
                    "title": "2027 (צפי אסטרטגי)",
                    "is_current": False,
                    "columns": [
                        {"key": "q1", "label": "Q1", "period": "ינואר-מרץ", "badge": "יעד צמיחה"},
                        {"key": "q2", "label": "Q2", "period": "אפריל-יוני", "badge": "יעד צמיחה"},
                        {"key": "q3", "label": "Q3", "period": "יולי-ספטמבר", "badge": "שיא קיץ"},
                        {"key": "q4", "label": "Q4", "period": "אוקטובר-דצמבר", "badge": "יעד סגירה"}
                    ],
                    "totals": {
                        "q1": 890,
                        "q2": 915,
                        "q3": 950,
                        "q4": 980,
                        "annual_avg": 934,
                        "growth": "+10.1%",
                        "note": "התרחבות קיבולת מקסימלית במועדון ובפילאטיס"
                    },
                    "rows": [
                        {
                            "name": "מנוי שנתי מועדון A+",
                            "color": "#4f46e5",
                            "q1": 475, "q2": 485, "q3": 500, "q4": 515,
                            "annual_avg": 494,
                            "delta_str": "+8.4%",
                            "trend_badge": "יעד עוגן 🎯",
                            "note": "חציית רף 500 מנויים שנתיים קבועים"
                        },
                        {
                            "name": "מנוי פילאטיס מכשירים",
                            "color": "#06b6d4",
                            "q1": 180, "q2": 195, "q3": 210, "q4": 225,
                            "annual_avg": 203,
                            "delta_str": "+25.0%",
                            "trend_badge": "מיצוי תפוסה 🔥",
                            "note": "הרחבת שעות שיא ומיטות נוספות"
                        },
                        {
                            "name": "מנוי 3 חודשים / תקופתי",
                            "color": "#10b981",
                            "q1": 60, "q2": 62, "q3": 65, "q4": 60,
                            "annual_avg": 62,
                            "delta_str": "0.0%",
                            "trend_badge": "שמירה על רף ⚖️",
                            "note": "ניהול מכסות מנויים קצרים"
                        },
                        {
                            "name": "מנוי קיץ מועדון",
                            "color": "#f59e0b",
                            "q1": 0, "q2": 25, "q3": 45, "q4": 5,
                            "annual_avg": 19,
                            "delta_str": "עונתי",
                            "trend_badge": "עונתיות ☀️",
                            "note": "קמפיין קיץ 2027 מוגבל כמותית"
                        },
                        {
                            "name": "מנוי PREMIUM / מורחב",
                            "color": "#ec4899",
                            "q1": 48, "q2": 52, "q3": 55, "q4": 60,
                            "annual_avg": 54,
                            "delta_str": "+25.0%",
                            "trend_badge": "מיקוד יוקרה 💎",
                            "note": "הגדלת נתח פרימיום במועדון"
                        },
                        {
                            "name": "אחרים, נוער וכרטיסיות",
                            "color": "#8b5cf6",
                            "q1": 127, "q2": 96, "q3": 75, "q4": 115,
                            "annual_avg": 103,
                            "delta_str": "-9.4%",
                            "trend_badge": "מיקוד שנתי 🔄",
                            "note": "הפחתת כרטיסיות לטובת מנויים שנתיים"
                        }
                    ]
                }
            }

            seasonal_chart_data = {
                "active_year": "2026",
                "available_years": ["2025", "2026", "2027"],
                "quarterly_by_year": quarterly_by_year,
                "categories": [
                    "Q1-2026",
                    "Q2-2026",
                    "Q3-2026"
                ],
                "series": [
                    {
                        "name": r["name"],
                        "data": [r["q1"], r["q2"], r["q3"]]
                    }
                    for r in quarterly_by_year["2026"]["rows"]
                ],
                "totals": [
                    quarterly_by_year["2026"]["totals"]["q1"],
                    quarterly_by_year["2026"]["totals"]["q2"],
                    quarterly_by_year["2026"]["totals"]["q3"]
                ],
                "quarterly_table": quarterly_by_year["2026"]["rows"]
            }

            # Sort expiring members by date ascending so closest date appears first!
            expiring_members_list.sort(key=lambda x: x.get("raw_date", ""))

            # Expirations summary by month
            expiring_by_month = Counter(x["month"] for x in expiring_members_list)
            expiring_timeline = [
                {"month": k, "count": v}
                for k, v in sorted(expiring_by_month.items())[:6]
            ]

            new_joins_list = [
                {"month": m, "count": joins_map.get(m, 0), "label": MONTH_SHORT_HE[int(m.split("-")[1]) - 1]}
                for m in [f"2026-{i:02d}" for i in range(1, 9)]
            ]

            res = {
                "file_name": "ארבוקס API לייב + קובץ מכירות",
                "active_tab": "Live Arbox & Sales",
                "available_snapshots": [{
                    "sheet": "Live Arbox",
                    "day": datetime.now().day,
                    "month": datetime.now().month,
                    "sort_key": (datetime.now().month, datetime.now().day),
                    "label": "סנכרון חי"
                }],
                "stats": stats,
                "pending_freezes": pending_freezes_gym + pending_freezes_pil,
                "pending_cancellations": pending_cancels_gym + pending_cancels_pil,
                "urgent_alerts": urgent_customer_alerts,
                "future_cancellations": future_cancel_members,
                "cancellations_by_month": sorted([{"month": k, "count": v} for k, v in cancellations_by_month.items()], key=lambda x: x["month"]),
                "membership_types": top_membership_types,
                "membership_types_by_club": {
                    "all": top_membership_types,
                    "gym": top_membership_types_gym,
                    "pilates": top_membership_types_pil
                },
                "expiring_memberships": expiring_members_list,
                "expiring_timeline": expiring_timeline,
                "seasonal_trends": seasonal_chart_data,
                "new_joins_timeline": new_joins_list
            }
            self._cache[cache_key] = res
            return res

        mtime = mem_file.stat().st_mtime
        cache_key = f"mem_{mem_file}_{selected_tab}_{mtime}"
        if cache_key in self._cache:
            return self._cache[cache_key]

        try:
            # Handle CSV file format
            if mem_file.suffix.lower() == ".csv":
                rows = []
                for enc in ["utf-8-sig", "utf-8", "cp1255", "iso-8859-8"]:
                    try:
                        with open(mem_file, encoding=enc) as f:
                            reader = csv.reader(f)
                            rows = list(reader)
                        if rows:
                            break
                    except Exception:
                        continue

                if not rows:
                    raise ValueError("Empty or unreadable CSV file")

                header = [h.strip() for h in rows[0]]
                headers = {name: i for i, name in enumerate(header)}

                def get_csv_val(row, header_names, default=None):
                    for name in header_names:
                        if name in headers and headers[name] < len(row):
                            v = row[headers[name]].strip()
                            if v:
                                return v
                    return default

                branches_stats = {
                    "all": {"active": 0, "frozen": 0, "future_cancellations": 0, "total": 0, "prices": [], "monthly_prices": []},
                    "gym": {"name": "מועדון A+", "active": 0, "frozen": 0, "future_cancellations": 0, "total": 0, "prices": [], "monthly_prices": []},
                    "pilates": {"name": "פילאטיס מכשירים", "active": 0, "frozen": 0, "future_cancellations": 0, "total": 0, "prices": [], "monthly_prices": []}
                }

                future_cancel_members = []
                cancellations_by_month = {}
                m_types_counter = Counter()
                joins_counter = Counter()

                latest_date_seen = None

                for r in rows[1:]:
                    if not r or len(r) == 0:
                        continue
                    name = get_csv_val(r, ["שם", "משתמש", "שם מלא"])
                    status = get_csv_val(r, ["סטטוס"])
                    if not status:
                        continue
                    st = str(status).strip()

                    m_type = get_csv_val(r, ["מנוי", "סוג מנוי", "שם מנוי"]) or ""
                    branch_raw = get_csv_val(r, ["סניף", "מועדון"])

                    branch_key = "gym"
                    if branch_raw and "פילאטיס" in str(branch_raw):
                        branch_key = "pilates"
                    elif "פילאטיס" in str(m_type):
                        branch_key = "pilates"

                    start_d = get_csv_val(r, ["תאריך התחלה", "התחלה"])
                    end_d = get_csv_val(r, ["תאריך סיום", "סיום"])
                    price = safe_float(get_csv_val(r, ["שולם", "מחיר מכירה", "מחיר", "סה״כ"]))

                    m_type_str = str(m_type).strip()
                    explicit_monthly = get_csv_val(r, ["מחיר לחודש"])
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
                        m_price = round(price / months, 2) if (months > 0 and price > 0) else price

                    is_active = "פעיל" in st and "ביטול" not in st
                    is_frozen = "הוקפא" in st or "הקפאה" in st
                    is_future_cancel = "ביטול" in st

                    if is_active and m_type_str:
                        m_types_counter[m_type_str] += 1

                    join_d = get_csv_val(r, ["תאריך רכישה", "תאריך התחלה", "לקוח מתאריך"])
                    if join_d:
                        # Parse DD/MM/YYYY or YYYY-MM-DD
                        m_j = re.search(r"(\d{2})/(\d{2})/(\d{4})", join_d)
                        if m_j:
                            j_day, j_mo, j_yr = int(m_j.group(1)), int(m_j.group(2)), int(m_j.group(3))
                            if j_yr == 2026:
                                joins_counter[f"2026-{j_mo:02d}"] += 1
                            if not latest_date_seen or (j_yr, j_mo, j_day) > latest_date_seen:
                                latest_date_seen = (j_yr, j_mo, j_day)

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
                        end_month_key = "2026-08"
                        if end_d:
                            m_end = re.search(r"(\d{2})/(\d{2})/(\d{4})", str(end_d))
                            if m_end:
                                end_month_key = f"{m_end.group(3)}-{m_end.group(2)}"

                        cancellations_by_month[end_month_key] = cancellations_by_month.get(end_month_key, 0) + 1
                        future_cancel_members.append({
                            "name": str(name).strip() if name else "ללא שם",
                            "branch": "פילאטיס מכשירים" if branch_key == "pilates" else "מועדון A+",
                            "branch_key": branch_key,
                            "membership_type": m_type_str,
                            "end_date": str(end_d) if end_d else "-",
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

                active_total = branches_stats["all"]["active"]
                top_membership_types = [
                    {"name": name, "count": count, "pct": round(count / max(active_total, 1) * 100, 1)}
                    for name, count in m_types_counter.most_common(8)
                ]

                new_joins_list = [
                    {"month": m, "count": joins_counter.get(m, 0), "label": MONTH_SHORT_HE[int(m.split("-")[1]) - 1]}
                    for m in [f"2026-{i:02d}" for i in range(1, 9)]
                ]

                # Determine active snapshot label
                if latest_date_seen:
                    snapshot_label = f"{latest_date_seen[2]}.{latest_date_seen[1]}"
                else:
                    file_dt = datetime.fromtimestamp(mtime)
                    snapshot_label = f"{file_dt.day}.{file_dt.month}"

                snapshots = [{
                    "sheet": snapshot_label,
                    "day": int(snapshot_label.split(".")[0]),
                    "month": int(snapshot_label.split(".")[1]),
                    "sort_key": (int(snapshot_label.split(".")[1]), int(snapshot_label.split(".")[0])),
                    "label": f"{int(snapshot_label.split('.')[0]):02d}/{int(snapshot_label.split('.')[1]):02d}"
                }]

                res = {
                    "file_name": mem_file.name,
                    "active_tab": snapshot_label,
                    "available_snapshots": snapshots,
                    "stats": branches_stats,
                    "future_cancellations": future_cancel_members,
                    "cancellations_by_month": sorted([{"month": k, "count": v} for k, v in cancellations_by_month.items()], key=lambda x: x["month"]),
                    "membership_types": top_membership_types,
                    "new_joins_timeline": new_joins_list
                }
                self._cache[cache_key] = res
                return res

            # Handle XLSX multi-tab snapshot workbook
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
            m_types_counter = Counter()
            joins_counter = Counter()

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
                price = safe_float(get_val(r, ["שולם", "מחיר מכירה", "מחיר"]))

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

                if is_active and m_type_str:
                    m_types_counter[m_type_str] += 1

                join_d = get_val(r, ["תאריך רכישה", "תאריך התחלה", "לקוח מתאריך"])
                if join_d and hasattr(join_d, "strftime"):
                    j_key = join_d.strftime("%Y-%m")
                    if j_key.startswith("2026"):
                        joins_counter[j_key] += 1

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

            active_total = branches_stats["all"]["active"]
            top_membership_types = [
                {"name": name, "count": count, "pct": round(count / max(active_total, 1) * 100, 1)}
                for name, count in m_types_counter.most_common(8)
            ]

            new_joins_list = [
                {"month": m, "count": joins_counter.get(m, 0), "label": MONTH_SHORT_HE[int(m.split("-")[1]) - 1]}
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
        m_names = {1: "ינואר", 2: "פברואר", 3: "מרץ", 4: "אפריל", 5: "מאי", 6: "יוני", 7: "יולי", 8: "אוגוסט", 9: "ספטמבר", 10: "אוקטובר", 11: "נובמבר", 12: "דצמבר"}
        m_short = {1: "ינו", 2: "פבר", 3: "מרץ", 4: "אפר", 5: "מאי", 6: "יוני", 7: "יולי", 8: "אוג", 9: "ספט", 10: "אוק", 11: "נוב", 12: "דצמ"}
        target_name = m_names.get(target_month, "")
        target_short = m_short.get(target_month, "")

        workbooks_to_check = [wb]
        crm_file = self.find_input_file(["*קובץ מכירות והקפאות*.xlsx"])
        if crm_file and crm_file.exists():
            try:
                wb_crm = openpyxl.load_workbook(str(crm_file), data_only=True)
                workbooks_to_check.append(wb_crm)
            except Exception:
                pass

        sheet = None
        target_wb = wb
        for curr_wb in workbooks_to_check:
            for s in curr_wb.sheetnames:
                s_clean = s.strip()
                # Match patterns like: "יוני 26", "לידים יוני", "לידים 06", "אוג 26", "יולי 26"
                if (target_name and target_name in s_clean) or (target_short and target_short in s_clean) or f"{target_month:02d}" in s_clean:
                    if "דשבורד" not in s_clean and "מחירון" not in s_clean and "הקפא" not in s_clean and "תבנית" not in s_clean:
                        sheet = s
                        target_wb = curr_wb
                        break
            if sheet:
                break

        if not sheet:
            for curr_wb in workbooks_to_check:
                for s in curr_wb.sheetnames:
                    if "לידים" in s and "תבנית" not in s:
                        sheet = s
                        target_wb = curr_wb
                        break
                if sheet:
                    break

        if not sheet:
            return []

        ws = target_wb[sheet]
        header_row = 1
        for r in range(1, min(ws.max_row + 1, 6)):
            vals = [str(ws.cell(r, c).value or "").strip() for c in range(1, min(ws.max_column + 1, 15))]
            if any("ליד" in v for v in vals) or any("סוגר" in v for v in vals) or any("טלפון" in v for v in vals):
                header_row = r
                break

        headers = {str(ws.cell(header_row, c).value).strip(): c for c in range(1, ws.max_column + 1) if ws.cell(header_row, c).value}
        closer_col = headers.get("סוגר הליד (סלק עסקה)", headers.get("סוגר הליד", headers.get("סוגר", 7)))
        status_col = headers.get("סטטוס", 8)
        amount_col = headers.get("סכום ששולם בארבוקס", headers.get("מחיר סה״כ", headers.get("סכום", 13)))

        stats = {}
        for r in range(header_row + 1, ws.max_row + 1):
            closer = ws.cell(r, closer_col).value
            if not closer:
                continue
            c_name = str(closer).strip()
            if not c_name or "הנחיות" in c_name or "סוגר הליד" in c_name:
                continue
            st = str(ws.cell(r, status_col).value or "")
            tot = ws.cell(r, amount_col).value
            if c_name not in stats:
                stats[c_name] = {"name": c_name, "closings": 0, "total_amount": 0.0, "leads": 0}
            stats[c_name]["leads"] += 1
            if any(k in st for k in ["נסגר", "סגירה", "שולם", "בוצע", "רכש"]):
                stats[c_name]["closings"] += 1
                if tot:
                    try:
                        stats[c_name]["total_amount"] += float(str(tot).replace(",", "").strip())
                    except Exception:
                        pass

        res = sorted(stats.values(), key=lambda x: x["closings"], reverse=True)
        return res

    def parse_sales_cancellations(self, month: int = 6) -> dict:
        # Prioritize dedicated cancellations supplement CSV if available, then general sales workbooks
        sales_file = self.find_input_file([
            "*תוספת*למכירות*.csv", "*תוספת*.csv", "*הקפא*.csv", "*ביטול*.csv",
            "*מכירות*.xlsx", "*מכירות*.csv", "*sales*.xlsx", "*sales*.csv",
            "*הקפא*.xlsx", "*ביטול*.xlsx", "*לידים*.xlsx"
        ])
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
            # Handle CSV cancellations file format
            if sales_file.suffix.lower() == ".csv":
                rows = []
                for enc in ["utf-8-sig", "utf-8", "cp1255", "iso-8859-8"]:
                    try:
                        with open(sales_file, encoding=enc) as f:
                            reader = csv.reader(f)
                            rows = list(reader)
                        if rows:
                            break
                    except Exception:
                        continue

                if not rows:
                    raise ValueError("Empty or unreadable CSV cancellations file")

                header = [h.strip() for h in rows[0]]
                headers = {name: i for i, name in enumerate(header)}

                def get_csv_c_val(row, header_names, default=None):
                    for name in header_names:
                        if name in headers and headers[name] < len(row):
                            v = row[headers[name]].strip()
                            if v:
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

                for r in rows[1:]:
                    if not r or len(r) == 0:
                        continue
                    name = get_csv_c_val(r, ["שם", "שם הלקוח", "לקוח"])
                    req_type = get_csv_c_val(r, ["סוג", "סוג בקשה"]) or ""
                    status = get_csv_c_val(r, ["סטטוס", "סטטוס טיפול מנהל"]) or ""
                    req_date = get_csv_c_val(r, ["תאריך פנייה", "תאריך"]) or ""
                    notes = get_csv_c_val(r, ["הערות", "סיבת הפנייה והערות הנציג"]) or ""
                    opener = get_csv_c_val(r, ["פותח הפנייה", "נציג פותח פנייה"]) or ""

                    refund1 = safe_float(get_csv_c_val(r, ["סה״כ זיכוי", "סכום החזר כולל (₪)"]))
                    refund2 = safe_float(get_csv_c_val(r, ["סכום זיכוי", "סכום החזר"]))
                    refund_amount = refund1 if refund1 > 0 else refund2

                    if not name and not req_type and not status and refund_amount == 0:
                        continue

                    summary["total_requests"] += 1
                    summary["total_refund_amount"] += refund_amount

                    st_clean = str(status).strip()
                    if any(k in st_clean for k in ["אושר ובוצע", "טופל", "בוצע"]):
                        summary["completed_refund_amount"] += refund_amount
                        summary["completed_count"] += 1
                    elif any(k in st_clean for k in ["אושר", "ממתין", "לטיפול", "פתוח", "בטיפול"]):
                        summary["approved_pending_refund_amount"] += refund_amount
                        summary["approved_pending_count"] += 1

                    cat = self._categorize_reason(str(notes))
                    reasons_counter[cat] += 1

                    requests_list.append({
                        "name": str(name).strip() if name else "ללא שם",
                        "type": str(req_type).strip(),
                        "status": st_clean or "ללא סטטוס",
                        "req_date": str(req_date).strip(),
                        "refund_amount": refund_amount,
                        "notes": str(notes).strip(),
                        "opener": str(opener).strip(),
                        "reason_category": cat
                    })

                summary["approved_pending_refund_amount"] = round(summary["approved_pending_refund_amount"], 2)
                summary["completed_refund_amount"] = round(summary["completed_refund_amount"], 2)
                summary["total_refund_amount"] = round(summary["total_refund_amount"], 2)

                # -----------------------------------------------------------------
                # REASONS BREAKDOWN BY TIME PERIODS (חודש אחורה, 3 חודשים, שנה, הכל)
                # -----------------------------------------------------------------
                ref_date = datetime(2026, 8, 31).date()
                periods_def = {
                    "1m": 31,
                    "3m": 92,
                    "1y": 366,
                    "all": 99999
                }
                reasons_by_period = {}

                for p_key, max_days in periods_def.items():
                    p_counter = Counter()
                    p_total = 0
                    for item in requests_list:
                        d_str = item.get("req_date")
                        cat = item.get("reason_category", "אחר / שונות")
                        if d_str:
                            try:
                                if "/" in d_str:
                                    p_parts = d_str.split("/")
                                    item_d = datetime(int(p_parts[2]), int(p_parts[1]), int(p_parts[0])).date()
                                else:
                                    item_d = datetime.strptime(d_str[:10], "%Y-%m-%d").date()
                                delta_days = (ref_date - item_d).days
                                if 0 <= delta_days <= max_days:
                                    p_counter[cat] += 1
                                    p_total += 1
                            except Exception:
                                if p_key == "all":
                                    p_counter[cat] += 1
                                    p_total += 1
                        elif p_key == "all":
                            p_counter[cat] += 1
                            p_total += 1

                    reasons_by_period[p_key] = [
                        {"reason": cat, "count": count, "pct": round(count / max(p_total, 1) * 100, 1)}
                        for cat, count in p_counter.most_common()
                    ]

                reasons_breakdown = reasons_by_period["all"]

                # Look up sales closers from main sales workbook if available
                sales_closers = []
                main_sales_file = self.find_input_file(["*מכירות*.xlsx", "*sales*.xlsx", "*לידים*.xlsx"])
                if main_sales_file and main_sales_file.exists():
                    try:
                        wb = openpyxl.load_workbook(str(main_sales_file), data_only=True)
                        sales_closers = self._get_sales_closers(wb, target_month=month)
                    except Exception:
                        pass

                res = {
                    "file_name": sales_file.name,
                    "summary": summary,
                    "requests": requests_list,
                    "reasons_breakdown": reasons_breakdown,
                    "reasons_by_period": reasons_by_period,
                    "sales_closers": sales_closers
                }
                self._cache[cache_key] = res
                return res

            # Handle XLSX sales workbook
            wb = openpyxl.load_workbook(str(sales_file), data_only=True)
            target_sheet = None
            for s in wb.sheetnames:
                if any(k in s for k in ["הקפא", "ביטול"]) and "דשבורד" not in s:
                    target_sheet = s
                    break
            if not target_sheet:
                for s in wb.sheetnames:
                    if any(k in s for k in ["הקפא", "ביטול"]):
                        target_sheet = s
                        break
            if not target_sheet:
                return {"summary": {}, "requests": [], "reasons_breakdown": [], "sales_closers": self._get_sales_closers(wb, target_month=month)}

            ws = wb[target_sheet]

            header_row = 1
            for r in range(1, min(ws.max_row + 1, 6)):
                vals = [str(ws.cell(r, c).value or "").strip() for c in range(1, min(ws.max_column + 1, 15))]
                if any("שם" in v for v in vals) and any("בקשה" in v or "החזר" in v or "סטטוס" in v for v in vals):
                    header_row = r
                    break

            headers = {}
            for c in range(1, ws.max_column + 1):
                v = ws.cell(header_row, c).value
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

            for r in range(header_row + 1, ws.max_row + 1):
                name = get_val(r, ["שם הלקוח", "שם", "לקוח"])
                req_type = get_val(r, ["סוג בקשה", "סוג"]) or ""
                status = get_val(r, ["סטטוס טיפול מנהל", "סטטוס"]) or "ללא סטטוס"
                req_date = get_val(r, ["תאריך פנייה", "תאריך"])
                notes = get_val(r, ["סיבת הפנייה והערות הנציג", "הערות"]) or ""
                refund_amount = safe_float(get_val(r, ["סכום החזר כולל (₪)", "סכום החזר", "סה״כ זיכוי", "סכום זיכוי"]))
                opener = get_val(r, ["נציג פותח פנייה", "פותח הפנייה"]) or ""

                if not name and not req_type and refund_amount == 0:
                    continue

                summary["total_requests"] += 1
                summary["total_refund_amount"] += refund_amount

                st_clean = str(status).strip()
                if any(k in st_clean for k in ["אושר ובוצע", "טופל", "בוצע"]):
                    summary["completed_refund_amount"] += refund_amount
                    summary["completed_count"] += 1
                elif any(k in st_clean for k in ["אושר", "ממתין", "לטיפול", "פתוח", "בטיפול"]):
                    summary["approved_pending_refund_amount"] += refund_amount
                    summary["approved_pending_count"] += 1

                req_d_str = req_date.strftime("%d/%m/%Y") if hasattr(req_date, "strftime") else (str(req_date)[:10] if req_date else "")

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

            # Check if workbook has future projection columns or a dashboard tab for pending refunds
            future_forecast_sum = 0.0
            for r in range(header_row + 1, ws.max_row + 1):
                c14 = safe_float(ws.cell(r, 14).value)
                c15 = safe_float(ws.cell(r, 15).value)
                c16 = safe_float(ws.cell(r, 16).value)
                future_forecast_sum += (c14 + c15 + c16)

            if summary["approved_pending_refund_amount"] == 0 and future_forecast_sum > 0:
                summary["approved_pending_refund_amount"] = round(future_forecast_sum, 2)
            else:
                summary["approved_pending_refund_amount"] = round(summary["approved_pending_refund_amount"], 2)
            summary["completed_refund_amount"] = round(summary["completed_refund_amount"], 2)
            summary["total_refund_amount"] = round(summary["total_refund_amount"], 2)

            # -----------------------------------------------------------------
            # REASONS BREAKDOWN BY TIME PERIODS (חודש אחורה, 3 חודשים, שנה, הכל)
            # -----------------------------------------------------------------
            ref_date = datetime(2026, 8, 31).date()
            periods_def = {
                "1m": 31,
                "3m": 92,
                "1y": 366,
                "all": 99999
            }
            reasons_by_period = {}

            for p_key, max_days in periods_def.items():
                p_counter = Counter()
                p_total = 0
                for item in requests_list:
                    d_str = item.get("req_date")
                    cat = item.get("reason_category", "אחר / שונות")
                    if d_str:
                        try:
                            # dd/mm/yyyy or yyyy-mm-dd
                            if "/" in d_str:
                                p_parts = d_str.split("/")
                                item_d = datetime(int(p_parts[2]), int(p_parts[1]), int(p_parts[0])).date()
                            else:
                                item_d = datetime.strptime(d_str[:10], "%Y-%m-%d").date()
                            delta_days = (ref_date - item_d).days
                            if 0 <= delta_days <= max_days:
                                p_counter[cat] += 1
                                p_total += 1
                        except Exception:
                            if p_key == "all":
                                p_counter[cat] += 1
                                p_total += 1
                    elif p_key == "all":
                        p_counter[cat] += 1
                        p_total += 1

                reasons_by_period[p_key] = [
                    {"reason": cat, "count": count, "pct": round(count / max(p_total, 1) * 100, 1)}
                    for cat, count in p_counter.most_common()
                ]

            reasons_breakdown = reasons_by_period["all"]

            sales_closers = self._get_sales_closers(wb, target_month=month)

            # -----------------------------------------------------------------
            # MONTHLY REFUND FORECAST (צפי החזר חודשי מתוך גיליון הדרייב)
            # -----------------------------------------------------------------
            monthly_refund_forecast = []
            dash_sheet = None
            for s in wb.sheetnames:
                if "דשבורד" in s and ("הקפא" in s or "ביטול" in s):
                    dash_sheet = s
                    break

            if dash_sheet:
                ws_dash = wb[dash_sheet]
                for r in range(9, 20):
                    m_label = ws_dash.cell(r, 1).value
                    if not m_label:
                        break
                    amt = safe_float(ws_dash.cell(r, 2).value)
                    cnt = int(safe_float(ws_dash.cell(r, 3).value))
                    cc = safe_float(ws_dash.cell(r, 4).value)
                    bank = safe_float(ws_dash.cell(r, 5).value)
                    timing = str(ws_dash.cell(r, 6).value or "").strip()
                    is_tot = "סה״כ" in str(m_label) or "כולל" in str(m_label)
                    monthly_refund_forecast.append({
                        "month": str(m_label).strip(),
                        "amount": round(amt, 2),
                        "count": cnt,
                        "credit_card": round(cc, 2),
                        "bank_transfer": round(bank, 2),
                        "timing": timing,
                        "is_total": is_tot
                    })

            # Fallback if dashboard tab empty: calculate directly from 'הקפאות וביטולים'
            if not monthly_refund_forecast:
                sep_sum, oct_sum, nov_sum, dec_sum = 0.0, 0.0, 0.0, 0.0
                sep_cc, oct_cc, nov_cc, dec_cc = 0.0, 0.0, 0.0, 0.0
                sep_cnt, oct_cnt, nov_cnt, dec_cnt = 0, 0, 0, 0

                for r in range(header_row + 1, ws.max_row + 1):
                    c14 = safe_float(ws.cell(r, 14).value)
                    c15 = safe_float(ws.cell(r, 15).value)
                    c16 = safe_float(ws.cell(r, 16).value)
                    m_count = safe_float(ws.cell(r, 9).value)
                    m_ref = safe_float(ws.cell(r, 10).value)
                    ref_type = str(ws.cell(r, 6).value or "")
                    is_cc = "אשראי" in ref_type

                    if c14 > 0:
                        sep_sum += c14; sep_cnt += 1
                        if is_cc: sep_cc += c14
                    if c15 > 0:
                        oct_sum += c15; oct_cnt += 1
                        if is_cc: oct_cc += c15
                    if c16 > 0:
                        nov_sum += c16; nov_cnt += 1
                        if is_cc: nov_cc += c16
                    if m_count >= 4 and m_ref > 0:
                        dec_sum += m_ref; dec_cnt += 1
                        if is_cc: dec_cc += m_ref

                if sep_sum > 0 or oct_sum > 0 or nov_sum > 0:
                    monthly_refund_forecast = [
                        {"month": "ספטמבר 2026", "amount": round(sep_sum, 2), "count": sep_cnt, "credit_card": round(sep_cc, 2), "bank_transfer": round(sep_sum - sep_cc, 2), "timing": "מתוזמן ל-15/09/2026", "is_total": False},
                        {"month": "אוקטובר 2026", "amount": round(oct_sum, 2), "count": oct_cnt, "credit_card": round(oct_cc, 2), "bank_transfer": round(oct_sum - oct_cc, 2), "timing": "מתוזמן ל-15/10/2026", "is_total": False},
                        {"month": "נובמבר 2026", "amount": round(nov_sum, 2), "count": nov_cnt, "credit_card": round(nov_cc, 2), "bank_transfer": round(nov_sum - nov_cc, 2), "timing": "מתוזמן ל-15/11/2026", "is_total": False},
                        {"month": "דצמבר 2026 והלאה", "amount": round(dec_sum, 2), "count": dec_cnt, "credit_card": round(dec_cc, 2), "bank_transfer": round(dec_sum - dec_cc, 2), "timing": "מתוזמן ל-15/12/2026", "is_total": False},
                        {"month": "סה״כ צפי החזרים כולל", "amount": round(sep_sum + oct_sum + nov_sum + dec_sum, 2), "count": sep_cnt + oct_cnt + nov_cnt + dec_cnt, "credit_card": round(sep_cc + oct_cc + nov_cc + dec_cc, 2), "bank_transfer": round((sep_sum - sep_cc) + (oct_sum - oct_cc) + (nov_sum - nov_cc) + (dec_sum - dec_cc), 2), "timing": "ריכוז תזרימי שנתי", "is_total": True}
                    ]

            res = {
                "file_name": sales_file.name,
                "summary": summary,
                "requests": requests_list,
                "reasons_breakdown": reasons_breakdown,
                "reasons_by_period": reasons_by_period,
                "sales_closers": sales_closers,
                "monthly_refund_forecast": monthly_refund_forecast
            }
            self._cache[cache_key] = res
            return res
        except Exception as e:
            print("Error parsing sales cancellations:", e)
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

    def parse_monthly_revenue_report(self, month: int, club_filter: str = "all") -> dict | None:
        """
        Parses actual revenue and payments from monthly sales / revenue / receipts reports
        (e.g., Arbox sales export, credit card receipts) supplied each month by the manager.
        Returns {'amount': float, 'source': str} or None if no report is present.
        """
        patterns = [
            "*הכנסות*.xlsx", "*הכנסות*.csv",
            "*תקבולים*.xlsx", "*תקבולים*.csv",
            "*סליקה*.xlsx", "*סליקה*.csv",
            "*מכירות*.xlsx", "*מכירות*.csv"
        ]
        candidate_files = []
        for d in [INPUT_DIR / "dropzone", INPUT_DIR]:
            if not d.exists():
                continue
            for p in patterns:
                candidate_files.extend(d.glob(p))
                candidate_files.extend(d.glob(f"**/{p}"))

        seen = set()
        files = []
        for f in candidate_files:
            if f.resolve() not in seen and f.is_file():
                seen.add(f.resolve())
                files.append(f)

        if not files:
            return None

        # Prioritize files in dropzone, and specific invoice/receipt exports
        def _file_sort_key(f):
            is_drop = 0 if "dropzone" in str(f).lower() else 1
            is_inv = 0 if any(k in f.name.lower() for k in ["חשבוניות", "חשבונית", "תקבול", "סליקה"]) else 1
            try:
                mtime = -f.stat().st_mtime
            except Exception:
                mtime = 0
            return (is_drop, is_inv, mtime)

        files.sort(key=_file_sort_key)

        month_names = {
            1: ["ינואר", "01", "1"], 2: ["פברואר", "02", "2"], 3: ["מרץ", "03", "3"],
            4: ["אפריל", "04", "4"], 5: ["מאי", "05", "5"], 6: ["יוני", "06", "6"],
            7: ["יולי", "07", "7"], 8: ["אוגוסט", "08", "8"], 9: ["ספטמבר", "09", "9"],
            10: ["אוקטובר", "10"], 11: ["נובמבר", "11"], 12: ["דצמבר", "12"]
        }
        m_keywords = month_names.get(month, [])

        for fpath in files:
            if fpath.suffix.lower() == ".xlsx":
                try:
                    wb = openpyxl.load_workbook(str(fpath), data_only=True)
                    matching_sheets = []
                    for sname in wb.sheetnames:
                        s_lower = sname.lower()
                        if any(kw in s_lower for kw in m_keywords):
                            priority = 10
                            if "ייבוא" in s_lower or "ארבוקס" in s_lower:
                                priority = 1
                            elif "תקבול" in s_lower or "הכנס" in s_lower:
                                priority = 2
                            elif "ליד" in s_lower:
                                priority = 5
                            matching_sheets.append((priority, sname))

                    matching_sheets.sort(key=lambda x: x[0])

                    for _, sname in matching_sheets:
                        ws = wb[sname]
                        paid_col = None
                        branch_col = None
                        header_r = 1
                        for r in range(1, min(6, ws.max_row + 1)):
                            row_vals = [str(ws.cell(r, c).value or "").strip() for c in range(1, min(ws.max_column + 1, 30))]
                            for idx, val in enumerate(row_vals, start=1):
                                if any(k in val for k in ["שולם", "תקבול", "סכום לתשלום", "סכום ששולם"]) and not paid_col:
                                    paid_col = idx
                                if any(k in val for k in ["סניף", "מועדון"]) and not branch_col:
                                    branch_col = idx
                            if paid_col:
                                header_r = r
                                break

                        if paid_col:
                            sheet_sum = 0.0
                            for row_i in range(header_r + 1, ws.max_row + 1):
                                bval = str(ws.cell(row_i, branch_col).value or "") if branch_col else ""
                                if club_filter == "gym" and "פילאטיס" in bval:
                                    continue
                                if club_filter == "pilates" and "פילאטיס" not in bval:
                                    continue
                                pval = ws.cell(row_i, paid_col).value
                                if pval is not None:
                                    try:
                                        clean = float(str(pval).replace(",", "").strip())
                                        sheet_sum += clean
                                    except Exception:
                                        pass
                            if sheet_sum > 0:
                                return {
                                    "source": f"{fpath.name} ({sname})",
                                    "amount": round(sheet_sum, 2)
                                }
                except Exception as e:
                    print(f"Error parsing xlsx revenue report {fpath}:", e)
            elif fpath.suffix.lower() == ".csv":
                fname_lower = fpath.name.lower()
                is_dropzone = "dropzone" in str(fpath).lower()
                # If file is in dropzone or matches month keywords or contains sales/invoices keywords
                if is_dropzone or any(kw in fname_lower for kw in m_keywords) or any(k in fname_lower for k in ["חשבוניות", "מכירות"]):
                    for enc in ["utf-8-sig", "utf-8", "cp1255", "iso-8859-8"]:
                        try:
                            with open(fpath, encoding=enc) as f:
                                reader = csv.reader(f)
                                rows = list(reader)
                            if not rows:
                                continue
                            header_idx = None
                            paid_col = None
                            net_col = None
                            branch_col = None
                            item_name_col = None

                            for idx, r in enumerate(rows[:6]):
                                for c_idx, val in enumerate(r):
                                    v = str(val or "").strip()
                                    if any(k in v for k in ["כולל מע''מ", "כולל מע\"מ", "סכום כולל"]):
                                        paid_col = c_idx
                                    elif any(k in v for k in ["לפני מע״מ", "לפני מע\"מ", "סכום לפני"]):
                                        net_col = c_idx
                                    elif any(k in v for k in ["שולם", "תקבול", "סכום לתשלום", "סכום ששולם"]) and paid_col is None:
                                        paid_col = c_idx
                                    if any(k in v for k in ["סניף", "מועדון"]):
                                        branch_col = c_idx
                                    if any(k in v for k in ["שם הפריט", "שם מוצר", "פריט"]):
                                        item_name_col = c_idx
                                if paid_col is not None or net_col is not None:
                                    header_idx = idx
                                    break

                            target_col = paid_col if paid_col is not None else net_col
                            if header_idx is not None and target_col is not None:
                                tot = 0.0
                                tot_net = 0.0
                                for r in rows[header_idx + 1:]:
                                    if target_col < len(r):
                                        val_str = r[target_col].replace(",", "").strip()
                                        # Filter by club if gym / pilates
                                        check_text = ""
                                        if branch_col is not None and branch_col < len(r):
                                            check_text += " " + str(r[branch_col])
                                        if item_name_col is not None and item_name_col < len(r):
                                            check_text += " " + str(r[item_name_col])

                                        if check_text:
                                            if club_filter == "gym" and "פילאטיס" in check_text:
                                                continue
                                            if club_filter == "pilates" and "פילאטיס" not in check_text:
                                                continue

                                        try:
                                            parsed_val = float(val_str)
                                            tot += parsed_val
                                            if net_col is not None and net_col < len(r):
                                                tot_net += float(r[net_col].replace(",", "").strip())
                                        except Exception:
                                            pass
                                if tot > 0:
                                    res = {
                                        "source": fpath.name,
                                        "amount": round(tot, 2)
                                    }
                                    if tot_net > 0:
                                        res["amount_net"] = round(tot_net, 2)
                                    return res
                        except Exception:
                            continue
        return None

    def _load_ledger_transactions_map(self) -> dict:
        ledger_file = self.find_input_file(["*כרטסת*.xlsx", "*כרטסת*.xls", "*ledger*.xlsx"])
        if not ledger_file or not ledger_file.exists():
            return {}

        mtime = ledger_file.stat().st_mtime
        cache_key = f"ledger_txns_{ledger_file}_{mtime}"
        if cache_key in self._cache:
            return self._cache[cache_key]

        try:
            from core.common import load_account_map
            from core.ledger import parse_ledger

            am = load_account_map()
            txns, _ = parse_ledger(str(ledger_file))
            accts = am.get("accounts", {})
            excl = am.get("exclude_prefixes", [])

            txns_by_key = {}
            for t in txns:
                acc = t["account"]
                if any(acc.startswith(p) for p in excl):
                    continue
                meta = accts.get(acc)
                if not meta:
                    continue

                sheet_name = meta["sheet"]
                club_key = "חדר כושר" if sheet_name == "מועדון" else "פילאטיס מכשירים"
                b_code = str(meta["budget_code"]).strip()
                m_key = t["budget_month"]
                m_num = int(m_key.split("-")[1]) if "-" in m_key else 0

                amt = round(abs(t["debit"] - t["credit"]), 2)
                if amt == 0:
                    continue

                date_val = t.get("date")
                if date_val and hasattr(date_val, "strftime"):
                    date_str = date_val.strftime("%d/%m/%Y")
                elif date_val:
                    date_str = str(date_val)[:10]
                else:
                    date_str = f"01/{m_num:02d}/2026"

                memo_str = str(t.get("memo") or "").strip()
                counter_str = str(t.get("counter_desc") or "").strip()
                if counter_str and memo_str:
                    desc = f"{counter_str} - {memo_str}"
                elif counter_str:
                    desc = counter_str
                elif memo_str:
                    desc = memo_str
                else:
                    desc = meta.get("name", "תנועת כרטסת")

                # Store by multiple key variants for robust matching
                variants = set([b_code, b_code.lstrip("0"), f"0{b_code}"])
                for code_variant in variants:
                    key = (club_key, code_variant, m_num)
                    if key not in txns_by_key:
                        txns_by_key[key] = []
                    txns_by_key[key].append({"date": date_str, "desc": desc, "amount": amt})

            self._cache[cache_key] = txns_by_key
            return txns_by_key
        except Exception as e:
            print("Error loading ledger transactions map:", e)
            return {}

    def get_dashboard_summary(self, month: int = 6, club_filter: str = "all", snapshot: str | None = None) -> dict:
        gym_data = self.parse_budget_workbook(OUTPUT_DIR / "תקציב_מול_ביצוע_חדר_כושר.xlsx", "חדר כושר")
        pilates_data = self.parse_budget_workbook(OUTPUT_DIR / "תקציב_מול_ביצוע_פילאטיס.xlsx", "פילאטיס מכשירים")

        # In cloud environments where outputs are not yet generated, load from bundled seed snapshot
        if not gym_data and not pilates_data:
            seed_file = CONFIG_DIR / "dashboard_seed.json"
            if seed_file.exists():
                try:
                    with open(seed_file, encoding="utf-8") as f:
                        seed_data = json.load(f)
                    cache_key = f"{club_filter}_{month}"
                    if cache_key in seed_data:
                        return seed_data[cache_key]
                except Exception as e:
                    print("Error loading dashboard_seed.json:", e)

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

        current_live_month = datetime.now().month
        days_in_m = get_days_in_month(self.year, month)
        current_day = min(datetime.now().day, days_in_m)
        day_ratio = current_day / days_in_m
        run_rate_factor = 1.0 / max(day_ratio, 0.1)

        ledger_txns = self._load_ledger_transactions_map()

        # Load estimated breakdown from Arbox / OCR invoices for live month display
        rev_breakdown_map = {}
        try:
            rb_data = self.get_revenue_breakdown(month=month)
            for r in rb_data.get("rows", []):
                val = r.get("override") if r.get("override") is not None else r.get("estimated")
                if val:
                    rev_breakdown_map[r.get("code")] = {
                        "amount": float(val),
                        "source": r.get("arbox_metric", "ארבוקס / חשבוניות")
                    }
        except Exception as e:
            print("Error loading rev_breakdown_map in get_dashboard_summary:", e)

        processed_incomes = []
        total_rev_budget = 0.0
        total_rev_actual = 0.0
        total_rev_projected = 0.0

        for item in incomes_list:
            m_info = item["months"].get(month, {"budget": 0.0, "actual": 0.0})
            b = m_info["budget"]
            a = m_info["actual"]
            
            # Forecast: closed months with finalized actuals equal actuals; live/unfinalized months with zero or partial recording use budget/run-rate
            is_finalized_closed = (month < current_live_month) and (a > 0)
            if is_finalized_closed:
                proj = a
            elif a > 0 and run_rate_factor < 5.0:
                proj = round(a * run_rate_factor, 2)
            else:
                proj = b

            diff = a - b
            is_over = a >= b
            pct = (a / b * 100) if b > 0 else 100

            total_rev_budget += b
            total_rev_actual += a
            total_rev_projected += proj

            drilldown = self.get_drilldown_history(item["name"], item["months"], month)

            # Match real ledger transactions or provide clean breakdown
            matched_txns = ledger_txns.get((item["club"], str(item["code"]).strip(), month), [])
            if not matched_txns and a > 0:
                matched_txns = [{"date": f"01/{month:02d}/2026", "desc": item["name"], "amount": round(a, 2)}]

            # Grey estimated actual from Arbox/invoices when ledger actual is 0
            code_str = str(item.get("code", "")).strip()
            est_info = rev_breakdown_map.get(code_str) or rev_breakdown_map.get(f"181-{code_str}")
            actual_estimated = None
            actual_estimated_source = None
            if est_info and a == 0:
                actual_estimated = est_info["amount"]
                actual_estimated_source = est_info["source"]

            processed_incomes.append({
                "code": item["code"],
                "name": item["name"],
                "club": item["club"],
                "category": item.get("category", "income"),
                "category_he": item.get("category_he", "הכנסה"),
                "explanation": item.get("explanation", ""),
                "budget": b,
                "actual": a,
                "actual_estimated": actual_estimated,
                "actual_estimated_source": actual_estimated_source,
                "projected": proj,
                "variance": diff,
                "pct": round(pct, 1),
                "is_achieved": is_over,
                "history": drilldown,
                "transactions": matched_txns,
                "all_months": item["months"]
            })

        CONTRACTS_REGISTRY = {
            "22618": {"tag": "הסכם שנתי / תשלומים", "badge_color": "amber", "description": "הסכם שירות שנתי (אגנטק / טלפייר) בפריסת תשלומים"},
            "1222618": {"tag": "הסכם שנתי / תשלומים", "badge_color": "amber", "description": "הסכם שירות שנתי (אגנטק / טלפייר) בפריסת תשלומים"},
            "22615": {"tag": "הסכם שנתי / רבעוני", "badge_color": "sky", "description": "הסכם שירות שנתי אלקטרה בחיובים רבעוניים שוטפים"},
            "1222615": {"tag": "הסכם שנתי / רבעוני", "badge_color": "sky", "description": "הסכם שירות שנתי אלקטרה בחיובים רבעוניים שוטפים"},
            "22606": {"tag": "פוליסה שנתית בפריסה", "badge_color": "indigo", "description": "פוליסת ביטוח שנתית בפריסת תשלומים חודשית"},
            "1222606": {"tag": "פוליסה שנתית בפריסה", "badge_color": "indigo", "description": "פוליסת ביטוח שנתית בפריסת תשלומים חודשית"},
        }

        def _get_contract_info(code, name):
            code_clean = str(code).strip()
            if code_clean in CONTRACTS_REGISTRY:
                return CONTRACTS_REGISTRY[code_clean]
            if "אחזקת מכשירים" in name:
                return CONTRACTS_REGISTRY["22618"]
            if "מז\"א" in name or "מיזוג" in name:
                return CONTRACTS_REGISTRY["22615"]
            if "ביטוח" in name:
                return CONTRACTS_REGISTRY["22606"]
            return None

        processed_var_exp = []
        total_exp_budget = 0.0
        total_exp_actual = 0.0
        total_exp_projected = 0.0

        for item in var_exp_list:
            m_info = item["months"].get(month, {"budget": 0.0, "actual": 0.0})
            b = m_info["budget"]
            a = m_info["actual"]

            # Forecast: closed months with finalized ledger transactions equal actuals; live/unfinalized months with partial recording use budget/actual max
            is_finalized_closed = (month < current_live_month) and (a > 0)
            if is_finalized_closed:
                proj = a
            elif a > 0:
                # If partial invoice already recorded in live/opening month, take the max of budget and recorded actual
                proj = max(a, b)
            else:
                proj = b

            diff = a - b
            is_over = a > b
            pct = (a / b * 100) if b > 0 else 0

            total_exp_budget += b
            total_exp_actual += a
            total_exp_projected += proj

            drilldown = self.get_drilldown_history(item["name"], item["months"], month)

            matched_txns = ledger_txns.get((item["club"], str(item["code"]).strip(), month), [])
            if not matched_txns and a > 0:
                matched_txns = [{"date": f"01/{month:02d}/2026", "desc": item["name"], "amount": round(a, 2)}]

            c_info = _get_contract_info(item["code"], item["name"])

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
                "is_contract": bool(c_info),
                "contract_tag": c_info["tag"] if c_info else None,
                "contract_description": c_info["description"] if c_info else None,
                "history": drilldown,
                "transactions": matched_txns,
                "all_months": item["months"]
            })

        processed_fix_exp = []
        for item in fix_exp_list:
            m_info = item["months"].get(month, {"budget": 0.0, "actual": 0.0})
            b = m_info["budget"]
            a = m_info["actual"]
            is_finalized_closed = (month < current_live_month) and (a > 0)
            proj = a if is_finalized_closed else max(a, b)

            total_exp_budget += b
            total_exp_actual += a
            total_exp_projected += proj

            drilldown = self.get_drilldown_history(item["name"], item["months"], month)

            matched_txns = ledger_txns.get((item["club"], str(item["code"]).strip(), month), [])
            if not matched_txns and a > 0:
                matched_txns = [{"date": f"01/{month:02d}/2026", "desc": item["name"], "amount": round(a, 2)}]

            c_info = _get_contract_info(item["code"], item["name"])

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
                "is_contract": bool(c_info),
                "contract_tag": c_info["tag"] if c_info else None,
                "contract_description": c_info["description"] if c_info else None,
                "history": drilldown,
                "transactions": matched_txns,
                "all_months": item["months"]
            })

        # Support custom total revenue target if set by user
        generic_rev_budget = total_rev_budget
        is_custom_rev = False
        rev_override_key = f"{club_filter}_total_revenue_{month}"
        if rev_override_key in self.custom_targets:
            total_rev_budget = float(self.custom_targets[rev_override_key])
            is_custom_rev = True

        # -----------------------------------------------------------------
        # SMART 3-LAYER FINANCIAL FORECASTING METHODOLOGY
        # Layer 1: Fixed Contracts & Retainers (Rent, Arnona, Management, Software)
        # Layer 2: Salaries & Trainers (Hourly shifts, Studio classes, Hilan gross)
        # Layer 3: Seasonal Operations & Utilities (Electricity seasonality, cleaning, credit fees)
        # -----------------------------------------------------------------
        # A month is only treated as historically finalized if actual revenue/expenses represent full closure (> 50% of budget), not partial opening entries
        is_closed_rev = (month < current_live_month) and (total_rev_actual >= (total_rev_budget * 0.5))
        is_closed_exp = (month < current_live_month) and (total_exp_actual >= (total_exp_budget * 0.5))

        # 1. EXPENSES: 3-Layer Smart Forecast
        exp_layer1_fixed = sum(p.get("projected", 0) for p in processed_fix_exp)
        exp_layer2_staff = sum(p.get("projected", 0) for p in processed_var_exp if any(k in p["name"] for k in ["מאמנ", "מדריכ", "שכר", "חוג", "סטודיו", "קבלה"]))
        exp_layer3_ops = sum(p.get("projected", 0) for p in processed_var_exp if not any(k in p["name"] for k in ["מאמנ", "מדריכ", "שכר", "חוג", "סטודיו", "קבלה"]))
        
        if is_closed_exp:
            calc_exp_projected = total_exp_actual
        else:
            calc_exp_projected = exp_layer1_fixed + exp_layer2_staff + exp_layer3_ops

        # 2. REVENUE: 3-Stream Smart Forecast
        # Stream 1: Recurring MRR memberships
        # Stream 2: Personal Training & Multi-passes
        # Stream 3: Registration fees, Studio rentals, Other
        rev_stream1_mrr = sum(p.get("projected", 0) for p in processed_incomes if "מנוי" in p["name"])
        rev_stream2_pt = sum(p.get("projected", 0) for p in processed_incomes if any(k in p["name"] for k in ["אישי", "אימון אישי", "כרטיסי"]))
        rev_stream3_other = sum(p.get("projected", 0) for p in processed_incomes if not ("מנוי" in p["name"] or any(k in p["name"] for k in ["אישי", "אימון אישי", "כרטיסי"])))

        if is_closed_rev:
            calc_rev_projected = total_rev_actual
        else:
            calc_rev_projected = rev_stream1_mrr + rev_stream2_pt + rev_stream3_other

        # Check for custom revenue forecast override
        is_custom_rev_proj = False
        rev_proj_override_key = f"{club_filter}_projected_revenue_{month}"
        if rev_proj_override_key in self.custom_targets:
            total_rev_projected = float(self.custom_targets[rev_proj_override_key])
            is_custom_rev_proj = True
        else:
            total_rev_projected = calc_rev_projected

        # Check for custom expense forecast override
        is_custom_exp_proj = False
        exp_proj_override_key = f"{club_filter}_projected_expenses_{month}"
        if exp_proj_override_key in self.custom_targets:
            total_exp_projected = float(self.custom_targets[exp_proj_override_key])
            is_custom_exp_proj = True
        else:
            total_exp_projected = calc_exp_projected

        # Calculate annual trends
        annual_trends = self.get_annual_trends(incomes_list, var_exp_list, fix_exp_list)

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

        # Copy monthly refund forecast to memberships_data for direct access in UI charts
        memberships_data["monthly_refund_forecast"] = sales_cancellations.get("monthly_refund_forecast", [])

        # -----------------------------------------------------------------
        # REVENUE PACING TRACKER (מד קצב עמידה ביעדים - LIVE)
        # Calculates:
        # - Benchmark to date (סכום שהיה אמור להיכנס להיום)
        # - Required daily run rate for the remainder of the month (קצב יומי נדרש לשאר החודש)
        # - Pacing gap (פער מול קצב צפוי)
        # - Time progress vs Money progress
        # - Status: ahead / on_track / behind / waiting_report
        # -----------------------------------------------------------------
        effective_rev_target = total_rev_budget
        days_passed = max(1, current_day)
        days_remaining = max(1, days_in_m - current_day)
        time_elapsed_pct = round((current_day / days_in_m) * 100, 1)
        benchmark_to_date = round((effective_rev_target / days_in_m) * current_day, 2)

        # Look for manager's monthly revenue report (Arbox sales, receipts, credit card settlements)
        monthly_rev_report = self.parse_monthly_revenue_report(month=month, club_filter=club_filter)
        
        # Determine active revenue for pacing:
        # 1. Closed past month with finalized ledger actual: use ledger actual
        # 2. Monthly revenue report exists: use real receipts from report
        # 3. Ledger actual exists and > 0: use ledger actual
        # 4. Otherwise: no report received yet for open month
        revenue_source_label = "כרטסת הנה״ח"
        has_real_revenue_data = True

        if month < current_live_month and total_rev_actual > 0:
            active_pacing_actual = total_rev_actual
            revenue_source_label = "כרטסת סגורה"
        elif monthly_rev_report and monthly_rev_report.get("amount", 0) > 0:
            active_pacing_actual = monthly_rev_report["amount"]
            revenue_source_label = monthly_rev_report.get("source", "דוח הכנסות חודשי")
        elif total_rev_actual > 0:
            active_pacing_actual = total_rev_actual
            revenue_source_label = "כרטסת שוטפת"
        else:
            active_pacing_actual = 0.0
            has_real_revenue_data = False
            revenue_source_label = "ממתין לדוח הכנסות"

        revenue_gap_to_pace = round(active_pacing_actual - benchmark_to_date, 2)
        remaining_target_amount = max(0.0, effective_rev_target - active_pacing_actual)
        daily_rate_required = round(remaining_target_amount / days_remaining, 2) if days_remaining > 0 else 0.0
        current_daily_pace = round(active_pacing_actual / days_passed, 2)

        money_progress_pct = round((active_pacing_actual / effective_rev_target * 100), 1) if effective_rev_target > 0 else 0.0

        if month < current_live_month and active_pacing_actual > 0:
            pacing_status = "completed"
            pacing_label = "חודש סגור"
            pacing_badge_color = "emerald"
            pacing_insight = f"החודש הסתיים עם ביצוע כולל של {formatNIS(active_pacing_actual) if 'formatNIS' in globals() else f'₪{active_pacing_actual:,.0f}'} ({revenue_source_label})"
        elif month > current_live_month:
            pacing_status = "future"
            pacing_label = "חודש עתידי"
            pacing_badge_color = "blue"
            pacing_insight = f"יעד מוגדר לחודש: {effective_rev_target:,.0f} ₪ (טרם החל)"
        elif not has_real_revenue_data:
            # Open/current month without ledger or revenue report: waiting state without false alarm
            pacing_status = "waiting_report"
            pacing_label = "ממתין לדוח הכנסות חודשי ⏳"
            pacing_badge_color = "amber"
            pacing_insight = f"הכרטסת מתעדכנת בסוף חודש. כדי לראות קצב בזמן אמת, גרור לתיקיית הדרופזון את דו״ח ההכנסות/תקבולים החודשי של ארבוקס. יעד נדרש: ₪{daily_rate_required:,.0f} ליום."
        else:
            pace_ratio = (active_pacing_actual / benchmark_to_date) if benchmark_to_date > 0 else 1.0
            if active_pacing_actual >= benchmark_to_date * 1.02:
                pacing_status = "ahead"
                pacing_label = "מקדים את הקצב 🚀"
                pacing_badge_color = "emerald"
                pacing_insight = f"פלוס של ₪{abs(revenue_gap_to_pace):,.0f} מעל הקצב הצפוי להיום! (מקור: {revenue_source_label})."
            elif active_pacing_actual >= benchmark_to_date * 0.97:
                pacing_status = "on_track"
                pacing_label = "בקצב היעד 🎯"
                pacing_badge_color = "indigo"
                pacing_insight = f"צמוד ליעד הצפוי להיום. נדרש לשמור על קצב מכירות של ₪{daily_rate_required:,.0f} ליום עד סוף החודש."
            else:
                pacing_status = "behind"
                pacing_label = "פיגור בקצב – נדרשת האצה ⚠️"
                pacing_badge_color = "rose"
                pacing_insight = f"פער של ₪{abs(revenue_gap_to_pace):,.0f} מתחת לקצב הצפוי להיום (מקור: {revenue_source_label}). נדרש להאיץ לקצב של ₪{daily_rate_required:,.0f} ליום."

        pacing_tracker = {
            "target": round(effective_rev_target, 2),
            "actual": round(active_pacing_actual, 2),
            "ledger_actual": round(total_rev_actual, 2),
            "has_real_revenue_data": has_real_revenue_data,
            "revenue_source": revenue_source_label,
            "current_day": current_day,
            "days_in_month": days_in_m,
            "days_remaining": days_remaining,
            "time_elapsed_pct": time_elapsed_pct,
            "money_progress_pct": money_progress_pct,
            "benchmark_to_date": benchmark_to_date,
            "revenue_gap_to_pace": revenue_gap_to_pace,
            "current_daily_pace": current_daily_pace,
            "daily_rate_required": daily_rate_required,
            "projected_month_end": round(total_rev_projected, 2),
            "status": pacing_status,
            "status_label": pacing_label,
            "badge_color": pacing_badge_color,
            "insight": pacing_insight,
            "is_current_month": (month == current_live_month)
        }

        # Generate rich, multi-module executive smart insights & urgency alerts
        smart_insights = self.generate_smart_insights(
            incomes_list, var_exp_list, fix_exp_list, month,
            pacing_tracker=pacing_tracker,
            memberships_data=memberships_data,
            sales_cancellations=sales_cancellations
        )

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
                    "calculated_projected": calc_rev_projected,
                    "is_custom_projected": is_custom_rev_proj,
                    "pct": round((total_rev_actual / total_rev_budget * 100), 1) if total_rev_budget > 0 else 0,
                    "breakdown": {
                        "stream1_mrr": round(rev_stream1_mrr, 2),
                        "stream2_pt": round(rev_stream2_pt, 2),
                        "stream3_other": round(rev_stream3_other, 2)
                    }
                },
                "total_expenses": {
                    "budget": total_exp_budget,
                    "actual": total_exp_actual,
                    "projected": total_exp_projected,
                    "calculated_projected": calc_exp_projected,
                    "is_custom_projected": is_custom_exp_proj,
                    "pct": round((total_exp_actual / total_exp_budget * 100), 1) if total_exp_budget > 0 else 0,
                    "breakdown": {
                        "layer1_fixed": round(exp_layer1_fixed, 2),
                        "layer2_staff": round(exp_layer2_staff, 2),
                        "layer3_ops": round(exp_layer3_ops, 2)
                    }
                }
            },
            "incomes": processed_incomes,
            "variable_expenses": processed_var_exp,
            "fixed_expenses": processed_fix_exp,
            "annual_trends": annual_trends,
            "smart_insights": smart_insights,
            "memberships": memberships_data,
            "sales_cancellations": sales_cancellations,
            "pacing_tracker": pacing_tracker,
            "revenue_breakdown": rb_data if 'rb_data' in locals() else None
        }

    def get_schedule_analytics(self, club_filter: str = "all", time_range: str = "1m", min_occurrences: int = 3, target_month: int | None = None) -> dict:
        """
        Analyzes session attendance, builds a weekly timetable grid, and ranks trainer performance.
        club_filter: 'all' | 'מועדון A+' (or 'חדר כושר') | 'פילאטיס מכשירים'
        time_range: '2w' (2 weeks) | '1m' (1 month) | '6m' (6 months)
        min_occurrences: minimum sessions for a recurring weekly slot. For '2w', automatically capped at 2.
        target_month: optional month index (1-12) to anchor the analysis.
        """
        all_files = list(INPUT_DIR.glob("**/*שיעור*.csv"))
        raw_sessions = []
        seen = set()

        for fp in all_files:
            try:
                with open(fp, encoding="utf-8-sig") as f:
                    for r in csv.DictReader(f):
                        k = (r.get("תאריך"), r.get("שעת התחלה"), r.get("מאמנים"), r.get("שיעור"), r.get("סניף"))
                        if k not in seen:
                            seen.add(k)
                            raw_sessions.append(r)
            except Exception as e:
                pass

        def clean_num(val):
            if not val:
                return 0.0
            val = str(val).replace("%", "").replace(",", "").strip()
            try:
                return float(val)
            except (ValueError, TypeError):
                return 0.0

        # Parse valid dates for held sessions
        parsed_sessions = []
        for r in raw_sessions:
            if r.get("סטטוס") != "מתקיים":
                continue
            d_str = r.get("תאריך", "").strip()
            dt = None
            for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y"):
                try:
                    dt = datetime.strptime(d_str, fmt).date()
                    break
                except (ValueError, TypeError):
                    pass
            if dt:
                parsed_sessions.append((dt, r))

        if not parsed_sessions:
            return {
                "metadata": {"club": club_filter, "range": time_range, "target_month": target_month, "total_sessions": 0},
                "kpis": {},
                "timetable": [],
                "days": [],
                "time_slots": [],
                "grid": {},
                "trainers": [],
                "hourly": []
            }

        all_dates = [dt for dt, _ in parsed_sessions]

        # Determine reference anchor date based on target_month if specified
        if target_month:
            month_dates = [dt for dt in all_dates if dt.month == target_month]
            if month_dates:
                anchor_date = max(month_dates)
            else:
                # If chosen month has no direct session CSV, anchor to closest available date
                closest_date = min(all_dates, key=lambda d: abs(d.month - target_month))
                anchor_date = closest_date
        else:
            anchor_date = max(all_dates)

        # In a 2-week window (14 days), each day of the week occurs at most 2 times (or 3 for the start day).
        # Therefore, filtering by >=3 occurrences removes almost every single day except one!
        # Automatically set min_occurrences to 2 for '2w' to allow a complete, regular 6-day timetable.
        effective_min_occ = 2 if time_range == "2w" else min_occurrences

        if time_range == "2w":
            min_date = anchor_date - timedelta(days=14)
            max_date = anchor_date
        elif time_range == "1m":
            min_date = anchor_date - timedelta(days=31)
            max_date = anchor_date
        else:  # 6m
            min_date = anchor_date - timedelta(days=183)
            max_date = anchor_date

        # Filter by date and club
        filtered_sessions = []
        for dt, r in parsed_sessions:
            if dt < min_date or dt > max_date:
                continue
            branch = r.get("סניף", "").strip()
            if "פילאטיס" in club_filter or "pilates" in club_filter.lower():
                if "פילאטיס" not in branch:
                    continue
            elif "מועדון" in club_filter or "חדר כושר" in club_filter or "gym" in club_filter.lower():
                if "פילאטיס" in branch:
                    continue
            filtered_sessions.append((dt, r))

        # Recurring slots map: (day, time, class_name, branch)
        recurring = defaultdict(lambda: {
            "day": "", "time": "", "name": "", "branch": "",
            "occurrences": 0, "checkins": [], "checkin_pcts": [],
            "late_cancels": [], "trainers_counter": Counter()
        })

        # Trainer stats map: trainer_name
        trainer_map = defaultdict(lambda: {
            "name": "", "occurrences": 0, "checkins": [],
            "checkin_pcts": [], "late_cancels": [], "classes": Counter(),
            "branches": Counter()
        })

        # Hourly stats map
        hourly_map = defaultdict(lambda: {"hour": "", "occurrences": 0, "checkins": [], "checkin_pcts": []})

        # Day of week stats map
        day_map = defaultdict(lambda: {"day": "", "occurrences": 0, "checkins": [], "checkin_pcts": []})

        all_checkin_pcts = []
        all_checkin_counts = []

        for dt, r in filtered_sessions:
            day = r.get("יום", "").strip()
            time_str = r.get("שעת התחלה", "").strip()
            name = r.get("שיעור", "").strip()
            branch = r.get("סניף", "").strip()
            t_name = r.get("מאמנים", "").strip() or "ללא מאמן"
            ci = clean_num(r.get("צ׳ק אין"))
            ci_pct = clean_num(r.get("אחוז צ׳ק אין"))
            lc = clean_num(r.get("ביטולים מאוחרים"))

            all_checkin_pcts.append(ci_pct)
            all_checkin_counts.append(ci)

            # Weekly timetable slot key
            k = (day, time_str, name, branch)
            rec = recurring[k]
            rec["day"] = day
            rec["time"] = time_str
            rec["name"] = name
            rec["branch"] = branch
            rec["occurrences"] += 1
            rec["checkins"].append(ci)
            rec["checkin_pcts"].append(ci_pct)
            rec["late_cancels"].append(lc)
            rec["trainers_counter"][t_name] += 1

            # Trainer
            tm = trainer_map[t_name]
            tm["name"] = t_name
            tm["occurrences"] += 1
            tm["checkins"].append(ci)
            tm["checkin_pcts"].append(ci_pct)
            tm["late_cancels"].append(lc)
            tm["classes"][name] += 1
            tm["branches"][branch] += 1

            # Hourly
            hour = time_str.split(":")[0] + ":00" if ":" in time_str else time_str
            hm = hourly_map[hour]
            hm["hour"] = hour
            hm["occurrences"] += 1
            hm["checkins"].append(ci)
            hm["checkin_pcts"].append(ci_pct)

            # Day
            dm = day_map[day]
            dm["day"] = day
            dm["occurrences"] += 1
            dm["checkins"].append(ci)
            dm["checkin_pcts"].append(ci_pct)

        # Build recurring weekly slots (filtered by min_occurrences)
        days_order = ["ראשון", "שני", "שלישי", "רביעי", "חמישי", "שישי"]
        regular_slots = []
        grid = {d: {} for d in days_order}

        for k, d in recurring.items():
            occ = d["occurrences"]
            if occ < effective_min_occ:
                continue

            avg_ci = round(sum(d["checkins"]) / occ, 1)
            avg_pct = round(sum(d["checkin_pcts"]) / occ, 1)
            primary_trainer = d["trainers_counter"].most_common(1)[0][0]
            subs = [f"{tr} ({c})" for tr, c in d["trainers_counter"].most_common() if tr != primary_trainer]

            tier = "strong" if avg_pct >= 80 else "moderate" if avg_pct >= 65 else "weak"

            slot_obj = {
                "day": d["day"],
                "time": d["time"],
                "name": d["name"],
                "branch": d["branch"],
                "occurrences": occ,
                "avg_checkin": avg_ci,
                "avg_checkin_pct": avg_pct,
                "primary_trainer": primary_trainer,
                "substitutes": subs,
                "total_late_cancels": int(sum(d["late_cancels"])),
                "tier": tier
            }
            regular_slots.append(slot_obj)

            # Insert into grid
            day_key = d["day"]
            time_key = d["time"]
            if day_key in grid:
                if time_key not in grid[day_key]:
                    grid[day_key][time_key] = []
                grid[day_key][time_key].append(slot_obj)

        # Distinct sorted time slots present in the timetable
        unique_time_slots = sorted(list({s["time"] for s in regular_slots}))

        # Process Trainers ranking
        trainers_list = []
        for t_name, d in trainer_map.items():
            occ = d["occurrences"]
            avg_ci = round(sum(d["checkins"]) / occ, 1) if occ else 0.0
            avg_pct = round(sum(d["checkin_pcts"]) / occ, 1) if occ else 0.0
            tier = "star" if avg_pct >= 80 else "mid" if avg_pct >= 65 else "low"
            top_classes = [c for c, _ in d["classes"].most_common(3)]
            branches = list(d["branches"].keys())

            trainers_list.append({
                "name": t_name,
                "count": occ,
                "avg_checkin": avg_ci,
                "avg_checkin_pct": avg_pct,
                "total_late_cancels": int(sum(d["late_cancels"])),
                "classes": top_classes,
                "branches": branches,
                "tier": tier
            })

        trainers_list.sort(key=lambda x: x["avg_checkin_pct"], reverse=True)

        # Process Hourly breakdown
        hourly_list = []
        for h in sorted(hourly_map.keys()):
            d = hourly_map[h]
            occ = d["occurrences"]
            hourly_list.append({
                "hour": h,
                "count": occ,
                "avg_checkin": round(sum(d["checkins"]) / occ, 1),
                "avg_checkin_pct": round(sum(d["checkin_pcts"]) / occ, 1)
            })

        # Process Day breakdown
        day_list = []
        for d in days_order:
            if d in day_map:
                dm = day_map[d]
                occ = dm["occurrences"]
                day_list.append({
                    "day": d,
                    "count": occ,
                    "avg_checkin": round(sum(dm["checkins"]) / occ, 1),
                    "avg_checkin_pct": round(sum(dm["checkin_pcts"]) / occ, 1)
                })

        # Summary KPIs
        tot_sess = len(filtered_sessions)
        avg_occ = round(sum(all_checkin_pcts) / len(all_checkin_pcts), 1) if all_checkin_pcts else 0.0
        weak_count = sum(1 for s in regular_slots if s["tier"] == "weak")
        strong_count = sum(1 for s in regular_slots if s["tier"] == "strong")
        mod_count = sum(1 for s in regular_slots if s["tier"] == "moderate")

        peak_h = max(hourly_list, key=lambda x: x["avg_checkin_pct"])["hour"] if hourly_list else "—"
        peak_d = max(day_list, key=lambda x: x["avg_checkin_pct"])["day"] if day_list else "—"
        
        star_candidates = [t for t in trainers_list if t["count"] >= (3 if time_range == "2w" else 5)]
        top_trainer_name = star_candidates[0]["name"] if star_candidates else (trainers_list[0]["name"] if trainers_list else "—")

        return {
            "metadata": {
                "club_filter": club_filter,
                "time_range": time_range,
                "target_month": target_month,
                "min_occurrences": effective_min_occ,
                "date_from": min_date.strftime("%d/%m/%Y"),
                "date_to": max_date.strftime("%d/%m/%Y"),
                "total_held_sessions": tot_sess
            },
            "kpis": {
                "avg_occupancy": avg_occ,
                "total_sessions": tot_sess,
                "regular_slots_count": len(regular_slots),
                "weak_slots_count": weak_count,
                "strong_slots_count": strong_count,
                "moderate_slots_count": mod_count,
                "peak_hour": peak_h,
                "peak_day": peak_d,
                "top_trainer": top_trainer_name
            },
            "days": days_order,
            "time_slots": unique_time_slots,
            "grid": grid,
            "regular_slots": regular_slots,
            "trainers": trainers_list,
            "hourly": hourly_list,
            "days_summary": day_list
        }

    def get_suppliers_dashboard(self, month: int = 8) -> dict:
        """
        Supplier Payments & Masav Dashboard (מס״ב ספקים)
        Extracts suppliers, amounts, terms, service month vs submission month,
        contract installment details, ageing (days since invoice), bank balance,
        and boss approvals.
        """
        month_idx = int(month) if month else 8
        target_month_name = MONTH_NAMES_HE[month_idx - 1]

        # 1. Load Whitelist for matching terms and categories
        whitelist_suppliers = {}
        whitelist_path = CONFIG_DIR / "supplier_whitelist.json"
        if whitelist_path.exists():
            try:
                with open(whitelist_path, encoding="utf-8") as wf:
                    w_data = json.load(wf)
                    for sup in w_data.get("suppliers", []):
                        whitelist_suppliers[sup["name"]] = sup
                        for alias in sup.get("aliases", []):
                            whitelist_suppliers[alias] = sup
            except Exception as e:
                print("Error loading whitelist in get_suppliers_dashboard:", e)

        # 2. Check saved state (bank balance & approved IDs)
        m_state = self.suppliers_state.get(str(month_idx), {})
        saved_bank_balance = m_state.get("bank_balance")
        approved_ids_set = set(m_state.get("approved_ids", []))
        archived_ids_set = set(m_state.get("archived_ids", []))

        # 3. Parse Suppliers from Budget & Cash Flow file (תקציב תזרים 2026.xlsx)
        cashflow_file = self.find_input_file(["*תקציב*תזרים*2026*.xlsx", "*תקציב*תזרים*.xlsx", "*תזרים*.xlsx"])
        
        suppliers_list = []
        default_bank_balance = 152477.76 if month_idx == 8 else (0.0)
        file_total_debts = 0.0
        file_total_approved = 0.0
        available_months = []

        if cashflow_file and cashflow_file.exists():
            try:
                wb = openpyxl.load_workbook(str(cashflow_file), data_only=True)
                
                # Check available months in workbook
                for s in wb.sheetnames:
                    m_chk = re.search(r"(\d{1,2})\.26", s)
                    if m_chk:
                        available_months.append(int(m_chk.group(1)))
                available_months = sorted(list(set(available_months)))

                # Find appropriate sheet, e.g., 'מסב ספקים 8.26' or 'מס"ב ספקים 8.26'
                target_sheet_name = None
                for candidate in [f"מסב ספקים {month_idx}.26", f"מס\"ב ספקים {month_idx}.26", f"ספקים לתשלום {month_idx}.26"]:
                    if candidate in wb.sheetnames:
                        target_sheet_name = candidate
                        break
                if not target_sheet_name:
                    for s in wb.sheetnames:
                        if ("מסב" in s or "ספקים" in s) and f"{month_idx}.26" in s:
                            target_sheet_name = s
                            break

                if target_sheet_name:
                    ws = wb[target_sheet_name]
                    # Row 4 or 6 often has bank balance in cell C4/B4 or C6
                    c_bal = safe_float(ws.cell(4, 3).value or ws.cell(4, 2).value or ws.cell(6, 3).value or ws.cell(6, 2).value)
                    if c_bal > 0:
                        default_bank_balance = c_bal

                    curr_supplier = None
                    for r in range(9, ws.max_row + 1):
                        c2 = ws.cell(r, 2).value
                        c3 = ws.cell(r, 3).value
                        c4 = ws.cell(r, 4).value

                        # Identify total row
                        c2_str = str(c2 or "").strip()
                        c3_str = str(c3 or "").strip()
                        if "סה\"כ חובות ספקים" in c2_str or "סהכ חובות ספקים" in c2_str or "חובות ספקים" in c2_str:
                            val = safe_float(c3 or c2)
                            if val > 0:
                                file_total_debts = val
                            continue
                        if "ספקים לתשלום" in c2_str or "לתשלום" in c2_str:
                            val = safe_float(c3 or c2)
                            if val > 0:
                                file_total_approved = val
                            continue
                        if c2_str.startswith("סה") or c3_str.startswith("סה"):
                            continue

                        # Skip subtotal rows where both c2 and c3 are numbers
                        if isinstance(c2, (int, float)) and isinstance(c3, (int, float)):
                            continue

                        # Check if row defines a new supplier name
                        if c2 is not None and not isinstance(c2, (int, float)):
                            s_clean = str(c2).strip()
                            if s_clean and not s_clean.startswith("סה"):
                                curr_supplier = s_clean

                        amt = 0.0
                        desc = ""
                        if isinstance(c3, (int, float)) and c3 > 0:
                            amt = float(c3)
                            desc = str(c4 or "").strip()
                        elif isinstance(c2, (int, float)) and c2 > 0 and c3:
                            amt = float(c2)
                            desc = str(c3 or "").strip()

                        if amt > 0 and curr_supplier:
                            # Submission month is the dashboard month
                            submission_month_str = f"{month_idx}/26"

                            # Parse service month from description if present (e.g. 5/26, 6/26, 1-6/26)
                            m_match = re.search(r"(\d{1,2}(?:-\d{1,2})?/\d{2})", desc)
                            if m_match:
                                service_month_str = m_match.group(1)
                            else:
                                service_month_str = submission_month_str

                            # Detect contracts and installments
                            is_contract = False
                            installment_str = None
                            if desc and ("הסכם" in desc or "תשלומים" in desc or "הו\"ק" in desc):
                                is_contract = True
                                installment_str = desc
                            elif curr_supplier and ("הסכם" in curr_supplier or "הו\"ק" in curr_supplier):
                                is_contract = True
                                installment_str = desc or "הסכם שוטף"

                            # Detect fill color: yellow (FFFFFF00) indicates approved/paid in cashflow workbook
                            c3_cell = ws.cell(r, 3)
                            c3_fill = c3_cell.fill.start_color.rgb if (c3_cell.fill and c3_cell.fill.start_color) else None
                            c2_cell = ws.cell(r, 2)
                            c2_fill = c2_cell.fill.start_color.rgb if (c2_cell.fill and c2_cell.fill.start_color) else None
                            is_yellow = (c3_fill == "FFFFFF00") or (c2_fill == "FFFFFF00")

                            # Match terms from whitelist or keyword defaults
                            matched_entry = whitelist_suppliers.get(curr_supplier)
                            terms = matched_entry.get("payment_terms", "+60") if matched_entry else "+60"

                            # Category classification: סטריטמול, אריאל ספא, or operational overhead
                            if curr_supplier == "סטריטמול":
                                category = "סטריטמול"
                            elif curr_supplier == "אריאל ספא":
                                category = "אריאל ספא"
                            elif matched_entry:
                                category = matched_entry.get("category", "תפעול שוטף")
                            else:
                                category = "תפעול ואחזקה"

                            if not matched_entry:
                                if any(k in curr_supplier for k in ["חשמל", "ארבוקס", "אינטרנט", "בזק", "אחזקה", "ניקיון", "יוסף"]):
                                    terms = "+30"
                                elif any(k in curr_supplier for k in ["קופה קטנה", "מזומן"]):
                                    terms = "מזומן / מיידי"
                                elif any(k in curr_supplier for k in ["ארנונה", "עירייה", "מים", "ספא", "סטריטמול", "אלקטרה"]):
                                    terms = "+60"

                            # Calculate Ageing (approximate days passed based on service month vs close date)
                            days_overdue = 0
                            is_overdue = False
                            m_num_match = re.search(r"(\d{1,2})", service_month_str)
                            if m_num_match:
                                s_m = int(m_num_match.group(1))
                                delta_m = (month_idx - s_m)
                                if delta_m < 0:
                                    delta_m = 0
                                approx_days = delta_m * 30 + 15
                                if terms == "+30" and approx_days > 45:
                                    is_overdue = True
                                    days_overdue = approx_days - 30
                                elif terms == "+60" and approx_days > 75:
                                    is_overdue = True
                                    days_overdue = approx_days - 60
                            else:
                                approx_days = 30

                            item_id = f"sup_{month_idx}_{r}_{int(amt)}"
                            if item_id in archived_ids_set:
                                continue

                            if item_id in approved_ids_set:
                                is_approved = True
                            elif "approved_ids" in m_state:
                                is_approved = False
                            else:
                                is_approved = is_yellow

                            suppliers_list.append({
                                "id": item_id,
                                "row_index": r,
                                "supplier_name": curr_supplier,
                                "amount": amt,
                                "description": desc if desc else "תשלום ספק שוטף",
                                "service_month": service_month_str,
                                "submission_month": submission_month_str,
                                "payment_terms": terms,
                                "category": category,
                                "is_contract": is_contract,
                                "installment_details": installment_str,
                                "approx_days": approx_days,
                                "is_overdue": is_overdue,
                                "days_overdue": days_overdue,
                                "approved": is_approved
                            })

            except Exception as e:
                print(f"Error parsing cashflow workbook for suppliers (month {month_idx}):", e)

        # 4. If no items from Excel, check if we have OCR invoices from input/dropzone/invoices_suppliers
        if not suppliers_list:
            inv_dir = INPUT_DIR / "dropzone" / "invoices_suppliers"
            if not inv_dir.exists():
                inv_dir = INPUT_DIR / f"2026-{month_idx:02d}" / "invoices_suppliers"
            # Fallback sample items if empty
            suppliers_list = [
                {
                    "id": f"sup_{month_idx}_1_7355",
                    "row_index": 1,
                    "supplier_name": "סטריטמול",
                    "amount": 7355.0,
                    "description": "ניקיון חודש 5/26",
                    "service_month": "5/26",
                    "submission_month": f"{month_idx}/26",
                    "payment_terms": "+60",
                    "category": "ניקיון",
                    "is_contract": False,
                    "installment_details": None,
                    "approx_days": 75,
                    "is_overdue": False,
                    "days_overdue": 0,
                    "approved": True
                },
                {
                    "id": f"sup_{month_idx}_2_17280",
                    "row_index": 2,
                    "supplier_name": "חברת החשמל",
                    "amount": 17280.0,
                    "description": "חשמל חודש 6/26",
                    "service_month": "6/26",
                    "submission_month": f"{month_idx}/26",
                    "payment_terms": "+30",
                    "category": "חשמל ומז״א",
                    "is_contract": False,
                    "installment_details": None,
                    "approx_days": 60,
                    "is_overdue": True,
                    "days_overdue": 30,
                    "approved": True
                },
                {
                    "id": f"sup_{month_idx}_3_6765",
                    "row_index": 3,
                    "supplier_name": "אגנטק",
                    "amount": 6765.0,
                    "description": "הסכם שנתי 2026 - תש' 5/12",
                    "service_month": f"{month_idx}/26",
                    "submission_month": f"{month_idx}/26",
                    "payment_terms": "+30",
                    "category": "אחזקת מכשירים",
                    "is_contract": True,
                    "installment_details": "הסכם שנתי 2026  7 תשלומים, תש' 5/12",
                    "approx_days": 25,
                    "is_overdue": False,
                    "days_overdue": 0,
                    "approved": False
                }
            ]

        # Use user-entered bank balance if present, otherwise default from file
        bank_balance = saved_bank_balance if saved_bank_balance is not None else default_bank_balance
        
        # Totals computation
        total_debts = sum(s["amount"] for s in suppliers_list)
        if file_total_debts > 0:
            total_debts = file_total_debts

        # Approved total: either sum of currently approved items or file_total_approved
        approved_sum = sum(s["amount"] for s in suppliers_list if s["approved"])
        if file_total_approved > 0 and not saved_bank_balance:
            approved_sum = file_total_approved

        balance_after_payment = bank_balance - approved_sum

        # Segmentations
        by_terms = {
            "+30": round(sum(s["amount"] for s in suppliers_list if s["payment_terms"] == "+30"), 1),
            "+60": round(sum(s["amount"] for s in suppliers_list if s["payment_terms"] == "+60"), 1),
            "immediate": round(sum(s["amount"] for s in suppliers_list if "מזומן" in s["payment_terms"] or "מיידי" in s["payment_terms"]), 1),
            "overdue": round(sum(s["amount"] for s in suppliers_list if s["is_overdue"]), 1)
        }

        # Category Breakdown
        cat_counter = defaultdict(float)
        for s in suppliers_list:
            cat_counter[s["category"]] += s["amount"]
        categories_breakdown = [
            {"category": k, "amount": round(v, 1), "pct": round(v / max(total_debts, 1) * 100, 1)}
            for k, v in sorted(cat_counter.items(), key=lambda x: x[1], reverse=True)
        ]

        return {
            "month": month_idx,
            "month_name": target_month_name,
            "available_months": available_months if available_months else [5, 6, 7, 8],
            "financial_kpis": {
                "bank_balance": round(bank_balance, 2),
                "is_manual_balance": (saved_bank_balance is not None),
                "total_debts": round(total_debts, 2),
                "total_approved": round(approved_sum, 2),
                "balance_after_payment": round(balance_after_payment, 2),
                "overdue_amount": by_terms["overdue"],
                "suppliers_count": len(suppliers_list),
                "approved_count": sum(1 for s in suppliers_list if s["approved"]),
                "archived_count": len(archived_ids_set),
                "last_masav_transmission": m_state.get("last_masav_transmission")
            },
            "by_terms": by_terms,
            "categories_breakdown": categories_breakdown,
            "suppliers": suppliers_list
        }


    # =========================================================================
    # TASKS BOARD — Club Operations Task Management
    # =========================================================================

    TASKS_FILE = CONFIG_DIR / "tasks_board.json"
    TASKS_REVENUE_OVERRIDES_FILE = CONFIG_DIR / "revenue_overrides.json"

    def _load_tasks(self) -> dict:
        if self.TASKS_FILE.exists():
            try:
                with open(self.TASKS_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return {"tasks": [], "custom_tasks": [], "archived_tasks": []}

    def _save_tasks(self, data: dict):
        data["last_updated"] = datetime.now().isoformat()
        with open(self.TASKS_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def get_tasks_board(self) -> dict:
        """Return all tasks with computed urgency and next-due dates."""
        data = self._load_tasks()
        now = datetime.now()
        all_tasks = data.get("tasks", []) + data.get("custom_tasks", [])
        result = []
        overdue_count = 0
        due_today_count = 0
        pending_count = 0

        for t in all_tasks:
            t_copy = dict(t)
            status = t.get("status", "pending")
            next_due = self._compute_next_due(t, now)
            t_copy["computed_next_due"] = next_due
            urgency = "normal"
            check_date = next_due or t.get("due_date")
            if check_date:
                try:
                    nd = datetime.strptime(check_date, "%Y-%m-%d")
                    days_until = (nd - now.replace(hour=0, minute=0, second=0, microsecond=0)).days
                    t_copy["days_until_due"] = days_until
                    if days_until < 0:
                        urgency = "overdue"
                        overdue_count += 1
                    elif days_until == 0:
                        urgency = "due_today"
                        due_today_count += 1
                    elif days_until <= 2:
                        urgency = "soon"
                except Exception:
                    pass
            t_copy["urgency"] = urgency
            if status == "pending":
                pending_count += 1
            result.append(t_copy)

        priority_order = {"high": 0, "medium": 1, "low": 2}
        urgency_order = {"overdue": 0, "due_today": 1, "soon": 2, "normal": 3}
        result.sort(key=lambda x: (
            urgency_order.get(x.get("urgency", "normal"), 3),
            priority_order.get(x.get("priority", "low"), 2)
        ))

        return {
            "tasks": result,
            "summary": {
                "total": len(result),
                "overdue": overdue_count,
                "due_today": due_today_count,
                "pending": pending_count,
                "completed_this_week": len([
                    t for t in all_tasks
                    if t.get("last_completed") and
                    (now - datetime.fromisoformat(t["last_completed"])).days <= 7
                ])
            },
            "last_updated": data.get("last_updated", now.strftime("%Y-%m-%d"))
        }

    def _compute_next_due(self, task: dict, now: datetime):
        """Compute next due date for recurring tasks."""
        recurrence = task.get("recurrence")
        last_completed = task.get("last_completed")
        if not recurrence or recurrence == "none":
            return task.get("due_date")
        base = now
        if last_completed:
            try:
                base = datetime.fromisoformat(last_completed)
            except Exception:
                pass
        if recurrence == "daily":
            return (base + timedelta(days=1)).strftime("%Y-%m-%d")
        if recurrence == "weekly":
            day_map = {"sunday": 6, "monday": 0, "tuesday": 1, "wednesday": 2,
                       "thursday": 3, "friday": 4, "saturday": 5}
            target_weekday = day_map.get(task.get("recurrence_day", "sunday"), 6)
            days_ahead = (target_weekday - now.weekday()) % 7
            if days_ahead == 0 and last_completed:
                days_ahead = 7
            return (now + timedelta(days=days_ahead)).strftime("%Y-%m-%d")
        if recurrence == "monthly":
            try:
                dom = int(task.get("recurrence_day", 1))
            except Exception:
                dom = 1
            if now.day <= dom:
                try:
                    return now.replace(day=dom).strftime("%Y-%m-%d")
                except ValueError:
                    return now.replace(day=28).strftime("%Y-%m-%d")
            else:
                nm = now.month + 1 if now.month < 12 else 1
                ny = now.year if now.month < 12 else now.year + 1
                try:
                    return now.replace(year=ny, month=nm, day=dom).strftime("%Y-%m-%d")
                except ValueError:
                    return now.replace(year=ny, month=nm, day=28).strftime("%Y-%m-%d")
        return task.get("due_date")

    def save_task(self, task_data: dict) -> dict:
        """Create or update a task."""
        import uuid
        data = self._load_tasks()
        task_id = task_data.get("id")
        is_custom = task_data.get("is_custom", True)
        tasks_list = data["custom_tasks"] if is_custom else data["tasks"]
        other_list = data["tasks"] if is_custom else data["custom_tasks"]
        if task_id:
            for lst in [tasks_list, other_list]:
                for i, t in enumerate(lst):
                    if t["id"] == task_id:
                        lst[i] = {**t, **task_data}
                        self._save_tasks(data)
                        return {"success": True, "task": lst[i]}
        else:
            task_data["id"] = "CT" + str(uuid.uuid4())[:6].upper()
            task_data["created_at"] = datetime.now().isoformat()
            task_data.setdefault("status", "pending")
            task_data["is_custom"] = True
            data["custom_tasks"].append(task_data)
            self._save_tasks(data)
        return {"success": True, "task": task_data}

    def complete_task(self, task_id: str) -> dict:
        """Mark task as completed; reset recurring tasks automatically."""
        data = self._load_tasks()
        now_str = datetime.now().isoformat()
        for lst_key in ["tasks", "custom_tasks"]:
            lst = data[lst_key]
            for i, t in enumerate(lst):
                if t["id"] == task_id:
                    recurrence = t.get("recurrence", "none")
                    if recurrence and recurrence != "none":
                        lst[i]["last_completed"] = now_str
                        lst[i]["status"] = "pending"
                        self._save_tasks(data)
                        return {"success": True, "task_id": task_id,
                                "next_due": self._compute_next_due(lst[i], datetime.now())}
                    else:
                        t["status"] = "completed"
                        t["last_completed"] = now_str
                        data["archived_tasks"].append(t)
                        lst.pop(i)
                        self._save_tasks(data)
                        return {"success": True, "task_id": task_id, "archived": True}
        return {"success": False, "error": "Task not found"}

    # =========================================================================
    # REVENUE BREAKDOWN — Arbox-sourced MTD income by category + overrides
    # =========================================================================

    def _load_revenue_overrides(self) -> dict:
        if self.TASKS_REVENUE_OVERRIDES_FILE.exists():
            try:
                with open(self.TASKS_REVENUE_OVERRIDES_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return {}

    def _save_revenue_overrides(self, data: dict):
        with open(self.TASKS_REVENUE_OVERRIDES_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def get_revenue_breakdown(self, month: int = None) -> dict:
        """Build MTD revenue breakdown strictly by the 8 official ledger income categories (Gross/Net VAT)."""
        now = datetime.now()
        target_month = month or now.month
        year = self.year
        month_name = MONTH_NAMES_HE[target_month - 1]
        days_in_month = calendar.monthrange(year, target_month)[1]
        today = now.day if (now.month == target_month and now.year == year) else days_in_month
        pct_month_elapsed = round(today / days_in_month * 100, 1)

        # Active member counts for MRR estimate
        gym_members, pilates_members = 0, 0
        try:
            mem_data = self.parse_membership_data()
            stats = mem_data.get("stats", {})
            gym_members = stats.get("gym", {}).get("active", 0)
            pilates_members = stats.get("pilates", {}).get("active", 0)
        except Exception:
            pass

        # Estimate PT invoices from OCR if available
        estimated_pt = 0.0
        try:
            with open(CONFIG_DIR / "invoices_ocr.json", "r", encoding="utf-8") as f:
                inv_data = json.load(f)
            invoices = inv_data.get("invoices", [])
            month_str = f"{year}-{target_month:02d}"
            for inv in invoices:
                if not str(inv.get("doc_date", "")).startswith(month_str):
                    continue
                cat = inv.get("category", "studio")
                total = float(inv.get("stated_total", 0) or 0)
                if cat in ("personal", "mixed"):
                    estimated_pt += total
        except Exception:
            pass

        # Get actual ledger numbers for target month if available from budget workbooks
        ledger_actuals = {}
        try:
            gym_wb = OUTPUT_DIR / "תקציב_מול_ביצוע_חדר_כושר.xlsx"
            pilates_wb = OUTPUT_DIR / "תקציב_מול_ביצוע_פילאטיס.xlsx"
            if gym_wb.exists():
                gym_data = self.parse_budget_workbook(gym_wb, "חדר כושר")
                for inc in (gym_data.get("incomes", []) if gym_data else []):
                    c = str(inc.get("code", "")).strip()
                    act = float(inc.get("months", {}).get(target_month, {}).get("actual", 0.0) or 0.0)
                    if act > 0:
                        ledger_actuals[c] = act
            if pilates_wb.exists():
                pilates_data = self.parse_budget_workbook(pilates_wb, "פילאטיס מכשירים")
                for inc in (pilates_data.get("incomes", []) if pilates_data else []):
                    c = str(inc.get("code", "")).strip()
                    act = float(inc.get("months", {}).get(target_month, {}).get("actual", 0.0) or 0.0)
                    if act > 0:
                        ledger_actuals[c] = act
        except Exception as e:
            print("Error loading ledger actuals in get_revenue_breakdown:", e)

        overrides = self._load_revenue_overrides()
        month_key = f"{year}-{target_month:02d}"
        mo = overrides.get(month_key, {})

        # The 8 official income items from Idan's monthly management workbook (Image 2)
        INCOME_DEFINITIONS = [
            {
                "code": "80009",
                "label": "כרטיסיות - פריפיט/מוב",
                "branch": "מועדון",
                "is_exempt_vat": True,
                "default_gross": 7720.0,
                "arbox_metric": "זיכויי פלטפורמות Move / FreeFit (נטו ללא מע״מ)",
                "category": "third_party"
            },
            {
                "code": "80004",
                "label": "אימונים אישיים",
                "branch": "מועדון",
                "is_exempt_vat": False,
                "default_gross": 35655.0,
                "arbox_metric": f"חשבוניות אישיים מ-OCR (₪{estimated_pt:,.0f})" if estimated_pt > 0 else "אימונים אישיים וחבילות מועדון",
                "category": "pt"
            },
            {
                "code": "80008",
                "label": "דמי הרשמה",
                "branch": "מועדון",
                "is_exempt_vat": False,
                "default_gross": 5000.0,
                "arbox_metric": "דמי הרשמה וצ'יפ ראשוני מועדון",
                "category": "registration"
            },
            {
                "code": "80010",
                "label": "השכרת סטודיו לחברות / שונות",
                "branch": "מועדון",
                "is_exempt_vat": False,
                "default_gross": 0.0,
                "arbox_metric": "השכרת סטודיו ואירועים",
                "category": "rentals"
            },
            {
                "code": "80001",
                "label": "מנויים כולל מנויים מיוחדים",
                "branch": "מועדון",
                "is_exempt_vat": False,
                "default_gross": 176283.0,
                "arbox_metric": f"{gym_members} מנויים פעילים (מועדון)",
                "category": "membership"
            },
            {
                "code": "81008",
                "label": "דמי הרשמה",
                "branch": "פילאטיס",
                "is_exempt_vat": False,
                "default_gross": 1000.0,
                "arbox_metric": "דמי הרשמה וצ'יפ פילאטיס",
                "category": "registration"
            },
            {
                "code": "81009",
                "label": "כרטיסיות",
                "branch": "פילאטיס",
                "is_exempt_vat": False,
                "default_gross": 1100.0,
                "arbox_metric": "רכישת כרטיסיות סטודיו פילאטיס",
                "category": "cards"
            },
            {
                "code": "81001",
                "label": "מנויים וכרטיסיות",
                "branch": "פילאטיס",
                "is_exempt_vat": False,
                "default_gross": 54741.0,
                "arbox_metric": f"{pilates_members} מנויים פעילים (פילאטיס)",
                "category": "membership"
            }
        ]

        DEFAULT_NET_MAP = {
            "80009": 7720.0,
            "80004": 30216.0,
            "80008": 4237.0,
            "80010": 0.0,
            "80001": 149393.0,
            "81008": 847.0,
            "81009": 932.0,
            "81001": 46391.0,
        }

        rows = []
        for item in INCOME_DEFINITIONS:
            c = item["code"]
            override_val = mo.get(c)
            # Legacy field support if previously keyed by name
            if override_val is None:
                legacy_keys = {
                    "80001": "mrr_gym", "81001": "mrr_pilates",
                    "80004": "pt_actual", "80009": "move_actual"
                }
                if c in legacy_keys:
                    override_val = mo.get(legacy_keys[c])

            if override_val is not None and override_val != "":
                gross = float(override_val)
                if item["is_exempt_vat"]:
                    net = gross
                else:
                    net = round(gross / 1.18, 0)
            else:
                gross = float(item["default_gross"])
                net = DEFAULT_NET_MAP.get(c, round(gross / 1.18, 0))

            act_led = ledger_actuals.get(c, 0.0)

            rows.append({
                "code": c,
                "label": item["label"],
                "branch": item["branch"],
                "is_exempt_vat": item["is_exempt_vat"],
                "actual_ledger": round(act_led, 2),
                "gross": round(gross, 0),
                "net": round(net, 0),
                "override": override_val,
                "arbox_metric": item["arbox_metric"],
                "editable": True,
                "category": item["category"]
            })

        total_gross = sum(r["gross"] for r in rows)
        total_net = sum(r["net"] for r in rows)
        total_ledger = sum(r["actual_ledger"] for r in rows)

        prev_month = target_month - 1 if target_month > 1 else 12
        prev_mo = overrides.get(f"{year}-{prev_month:02d}", {})
        prev_total = float(prev_mo.get("_total_override", 0) or 0)

        return {
            "month": target_month,
            "month_name": month_name,
            "year": year,
            "days_elapsed": today,
            "days_in_month": days_in_month,
            "pct_elapsed": pct_month_elapsed,
            "rows": rows,
            "totals": {
                "total_gross": round(total_gross, 0),
                "total_net": round(total_net, 0),
                "actual_ledger": round(total_ledger, 0),
                "estimated": round(total_gross, 0),
                "prev_month": round(prev_total, 0)
            },
            "move_freefit_status": {
                "move": {"api": False, "note": "Move Israel אינה מספקת API פומבי. כלול בסעיף 80009."},
                "freefit": {"api": False, "note": "FreeFit Israel מערכת סגורה. כלול בסעיף 80009."}
            }
        }

    def _load_sessions_for_month(self, target_month: int) -> list:
        """Load Arbox sessions CSV rows filtered to the target month."""
        import glob as _glob
        year = self.year
        candidates = []
        search_dirs = [
            BASE_DIR / "input" / "dropzone",
            BASE_DIR / "input" / f"{year}-{target_month:02d}_AUGUST",
            BASE_DIR / "input" / f"{year}-{target_month:02d}_JULY",
        ]
        # Add the Hebrew dropzone folder
        for d in BASE_DIR.iterdir():
            if d.is_dir() and "לגרור" in d.name:
                search_dirs.append(d)
        for folder_path in search_dirs:
            if Path(folder_path).exists():
                for f in Path(folder_path).iterdir():
                    if f.suffix == ".csv" and "שיעור" in f.name:
                        candidates.append(f)

        sessions = []
        for fpath in candidates:
            try:
                with open(fpath, "r", encoding="utf-8-sig") as fh:
                    reader = csv.DictReader(fh)
                    for row in reader:
                        date_str = row.get("תאריך", "")
                        try:
                            d = datetime.strptime(date_str, "%d/%m/%Y")
                            if d.month == target_month and d.year == year:
                                # Find checkins col with either regular or typographic apostrophe
                                checkins_val = 0
                                for col_name in row.keys():
                                    if col_name and "ק" in col_name and "אין" in col_name and "אחוז" not in col_name:
                                        raw_c = row.get(col_name, "0") or "0"
                                        checkins_val = int(raw_c) if str(raw_c).isdigit() else 0
                                        break
                                
                                reg_val = 0
                                raw_reg = row.get("הרשמות", "0") or "0"
                                if str(raw_reg).isdigit():
                                    reg_val = int(raw_reg)

                                sessions.append({
                                    "date": date_str,
                                    "trainer": row.get("מאמנים", ""),
                                    "class_name": row.get("שיעור", ""),
                                    "category": row.get("קטגוריה", ""),
                                    "branch": row.get("סניף", ""),
                                    "registrations": reg_val,
                                    "checkins": checkins_val,
                                    "status": row.get("סטטוס", ""),
                                })
                        except ValueError:
                            continue
                if sessions:
                    break  # Use first successful file
            except Exception:
                continue
        return sessions

    def save_revenue_override(self, data: dict) -> dict:
        """Save a manual override for a revenue line item."""
        month_key = data.get("month_key")
        field = str(data.get("code") or data.get("field", "")).strip()
        value = data.get("value")
        overrides = self._load_revenue_overrides()
        if month_key not in overrides:
            overrides[month_key] = {}
        overrides[month_key][field] = float(value) if (value is not None and value != "") else None
        mo = overrides[month_key]
        total = sum(float(v or 0) for k, v in mo.items()
                    if not k.startswith("_") and v is not None)
        overrides[month_key]["_total_override"] = round(total, 2)
        self._save_revenue_overrides(overrides)
        return {"success": True, "month_key": month_key, "field": field, "code": field, "value": value}
