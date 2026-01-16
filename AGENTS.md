# Jules Tools

This repository contains a collection of scripts and tools for managing and interacting with the **Jules API**, an autonomous software engineering agent.

## Project Overview

The primary purpose of this project is to provide a harness for running autonomous coding tasks via Jules. It includes:

*   **`ralph-wiggum-jules.py`**: A Python-based autonomous harness that executes a plan (list of tasks) by creating Jules sessions, monitoring them, and merging the results. Uses the `jules-agent-sdk`.
*   **`session_info.py`**: A utility script to inspect the detailed status and history of a specific Jules session. Uses the `jules-agent-sdk`.

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
```

### 2. Session Info (Inspector)

A CLI tool to view detailed reports of a session.

**Usage:**

```bash
uv run session_info.py <session-id>
```

**Output:**
Displays session state, creation time, source context, full prompt, output PRs, and a chronological log of activities.

## Development & Testing

*   **Language:** Python 3 (using `jules-agent-sdk`).
*   **Dependencies:** Managed via `uv` or `pip install jules-agent-sdk`.

## Directory Structure

*   `ralph-wiggum-jules.py`: Main automation script.
*   `session_info.py`: Helper utility for session inspection.
*   `docs/`: Documentation and context files.