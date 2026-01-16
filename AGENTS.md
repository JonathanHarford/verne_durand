# Jules Tools

This repository contains a collection of scripts and tools for managing and interacting with the **Jules API**, an autonomous software engineering agent.

## Project Overview

The primary purpose of this project is to provide a harness for running autonomous coding tasks via Jules. It includes:

*   **`ralph-wiggum-jules.py`**: A Python-based autonomous harness that executes a plan (list of tasks) by creating Jules sessions, monitoring them, and merging the results.
*   **`session_info.bb`**: A utility script (using Babashka) to inspect the detailed status and history of a specific Jules session.

## Key Tools & Usage

### 1. Ralph Wiggum (Autonomous Harness)

This script automates the "Plan -> Execute -> Merge" loop. It reads a markdown file with a checklist, picks the next unchecked item, starts a Jules session, and applies the result.

**Prerequisites:**
*   `uv` (strictly used for execution and dependency management)
*   `JULES_API_KEY` environment variable set.
*   A markdown plan file (e.g., `PLAN.md`).

**Usage:**

```bash
export JULES_API_KEY="your-api-key"

# Run with uv (auto-installs dependencies)
uv run ralph-wiggum-jules.py --plan PLAN.md --project /path/to/target/repo

# Options:
#   --branch <name>   : The git branch to work on (default: ralph-wiggum)
#   --timeout <sec>   : Timeout for each task (default: 600)
#   -v                : Verbose logging
```

**Workflow:**
1.  Checks `PLAN.md` for the next unchecked task (e.g., `- [ ] Fix bug X`).
2.  Creates a Jules session for that task.
3.  Polls for completion (handles timeouts and "stale" sessions).
4.  Fetches the remote branch created by Jules.
5.  Merges the changes into the local working branch.
6.  Updates `PLAN.md` to mark the task as done.
7.  Pushes changes to origin.
8.  Repeats until all tasks are done.

### 2. Session Info (Inspector)

A CLI tool to view detailed reports of a session.

**Prerequisites:**
*   [Babashka](https://babashka.org/) (`bb`)
*   `JULES_API_KEY` environment variable set.

**Usage:**

```bash
./session_info.bb <session-id>
```

**Output:**
Displays session state, creation time, source context, full prompt, output PRs, and a chronological log of activities (agent messages, progress updates).

## Development & Testing

*   **Language:** Python 3 (Harness) & Clojure/Babashka (Utilities).
*   **Testing:** Unit tests for the Python harness are in `test_stale_logic.py`.
    *   Run with: `uv run test_stale_logic.py`

## Directory Structure

*   `ralph-wiggum-jules.py`: Main automation script.
*   `session_info.bb`: Helper utility for session inspection.
*   `docs/` & `skills/`: Documentation and context files defining the Jules agent's capabilities (likely used for bootstrapping the agent itself).