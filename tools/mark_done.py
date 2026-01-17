#!/usr/bin/env -S uv run --script
# /// script
# dependencies = [
#   "PyYAML",
# ]
# ///

import yaml
import argparse
import os
import sys

def main():
    parser = argparse.ArgumentParser(description="Mark a task as completed in a YAML plan.")
    parser.add_argument("--task", required=True, help="The exact task string to mark as completed.")
    parser.add_argument("--plan", default="PLAN.yaml", help="Path to the YAML plan file.")
    args = parser.parse_args()

    if not os.path.exists(args.plan):
        print(f"Error: Plan file '{args.plan}' not found.", file=sys.stderr)
        sys.exit(1)

    with open(args.plan, 'r') as f:
        try:
            data = yaml.safe_load(f) or {}
        except yaml.YAMLError as e:
            print(f"Error parsing YAML: {e}", file=sys.stderr)
            sys.exit(1)

    # Ensure structure exists
    for key in ['todo', 'started', 'completed']:
        if key not in data or data[key] is None:
            data[key] = []

    task_name = args.task.strip()
    moved = False

    # Check 'started' first
    if task_name in data['started']:
        data['started'].remove(task_name)
        moved = True
    # Then check 'todo' just in case Jules finished it without the orchestrator noticing
    elif task_name in data['todo']:
        data['todo'].remove(task_name)
        moved = True

    if moved:
        if task_name not in data['completed']:
            data['completed'].append(task_name)
        
        with open(args.plan, 'w') as f:
            yaml.dump(data, f, default_flow_style=False, sort_keys=False)
        print(f"Successfully marked '{task_name}' as completed in {args.plan}")
    else:
        print(f"Task '{task_name}' not found in 'started' or 'todo' lists. No changes made.")

if __name__ == "__main__":
    main()
