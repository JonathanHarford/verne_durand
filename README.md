# Verne Durand: Autonomous Jules SDK Harness

This script automates the execution of multiple tasks using the Jules AI agent. It parses a YAML checklist (e.g., `PLAN.yaml`) and executes tasks in the `todo` and `started` lists sequentially.

### Key Features
- **SDK-Based**: Uses the official `jules-agent-sdk`, ensuring robust communication and automatic retries.
- **`uv` Ready**: Includes inline dependency metadata for zero-setup execution.
- **Resilient**: Automatically resumes active sessions or retries failed tasks (up to 3 times).
- **Auto-Approval**: Detects when a plan requires approval and automatically approves it to maintain autonomy.
- **Git Integration**: Automatically manages branch creation, remote pushing, merging Jules' changes, and **cleaning up transient branches** after work is applied.
- **Atomic Updates**: Automatically commits and pushes plan updates (e.g. moving tasks to `started`) before Jules begins work.

## TODO

* Parallel task execution

## Usage
Run the harness using `uv`. The plan file is a YAML file specific to the project you are working on, usually located at the root of that project.

```bash
export JULES_API_KEY="your-api-key"
# If PLAN.yaml is in the project root:
uv run verne_durand.py --plan PLAN.yaml --project /path/to/project
```

## Development

### Git Hooks
To keep the `README.md` and `prompt_template.txt` in sync, this project uses a git hook. To enable it, run:
```bash
git config core.hooksPath .githooks
```
This will run `tools/sync_prompt.py` automatically before every commit.

## Checklist Format (`PLAN.yaml`)
The checklist is a YAML file with the following structure:
```yaml
todo:
  - "Implement feature A"
  - "Fix bug B"
started: []
completed: []
```

## Flow Architecture

### 1. Main Orchestration Loop
```mermaid
---
config:
  layout: elk
---
flowchart TD
    Start((Start)) --> Init[Initialize: Check JULES_API_KEY, Chdir]
    Init --> Ensure[Ensure Work Branch & Initial Push]
    Ensure --> ParsePlan[Parse PLAN.yaml for Pending Tasks]
    ParsePlan --> HasTasks{Tasks left?}
    
    HasTasks -- No --> Done((Done))
    
    HasTasks -- Yes --> GetNextTask[Select Next Task]
    GetNextTask --> CheckStatus{Task status?}
    
    CheckStatus -- todo --> MoveToStarted[Move task to 'started' list]
    MoveToStarted --> PushPlan[Git Push Updated Plan]
    PushPlan --> InitRetry
    
    CheckStatus -- started --> InitRetry[Set attempts = 0]
    InitRetry --> RetryLoop{attempts < 3?}
    
    RetryLoop -. No .-> CritFail((Critical Failure))
    
    RetryLoop -->|Yes| IncAttempts[attempts++]
    
    IncAttempts --> Execution(((2. Execute Task)))
    
    Execution -->|SUCCESS| Verify{Marked Complete?}
    
    Verify -- Yes --> Push[Git Push Work Branch]
    Push --> HasTasks
    
    Verify -- No --> Pause((Stop for Review))
    
    Execution -. FAIL/ERROR .-> CheckRetry{attempts < 3?}

    CheckRetry -->|Yes| RetryWait[Wait 15s]
    RetryWait --> RetryLoop

    CheckRetry -. No .-> CritFail
```

### 2. Task Execution Detail (run_jules_task)
```mermaid
---
config:
  layout: elk
---
flowchart TD
    Entry((Start Task)) --> EnsureBranch[Ensure Work Branch]
    EnsureBranch --> CheckExisting{Active sessions already?}

    CheckExisting -- Yes --> Poll[Get status]
    CheckExisting -- No --> StartNew[Create Session]
    StartNew --> Poll

    Poll --> Status{Status?}

    Status -- Working --> Approve[Approve Plan]
    Approve --> Wait[Wait 30s]
    Wait --> Poll

    Status -. FAILED/ERROR .-> ReturnFail((FAIL))
    Status -- COMPLETED --> CheckOutputs[Get PR ID from Session]
    subgraph "Apply Changes"
      CheckOutputs --> FetchPR[Git Fetch PR]
      FetchPR --> Merge[Git Merge FETCH_HEAD]
      Merge --> DeleteBranch[Delete Remote Jules Branch]
    end
    DeleteBranch --> MergeSuccess((SUCCESS))
    FetchPR -.-> ReturnFail
    CheckOutputs -.-> ReturnFail
    Merge -.-> ReturnFail
    DeleteBranch -.-> MergeSuccess
```

## Prompt Template

Jules is instructed to use a specific tool to mark tasks as completed. This ensures that the YAML file is updated reliably and that Jules makes an explicit "executive decision" on whether a task is truly finished.

```markdown
{task}

Use your best judgment, and ask absolutely no questions.

As your final step, if and only if the task is fully completed, update the status by running:
`uv run tools/mark_done.py --task "{task}" --plan "{plan_path}"`

If you inadvertently completed any subsequent tasks, run the tool for those as well.
```

## Tools

*   **`tools/mark_done.py`**: A CLI tool used by Jules to move a task from `started` to `completed` in the plan YAML.
*   **`tools/sync_prompt.py`**: A utility to keep the `README.md` and `prompt_template.txt` in sync.
*   **`tools/session_info.py`**: Inspected detailed status of a Jules session.

## The Name

If one person checks out _Anathem_ thanks to this silly name, it'll've been worth it.