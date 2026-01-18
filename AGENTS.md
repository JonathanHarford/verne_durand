# Verne Durand

This repository contains **Verne Durand**, an autonomous harness for executing multi-task plans via the **Jules API**.

## Project Overview

The primary purpose of this project is to automate software engineering work by orchestrating Jules sessions. It includes:

*   **`verne_durand.py`**: The main autonomous orchestrator. It parses a YAML checklist, picks tasks sequentially, creates Jules sessions, monitors them, merges the resulting PRs, and updates the checklist.
*   **`prompt_template.txt`**: The prompt template injected into each Jules session. It instructs Jules how to report its status.

## Key Tools & Usage

### 1. Verne Durand (Autonomous Orchestrator)

This script automates the "Plan -> Execute -> Merge" loop. It reads a YAML checklist (e.g., `PLAN.yaml`), picks the next task from `started` or `todo`, starts a Jules session, and applies the result.

**Prerequisites:**
*   `uv` (used for execution and dependency management)
*   `JULES_API_KEY` environment variable set.
*   A YAML plan file (e.g., `PLAN.yaml`) in the target project.

**Usage:**

```bash
export JULES_API_KEY="your-api-key"

# Run with uv (auto-installs dependencies)
uv run verne_durand.py --plan PLAN.yaml --project /path/to/target/repo
```

### 2. Session Info (Inspector)

A CLI tool to view detailed reports of a Jules session.

**Usage:**

```bash
uv run tools/session_info.py <session-id>
```

**Output:**
Displays session state, creation time, source context, full prompt, output PRs, and a chronological log of activities.

## Directory Structure

*   `verne_durand.py`: Main orchestration script.
*   `prompt_template.txt`: The prompt template sent to Jules.
*   `tools/`: Utility scripts.
    *   `session_info.py`: Inspect a Jules session.
    *   `test_pr_structure.py`: Test utility for PR structure validation.
*   `tests/`: Unit tests for the orchestrator.
*   `skills/`: Gemini skill definitions.
*   `docs/`: Documentation and context files.

## Development & Testing

*   **Language:** Python 3 (using `jules-agent-sdk`).
*   **Dependencies:** Managed via `uv` or `pip install jules-agent-sdk python-dotenv pyyaml`.
*   **Tests:** Run with `PYTHONPATH=. uv run python3 tests/test_verne.py`.

## Checklist Format (`PLAN.yaml`)

The plan file is a YAML file with the following structure:

```yaml
todo:
  - "Implement feature A"
  - "Fix bug B"
started: []
completed: []
```

Tasks are processed in order: `started` first, then `todo`.