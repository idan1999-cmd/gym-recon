import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from dashboard.backend.data_service import DashboardDataService

class TestScheduleAnalytics(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ds = DashboardDataService()

    def test_gym_analytics(self):
        res = self.ds.get_schedule_analytics(club_filter="מועדון A+", time_range="1m", min_occurrences=3)
        self.assertIn("kpis", res)
        self.assertIn("grid", res)
        self.assertIn("trainers", res)
        self.assertGreater(res["kpis"]["total_sessions"], 0)
        self.assertGreater(res["kpis"]["regular_slots_count"], 0)
        for slot in res["regular_slots"]:
            self.assertGreaterEqual(slot["occurrences"], 3)
            self.assertIn(slot["tier"], ["strong", "moderate", "weak"])

    def test_pilates_analytics(self):
        res = self.ds.get_schedule_analytics(club_filter="פילאטיס מכשירים", time_range="1m", min_occurrences=3)
        self.assertIn("kpis", res)
        self.assertGreater(res["kpis"]["total_sessions"], 0)
        self.assertGreater(res["kpis"]["regular_slots_count"], 0)
        for slot in res["regular_slots"]:
            self.assertIn("פילאטיס", slot["branch"])

    def test_time_ranges(self):
        res_2w = self.ds.get_schedule_analytics(club_filter="all", time_range="2w", min_occurrences=2)
        res_1m = self.ds.get_schedule_analytics(club_filter="all", time_range="1m", min_occurrences=3)
        res_6m = self.ds.get_schedule_analytics(club_filter="all", time_range="6m", min_occurrences=3)
        self.assertLess(res_2w["kpis"]["total_sessions"], res_1m["kpis"]["total_sessions"])
        self.assertLessEqual(res_1m["kpis"]["total_sessions"], res_6m["kpis"]["total_sessions"])

if __name__ == "__main__":
    unittest.main()
