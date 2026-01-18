import os
import yaml
from typing import List, Dict, Optional

class PlanManager:
    def __init__(self, filepath: str):
        self.filepath = filepath
        self.data: Dict[str, List[str]] = {
            "todo": [],
            "started": [],
            "completed": []
        }
        self.load()

    def load(self) -> None:
        """Loads the plan from the file. Initializes with empty structure if file doesn't exist."""
        if os.path.exists(self.filepath):
            with open(self.filepath, 'r') as f:
                loaded = yaml.safe_load(f)

            if loaded and isinstance(loaded, dict):
                self.data = {
                    "todo": loaded.get("todo") or [],
                    "started": loaded.get("started") or [],
                    "completed": loaded.get("completed") or []
                }
            else:
                self.data = {
                    "todo": [],
                    "started": [],
                    "completed": []
                }
        else:
             self.data = {
                "todo": [],
                "started": [],
                "completed": []
            }

    def save(self) -> None:
        """Saves the current in-memory plan to the file."""
        with open(self.filepath, 'w') as f:
            yaml.dump(self.data, f, default_flow_style=False)

    def reload(self) -> None:
        """Explicitly reloads the plan from disk."""
        self.load()

    def get_next_task(self) -> Optional[str]:
        """Returns the next task to work on.

        Prioritizes tasks in 'started', then 'todo'.
        Returns None if no tasks are available.
        """
        if self.data["started"]:
            return self.data["started"][0]
        if self.data["todo"]:
            return self.data["todo"][0]
        return None

    def mark_started(self, task: str) -> bool:
        """Moves a task from 'todo' to 'started'.

        Returns True if the task was found and moved, False otherwise.
        """
        if task in self.data["todo"]:
            self.data["todo"].remove(task)
            if task not in self.data["started"]:
                self.data["started"].append(task)
            return True
        return False

    def mark_complete(self, task: str) -> bool:
        """Moves a task from 'started' or 'todo' to 'completed'.

        Returns True if the task was found and moved, False otherwise.
        """
        moved = False
        if task in self.data["started"]:
            self.data["started"].remove(task)
            moved = True
        elif task in self.data["todo"]:
            self.data["todo"].remove(task)
            moved = True

        if moved:
            if task not in self.data["completed"]:
                self.data["completed"].append(task)
            return True

        return False
