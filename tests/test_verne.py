import unittest
import os
import yaml
import tempfile
import shutil
from verne_durand import PlanManager, parse_jules_response

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
        self.assertEqual(result['next'], "Task B")
        self.assertEqual(result['todo'], ["Task C", "Task D"])

    def test_parse_done_marker(self):
        text = "I have finished. [DONE]"
        result = parse_jules_response(text)
        self.assertTrue(result['is_done'])
        self.assertEqual(result.get('completed'), []) # No structured blocks

    def test_parse_partial_status(self):
        text = """
[STATUS]
COMPLETED: Part 1
NEXT: Part 2
"""
        result = parse_jules_response(text)
        self.assertEqual(result['completed'], ["Part 1"])
        self.assertEqual(result['next'], "Part 2")
        self.assertEqual(result['todo'], [])

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
        next_task = "Subtask 2"
        todo_items = ["Subtask 3"]

        manager.expand_task(
            "Big Task",
            completed_items,
            next_task,
            todo_items,
            "sess_123",
            "sha_abc"
        )

        data = manager.load()
        # Check started
        self.assertEqual(data["started"], ["Subtask 2"])

        # Check completed
        self.assertEqual(len(data["completed"]), 1)
        self.assertEqual(data["completed"][0]["task"], "Subtask 1")
        self.assertEqual(data["completed"][0]["session_id"], "sess_123")

        # Check todo (Subtask 3 should be prepended)
        self.assertEqual(data["todo"][0], "Subtask 3")
        self.assertEqual(data["todo"][1], "Future Task")

if __name__ == '__main__':
    unittest.main()
