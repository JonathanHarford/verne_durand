import unittest
import os
import yaml
import tempfile
import shutil
from unittest.mock import MagicMock, patch
import verne_durand
from verne_durand import PlanManager, parse_jules_response, wait_for_session

class TestSessionWaiting(unittest.TestCase):
    def setUp(self):
        self.original_poll_interval = verne_durand.POLL_INTERVAL_SEC
        verne_durand.POLL_INTERVAL_SEC = 0.01

    def tearDown(self):
        verne_durand.POLL_INTERVAL_SEC = self.original_poll_interval

    @patch('time.sleep')
    def test_wait_for_session_paused(self, mock_sleep):
        client = MagicMock()
        session_mock = MagicMock()
        session_mock.state = "PAUSED"
        session_mock.name = "sessions/123"
        client.sessions.get.return_value = session_mock
        client.activities.list_all.return_value = []

        success, status, _, _ = wait_for_session(client, "sessions/123", timeout=1)

        self.assertFalse(success)
        self.assertEqual(status, "PAUSED")

class TestResponseParser(unittest.TestCase):
    def test_parse_simple_status(self):
        text = """
Some text
[STATUS]
COMPLETED: Task A
NEXT: Task B
TODO: Task C
TODO: Task D
"""
        result = parse_jules_response(text)
        self.assertEqual(result['completed'], ["Task A"])
        # NEXT is mapped to TODO, next field is unused
        self.assertIsNone(result['next'])
        self.assertEqual(result['todo'], ["Task B", "Task C", "Task D"])

    def test_parse_partial_status(self):
        text = """
[STATUS]
COMPLETED: Part 1
NEXT: Part 2
"""
        result = parse_jules_response(text)
        self.assertEqual(result['completed'], ["Part 1"])
        self.assertIsNone(result['next'])
        self.assertEqual(result['todo'], ["Part 2"])

    def test_parse_completed_with_desc(self):
        text = """
[STATUS]
COMPLETED: Task A (with details)
"""
        result = parse_jules_response(text)
        self.assertEqual(result['completed'], ["Task A (with details)"])

class TestPlanManager(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.plan_path = os.path.join(self.test_dir, "PLAN.yaml")

    def tearDown(self):
        shutil.rmtree(self.test_dir)

    def create_plan(self, todo=None, started=None, completed=None):
        data = {
            "todo": todo or [],
            "started": started or [],
            "completed": completed or []
        }
        with open(self.plan_path, 'w') as f:
            yaml.dump(data, f)
        return PlanManager(self.plan_path)

    def test_record_completion(self):
        manager = self.create_plan(started=["Task 1"])
        manager.record_completion("Task 1", "sess_123", "sha_abc")

        data = manager.load()
        self.assertEqual(data["started"], [])
        self.assertEqual(len(data["completed"]), 1)
        item = data["completed"][0]
        self.assertIsInstance(item, dict)
        self.assertEqual(item["task"], "Task 1")
        self.assertEqual(item["session_id"], "sess_123")
        self.assertEqual(item["commit_hash"], "sha_abc")

    def test_expand_task(self):
        manager = self.create_plan(started=["Big Task"], todo=["Future Task"])

        completed_items = ["Subtask 1"]
        # next_task = "Subtask 2" # Next is now just the first todo
        todo_items = ["Subtask 2", "Subtask 3"]

        manager.expand_task(
            "Big Task",
            completed_items,
            todo_items,
            "sess_123",
            "sha_abc"
        )

        data = manager.load()
        # Check started - nothing starts automatically in expand_task anymore?
        # The logic in expand_task:
        # data["todo"] = new_todos + data["todo"]
        # It does NOT move anything to started. The main loop picks the first task (started or todo) next.

        self.assertEqual(data["started"], [])

        # Check completed
        self.assertEqual(len(data["completed"]), 1)
        self.assertEqual(data["completed"][0]["task"], "Subtask 1")
        self.assertEqual(data["completed"][0]["session_id"], "sess_123")

        # Check todo
        self.assertEqual(data["todo"][0], "Subtask 2")
        self.assertEqual(data["todo"][1], "Subtask 3")
        self.assertEqual(data["todo"][2], "Future Task")

if __name__ == '__main__':
    unittest.main()
