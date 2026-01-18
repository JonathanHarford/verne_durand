import os
import yaml
from verne_durand import PlanManager

def test_plan_manager():
    test_file = "test_plan.yaml"
    if os.path.exists(test_file):
        os.remove(test_file)
        
    manager = PlanManager(test_file)
    data = {
        "completed": [],
        "started": ["Task A"],
        "todo": ["Task B", "Task C"]
    }
    manager.save(data)
    
    print("Initial state:")
    print(yaml.dump(manager.load()))
    
    # Test expand_task with overlap
    # NOTE: next_task argument removed. First item in todo_items becomes next.
    print("\nExpanding 'Task A' with 'Subtask A.1' (new start), 'Task B' (existing todo), and 'Task D' (new todo)...")
    
    # Simulating a split: 
    # COMPLETED: Task A - Part 1
    # TODO: Subtask A.1
    # TODO: Task D
    # TODO: Task B
    
    manager.expand_task(
        original_task="Task A",
        completed_items=["Task A - Part 1"],
        todo_items=["Subtask A.1", "Task D", "Task B"],
        session_id="123",
        commit_hash="abc"
    )
    
    final_data = manager.load()
    print("Final state:")
    print(yaml.dump(final_data))
    
    # Assertions
    assert len(final_data["completed"]) == 1
    assert final_data["completed"][0]["task"] == "Task A - Part 1"
    
    # Check that Subtask A.1 is at the top of started (wait, the logic puts them in TODO now?)
    # Let's check the implementation.
    # expand_task: new_todos = [...] -> data["todo"] = new_todos + data["todo"]
    # So "Subtask A.1" should be at the top of 'todo'.
    # 'started' should be empty (since Task A was removed).
    
    assert "Task A" not in final_data["started"]
    assert "Task A - Part 1" not in final_data["started"]
    
    # Check Todo Order
    # Expected: Subtask A.1, Task D, Task B, Task C (since Task B was deduped and moved? No, dedup logic:
    # "new_todos = [t for t in todo_items if t not in data["todo"] and t not in data["started"]]"
    # Task B is in data["todo"], so it's NOT in new_todos.
    # So data["todo"] remains: [Task B, Task C]
    # new_todos: [Subtask A.1, Task D]
    # Final todo: [Subtask A.1, Task D, Task B, Task C]
    
    todos = final_data["todo"]
    print(f"Todos: {todos}")
    
    assert todos[0] == "Subtask A.1"
    assert todos[1] == "Task D"
    assert "Task B" in todos
    assert "Task C" in todos
    
    print("\nTest passed! Logic verified.")
    
    os.remove(test_file)

if __name__ == "__main__":
    test_plan_manager()
