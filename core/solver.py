"""
Gym Schedulizer Core Engine — Integer Linear Programming (PuLP / CBC) Solver

Assigns trainers to shift slots while respecting hard constraints (coverage, no overlaps, max shifts)
and maximizing soft preferences (preferred shifts, fairness).
"""

import pulp


class ShiftSolver:
    def __init__(self, trainers, shifts, constraints=None):
        """
        trainers: list of dicts [{"id": "t1", "name": "ערד קוצר", "max_shifts": 4, "preferred": [...], "unavailable": [...]}]
        shifts: list of dicts [{"id": "s1", "day": "ראשון", "name": "משמרת בוקר", "start": "08:00", "end": "13:00", "required": 1}]
        constraints: dict of global rules (e.g. {"max_shifts_per_day": 1})
        """
        self.trainers = trainers
        self.shifts = shifts
        self.constraints = constraints or {"max_shifts_per_day": 1}
        self.prob = pulp.LpProblem("Gym_Shift_Scheduling", pulp.LpMaximize)
        self.vars = {}

    def solve(self):
        # 1. Create binary decision variables: X[trainer_id, shift_id] in {0, 1}
        for t in self.trainers:
            for s in self.shifts:
                var_name = f"x_{t['id']}_{s['id']}"
                self.vars[(t['id'], s['id'])] = pulp.LpVariable(var_name, cat=pulp.LpBinary)

        # 2. Hard Constraint: Exactly `required` trainers per shift
        for s in self.shifts:
            self.prob += (
                pulp.lpSum(self.vars[(t['id'], s['id'])] for t in self.trainers) == s.get('required', 1),
                f"Coverage_{s['id']}"
            )

        # 3. Hard Constraint: Max shifts per day per trainer
        days = list({s['day'] for s in self.shifts})
        max_per_day = self.constraints.get("max_shifts_per_day", 1)
        for t in self.trainers:
            for d in days:
                day_shifts = [s for s in self.shifts if s['day'] == d]
                if day_shifts:
                    self.prob += (
                        pulp.lpSum(self.vars[(t['id'], s['id'])] for s in day_shifts) <= max_per_day,
                        f"MaxDay_{t['id']}_{d}"
                    )

        # 4. Hard Constraint: Max shifts total per trainer per week/period
        for t in self.trainers:
            max_shifts = t.get('max_shifts', len(self.shifts))
            self.prob += (
                pulp.lpSum(self.vars[(t['id'], s['id'])] for s in self.shifts) <= max_shifts,
                f"MaxTotal_{t['id']}"
            )

        # 5. Hard Constraint: Trainer unavailable shifts
        for t in self.trainers:
            unavail = set(t.get('unavailable', []))
            for s in self.shifts:
                if s['id'] in unavail or (s['day'], s['name']) in unavail:
                    self.prob += (
                        self.vars[(t['id'], s['id'])] == 0,
                        f"Unavail_{t['id']}_{s['id']}"
                    )

        # 6. Objective Function: Soft Preferences & Fair Allocation
        objective_terms = []
        for t in self.trainers:
            pref = set(t.get('preferred', []))
            for s in self.shifts:
                var = self.vars[(t['id'], s['id'])]
                if s['id'] in pref or (s['day'], s['name']) in pref:
                    # High positive score for fulfilling preferred shift
                    objective_terms.append(10 * var)
                else:
                    # Baseline score for scheduling available trainer
                    objective_terms.append(1 * var)

        self.prob += pulp.lpSum(objective_terms), "Maximize_Preference_Satisfaction"

        # 7. Solve using default CBC solver (msg=False suppresses solver stdout noise)
        solver = pulp.PULP_CBC_CMD(msg=False, timeLimit=5)
        self.prob.solve(solver)

        status_str = pulp.LpStatus[self.prob.status]

        # 8. Extract results
        if status_str in ("Optimal", "Feasible"):
            assigned_shifts = []
            trainer_counts = {t['id']: 0 for t in self.trainers}

            for s in self.shifts:
                assigned_trainers = []
                for t in self.trainers:
                    val = pulp.value(self.vars[(t['id'], s['id'])])
                    if val is not None and round(val) == 1:
                        assigned_trainers.append(t)
                        trainer_counts[t['id']] += 1

                assigned_shifts.append({
                    "shift": s,
                    "assigned": assigned_trainers
                })

            return {
                "status": status_str.upper(),
                "score": pulp.value(self.prob.objective),
                "schedule": assigned_shifts,
                "summary": trainer_counts
            }
        else:
            return {
                "status": "INFEASIBLE",
                "score": 0,
                "schedule": [],
                "summary": {}
            }
