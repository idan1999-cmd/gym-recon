"""
Gym Schedulizer CLI Tool (Prototype)

Usage:
    python tools/scheduler.py [--demo]
"""

import sys
import os
import argparse
import json

# Ensure UTF-8 output encoding for Windows PowerShell
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

# Add project root to sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.solver import ShiftSolver


def get_demo_data():
    """Sample data representing a 3-day shift schedule at the gym/pilates studio."""
    trainers = [
        {
            "id": "t_kotzer",
            "name": "ערד קוצר",
            "max_shifts": 3,
            "preferred": ["s_sun_morn", "s_mon_morn"],
            "unavailable": ["s_tue_eve"]
        },
        {
            "id": "t_verchovsky",
            "name": "לאון ורחובסקי",
            "max_shifts": 3,
            "preferred": ["s_sun_eve", "s_mon_eve"],
            "unavailable": ["s_sun_morn"]
        },
        {
            "id": "t_zlotkewicz",
            "name": "איב זלוטקביץ",
            "max_shifts": 2,
            "preferred": ["s_tue_morn", "s_tue_eve"],
            "unavailable": []
        }
    ]

    shifts = [
        {"id": "s_sun_morn", "day": "יום ראשון", "name": "משמרת בוקר", "time": "08:00-14:00", "branch": "חדר כושר", "required": 1},
        {"id": "s_sun_eve",  "day": "יום ראשון", "name": "משמרת ערב",  "time": "16:00-22:00", "branch": "חדר כושר", "required": 1},
        {"id": "s_mon_morn", "day": "יום שני",   "name": "משמרת בוקר", "time": "08:00-14:00", "branch": "חדר כושר", "required": 1},
        {"id": "s_mon_eve",  "day": "יום שני",   "name": "משמרת ערב",  "time": "16:00-22:00", "branch": "חדר כושר", "required": 1},
        {"id": "s_tue_morn", "day": "יום שלישי", "name": "משמרת בוקר", "time": "08:00-14:00", "branch": "חדר כושר", "required": 1},
        {"id": "s_tue_eve",  "day": "יום שלישי", "name": "משמרת ערב",  "time": "16:00-22:00", "branch": "חדר כושר", "required": 1},
    ]

    return trainers, shifts


def main():
    parser = argparse.ArgumentParser(description="Gym Staff Shift Schedulizer")
    parser.add_argument("--demo", action="store_true", default=True, help="Run with demo data")
    args = parser.parse_args()

    print("=" * 60)
    print("🗓️  Gym Schedulizer — OR-Tools Constraint Solver Engine")
    print("=" * 60)

    trainers, shifts = get_demo_data()

    print(f"\n📥 Loaded {len(trainers)} trainers and {len(shifts)} target shifts.")
    print("⚙️  Running OR-Tools CP-SAT solver...\n")

    solver = ShiftSolver(trainers, shifts)
    res = solver.solve()

    if res["status"] in ("OPTIMAL", "FEASIBLE"):
        print(f"✅ Solution status: {res['status']} (Score: {res['score']})")
        print("-" * 60)

        # Print schedule nicely grouped by day
        by_day = {}
        for item in res["schedule"]:
            day = item["shift"]["day"]
            by_day.setdefault(day, []).append(item)

        for day, items in by_day.items():
            print(f"\n📌 {day}:")
            for it in items:
                s = it["shift"]
                assigned_names = ", ".join(t["name"] for t in it["assigned"]) if it["assigned"] else "⚠️ UNASSIGNED"
                print(f"  • {s['name']} ({s['time']}) | {s['branch']}: {assigned_names}")

        print("\n" + "-" * 60)
        print("📊 Trainer Shift Summary:")
        for t in trainers:
            count = res["summary"].get(t["id"], 0)
            print(f"  • {t['name']}: {count} shifts (max: {t['max_shifts']})")
        print("=" * 60)
    else:
        print("❌ INFEASIBLE: Could not satisfy all constraints with the given pool.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
