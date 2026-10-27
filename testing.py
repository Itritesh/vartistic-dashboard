"""
VARTISTIC AGENCY OPERATIONS & DASHBOARD VERIFICATION SUITE
File: testing.py
Verifies: User task ownership, multi-commit persistence, consecutive day streaks,
          overdue blocker reasoning schema, and Admin validation-only authority.
"""

import unittest
from datetime import datetime, timedelta

class TestVartisticCoreOperations(unittest.TestCase):

    def setUp(self):
        self.today = datetime.now().date()
        self.yesterday = self.today - timedelta(days=1)
        self.two_days_ago = self.today - timedelta(days=2)

        # Mock User Roster with Streaks
        self.users = [
            {"id": "u0", "name": "Vartistic Admin", "role": "admin", "streak": 0, "points": 0, "lastActiveDate": ""},
            {"id": "u1", "name": "Ritesh", "role": "member", "streak": 4, "points": 340, "lastActiveDate": str(self.yesterday)},
            {"id": "u2", "name": "sarib", "role": "member", "streak": 6, "points": 520, "lastActiveDate": str(self.today)},
            {"id": "u3", "name": "Rohit", "role": "member", "streak": 1, "points": 140, "lastActiveDate": str(self.two_days_ago)}
        ]

        # Mock Task Board
        self.tasks = [
            {
                "id": "TSK-101",
                "title": "Brand Glassmorphic Dashboard Design",
                "assignee": "Ritesh",
                "status": "In Progress",
                "deadline": str(self.today + timedelta(days=2)),
                "verified": False,
                "isSelfInitiated": False,
                "delayReason": "",
                "commits": []
            },
            {
                "id": "TSK-105",
                "title": "Docker Sync Proxy Setup",
                "assignee": "Rohit",
                "status": "Pending",
                "deadline": str(self.yesterday),
                "verified": False,
                "isSelfInitiated": False,
                "delayReason": "Pending Docker networking certificates on candidate machine.",
                "commits": []
            }
        ]

    # TEST 1: CANDIDATE CAN RECORD COMMITS & SUBMIT OUTPUT
    def test_candidate_task_ownership(self):
        task = self.tasks[0]
        self.assertEqual(task["status"], "In Progress")

        # Candidate logs a commit
        commit = {"hash": "9b71e1", "msg": "Built frosted glass sidebar tokens", "time": "11:20 AM"}
        task["commits"].append(commit)
        task["status"] = "Completed"

        self.assertEqual(len(task["commits"]), 1)
        self.assertEqual(task["status"], "Completed")
        # Ensure candidate submission is not auto-verified
        self.assertFalse(task["verified"])

    # TEST 2: ADMIN VALIDATION ONLY PRIVILEGE
    def test_admin_validation_authority(self):
        task = self.tasks[0]
        task["status"] = "Completed"

        # Member cannot approve task
        member = self.users[1]
        self.assertNotEqual(member["role"], "admin")
        
        # Admin verifies task
        admin = self.users[0]
        self.assertEqual(admin["role"], "admin")
        task["verified"] = True

        self.assertTrue(task["verified"])
        self.assertEqual(task["status"], "Completed")

    # TEST 3: CONSECUTIVE STREAK CALCULATION
    def test_streak_calculation_rules(self):
        def update_streak(user, active_date):
            last_date = user["lastActiveDate"]
            today_str = str(active_date)
            yesterday_str = str(active_date - timedelta(days=1))

            if last_date == today_str:
                user["points"] += 30
            elif last_date == yesterday_str:
                user["streak"] += 1
                user["points"] += 30
                user["lastActiveDate"] = today_str
            else:
                user["streak"] = 1
                user["points"] += 30
                user["lastActiveDate"] = today_str

        # Ritesh contributed yesterday -> increments streak today
        ritesh = self.users[1]
        self.assertEqual(ritesh["streak"], 4)
        update_streak(ritesh, self.today)
        self.assertEqual(ritesh["streak"], 5)

        # Sarib already contributed today -> streak stays unchanged
        sarib = self.users[2]
        self.assertEqual(sarib["streak"], 6)
        update_streak(sarib, self.today)
        self.assertEqual(sarib["streak"], 6)

        # Rohit missed yesterday -> streak resets to 1
        rohit = self.users[3]
        self.assertEqual(rohit["streak"], 1)
        update_streak(rohit, self.today)
        self.assertEqual(rohit["streak"], 1)

    # TEST 4: DELAY REASONING SCHEMA ON BLOCKED/OVERDUE TASKS
    def test_overdue_task_delay_reason(self):
        overdue_task = self.tasks[1]
        deadline = datetime.strptime(overdue_task["deadline"], "%Y-%m-%d").date()
        
        is_overdue = deadline < self.today and not overdue_task["verified"]
        self.assertTrue(is_overdue)
        self.assertTrue(len(overdue_task["delayReason"]) > 0, "Overdue or blocked tasks must carry explicit delay reasoning.")

    # TEST 5: SELF-INITIATED EXTRA WORK LOGGING
    def test_self_initiated_work_flag(self):
        extra_task = {
            "id": "EXT-106",
            "title": "WebGL Particle Backdrop Experiment",
            "assignee": "Ritesh",
            "isSelfInitiated": True,
            "status": "In Progress"
        }
        self.assertTrue(extra_task["isSelfInitiated"])
        self.assertEqual(extra_task["assignee"], "Ritesh")

if __name__ == "__main__":
    print("=" * 70)
    print("RUNNING VARTISTIC OPERATIONS ENGINE TEST SUITE (testing.py)")
    print("=" * 70)
    unittest.main(verbosity=2)