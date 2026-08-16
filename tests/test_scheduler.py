"""
Unit and acceptance tests for the Schedulizer solver.
Run: python tests/test_scheduler.py
"""

import sys
import os

B = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(B, "core"))
sys.path.insert(0, os.path.join(B, "tools"))
sys.path.insert(0, B)

from solver import ShiftSolver
from scheduler import get_demo_data

ok = 0
fail = 0

def check(name, cond, detail=""):
    global ok, fail
    if cond:
        ok += 1
        print(f"  PASS  {name}")
    else:
        fail += 1
        print(f"  FAIL  {name}  {detail}")


def test_basic_solver():
    print("\n--- Test 1: Basic ShiftSolver with Demo Data ---")
    trainers, shifts = get_demo_data()
    solver = ShiftSolver(trainers, shifts)
    res = solver.solve()

    check("Solver returns OPTIMAL status", res["status"] == "OPTIMAL")
    check("All 6 shifts assigned", len(res["schedule"]) == 6)

    # Check max shifts constraint per trainer
    for t in trainers:
        assigned_count = res["summary"].get(t["id"], 0)
        check(f"Trainer {t['name']} <= max ({t['max_shifts']})", assigned_count <= t["max_shifts"], f"Got {assigned_count}")


def test_unavailability_constraint():
    print("\n--- Test 2: Unavailability Hard Constraint ---")
    trainers, shifts = get_demo_data()
    
    # Force Arad Kotzer to be unavailable for Sunday Morning
    trainers[0]["unavailable"].append("s_sun_morn")
    
    solver = ShiftSolver(trainers, shifts)
    res = solver.solve()
    
    # Find who got Sunday Morning
    sun_morn_item = next(it for it in res["schedule"] if it["shift"]["id"] == "s_sun_morn")
    assigned_ids = [t["id"] for t in sun_morn_item["assigned"]]
    
    check("Arad Kotzer NOT assigned to Sunday Morning", "t_kotzer" not in assigned_ids)


def test_infeasible_schedule():
    print("\n--- Test 3: Infeasible Schedule Detection ---")
    trainers = [
        {"id": "t1", "name": "תמי", "max_shifts": 1, "preferred": [], "unavailable": []}
    ]
    shifts = [
        {"id": "s1", "day": "ראשון", "name": "בוקר", "required": 1},
        {"id": "s2", "day": "שני",   "name": "בוקר", "required": 1}
    ]
    solver = ShiftSolver(trainers, shifts)
    res = solver.solve()
    
    check("Correctly flags INFEASIBLE when not enough staff", res["status"] == "INFEASIBLE")


if __name__ == "__main__":
    print("=" * 50)
    print("🧪 Running Gym Schedulizer Solver Tests")
    print("=" * 50)
    
    test_basic_solver()
    test_unavailability_constraint()
    test_infeasible_schedule()
    
    print("\n" + "=" * 50)
    print(f"Results: {ok} PASSED, {fail} FAILED")
    print("=" * 50)
    sys.exit(0 if fail == 0 else 1)
