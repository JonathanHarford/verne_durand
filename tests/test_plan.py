import unittest
import os
import yaml
import tempfile
from lib.plan import PlanManager

class TestPlanManager(unittest.TestCase):
    def setUp(self):
        # Create a temporary file for testing
        self.temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".yaml")
        self.temp_file.close()
        self.filepath = self.temp_file.name

    def tearDown(self):
        # Remove the temporary file
        if os.path.exists(self.filepath):
            os.remove(self.filepath)

    def test_init_empty_file(self):
        # File exists but is empty
        manager = PlanManager(self.filepath)
        self.assertEqual(manager.data["todo"], [])
        self.assertEqual(manager.data["started"], [])
        self.assertEqual(manager.data["completed"], [])

    def test_init_nonexistent_file(self):
        # File does not exist
        os.remove(self.filepath)
        manager = PlanManager(self.filepath)
        self.assertEqual(manager.data["todo"], [])
        self.assertEqual(manager.data["started"], [])
        self.assertEqual(manager.data["completed"], [])

    def test_load_existing_data(self):
        data = {
            "todo": ["Task A"],
            "started": ["Task B"],
            "completed": ["Task C"]
        }
        with open(self.filepath, 'w') as f:
            yaml.dump(data, f)

        manager = PlanManager(self.filepath)
        self.assertEqual(manager.data["todo"], ["Task A"])
        self.assertEqual(manager.data["started"], ["Task B"])
        self.assertEqual(manager.data["completed"], ["Task C"])

    def test_get_next_task(self):
        manager = PlanManager(self.filepath)
        manager.data["started"] = ["Task B"]
        manager.data["todo"] = ["Task A"]

        # Priority: started > todo
        self.assertEqual(manager.get_next_task(), "Task B")

        manager.data["started"] = []
        self.assertEqual(manager.get_next_task(), "Task A")

        manager.data["todo"] = []
        self.assertIsNone(manager.get_next_task())

    def test_mark_started(self):
        manager = PlanManager(self.filepath)
        manager.data["todo"] = ["Task A"]

        # Move from todo to started
        self.assertTrue(manager.mark_started("Task A"))
        self.assertEqual(manager.data["todo"], [])
        self.assertEqual(manager.data["started"], ["Task A"])

        # Try to mark started again (already in started, but method returns False if not in todo)
        self.assertFalse(manager.mark_started("Task A"))

        # Task not present
        self.assertFalse(manager.mark_started("Task Z"))

    def test_mark_complete(self):
        manager = PlanManager(self.filepath)
        manager.data["started"] = ["Task B"]
        manager.data["todo"] = ["Task A"]

        # Complete from started
        self.assertTrue(manager.mark_complete("Task B"))
        self.assertEqual(manager.data["started"], [])
        self.assertEqual(manager.data["completed"], ["Task B"])

        # Complete from todo
        self.assertTrue(manager.mark_complete("Task A"))
        self.assertEqual(manager.data["todo"], [])
        self.assertIn("Task A", manager.data["completed"])

        # Task not present
        self.assertFalse(manager.mark_complete("Task Z"))

    def test_save_and_reload(self):
        manager = PlanManager(self.filepath)
        manager.data["todo"] = ["Task A"]
        manager.save()

        # Create new manager to check persistence
        new_manager = PlanManager(self.filepath)
        self.assertEqual(new_manager.data["todo"], ["Task A"])

        # Modify first manager
        manager.data["todo"].append("Task B")
        manager.save()

        # Reload second manager
        new_manager.reload()
        self.assertEqual(new_manager.data["todo"], ["Task A", "Task B"])

    def test_state_persistence_across_instances(self):
        # 1. Create manager, load data
        data = {"todo": ["Task 1"], "started": [], "completed": []}
        with open(self.filepath, 'w') as f:
            yaml.dump(data, f)

        m1 = PlanManager(self.filepath)
        self.assertEqual(m1.get_next_task(), "Task 1")

        # 2. Update via m1
        m1.mark_started("Task 1")
        # m1 is updated in memory
        self.assertEqual(m1.data["started"], ["Task 1"])

        # 3. Create m2 (should read from disk, which is OLD)
        m2 = PlanManager(self.filepath)
        self.assertEqual(m2.data["todo"], ["Task 1"])
        self.assertEqual(m2.data["started"], [])

        # 4. Save m1
        m1.save()

        # 5. Reload m2
        m2.reload()
        self.assertEqual(m2.data["started"], ["Task 1"])
        self.assertEqual(m2.data["todo"], [])

    def test_load_empty_file_reset(self):
        # 1. Setup with data
        data = {"todo": ["Task A"], "started": [], "completed": []}
        with open(self.filepath, 'w') as f:
            yaml.dump(data, f)

        manager = PlanManager(self.filepath)
        self.assertEqual(manager.data["todo"], ["Task A"])

        # 2. Clear file content (simulate empty file)
        with open(self.filepath, 'w') as f:
            pass # Empty

        # 3. Reload
        manager.reload()

        # 4. Verify data is reset to empty
        self.assertEqual(manager.data["todo"], [])

    def test_load_invalid_yaml_reset(self):
         # 1. Setup with data
        data = {"todo": ["Task A"], "started": [], "completed": []}
        with open(self.filepath, 'w') as f:
            yaml.dump(data, f)

        manager = PlanManager(self.filepath)
        self.assertEqual(manager.data["todo"], ["Task A"])

        # 2. Write invalid YAML (e.g. just a string, not a dict)
        with open(self.filepath, 'w') as f:
            f.write("Just a string")

        # 3. Reload
        manager.reload()

        # 4. Verify data is reset to empty (since it's not a dict)
        self.assertEqual(manager.data["todo"], [])

if __name__ == '__main__':
    unittest.main()
