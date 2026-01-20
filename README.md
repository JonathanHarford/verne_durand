# Verne Durand: Autonomous Jules SDK Harness

If you're not using your 100 Jules sessions per day, you're leaving _money on the table._

![Verne Durand](docs/ralph_verne.png)

This script automates the sequential execution of tasks using the Jules AI agent.

Verne_Durand is ALPHA. Trust it accordingly. When you encounter weirdness, please open an Issue.

### Key Features

- **API-Based**: Uses the [jules-agent-sdk](https://github.com/AsyncFuncAI/jules-agent-sdk-python) to communicate with the Jules AI agent.
- **`uv` Ready**: Includes inline dependency metadata for zero-setup execution.
- **Resilient**: Automatically resumes active sessions or retries failed tasks (but not indefinitely).
- **Stale Session Handling**: Detects and recovers from stalled Jules sessions by recording rejected sessions in the plan to avoid re-joining "ghost" states.
- **Auto-Approval**: Detects when a plan requires approval and automatically approves it to maintain autonomy.
- **Git Integration**: Automatically manages branch creation, remote pushing, merging Jules' changes, and **cleaning up transient branches** after work is applied.

## Usage

1. Get your [Jules API key](https://jules.google.com/settings/api).
2. Commit a checklist (e.g. PLAN.yaml) for Jules in your project. It should look like:

```yaml
todo:
  - "Implement feature A"
  - "Fix bug B"
started: []
completed: []
rejected: []
```

3. Run the harness using `uv`.

```bash
export JULES_API_KEY="your-api-key" # Or set it in verne_durand's .env file
# If PLAN.yaml is in the project root:
uv run verne_durand.py --project /path/to/project --plan PLAN.yaml
```

## Demo

Copy [docs/demo.yaml](docs/demo.yaml) to an empty repository, and run the script!

## Flow Architecture

### 1. Main Control Loop

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

    RetryLoop -- No --> CritFail((Critical Failure))

    RetryLoop -->|Yes| IncAttempts[attempts++]

    IncAttempts --> Execution[[2. Execute Task]]

    Execution -->|SUCCESS| ResultProcessing[[3. Process Task Result]]
    ResultProcessing --> HasTasks

    Execution -- FAIL/ERROR --> CheckRetry{attempts < 3?}
    Execution -- STALE --> RecordReject[Record rejected session in PLAN.yaml]
    RecordReject --> CheckRetry

    CheckRetry -->|Yes| RetryWait[Wait 15s]
    RetryWait --> RetryLoop

    CheckRetry -- No --> CritFail
```

### 2. Task Execution Detail (run_jules_task)

```mermaid
---
config:
  layout: elk
---
flowchart TD
    Entry((Start Task)) --> CheckExisting{"Recent active<br/>sessions exist?"}

    CheckExisting -- Yes --> Resume[Resume existing session]
    Resume --> Poll

    CheckExisting -- No --> StartNew[Create new session with prompt]
    StartNew --> Poll[Poll session status]

    Poll --> Status{State?}

    Status -- "QUEUED/PLANNING/<br/>IN_PROGRESS" --> CheckStale{"Inactive for<br/>20+ min?"}
    CheckStale -- Yes --> ReturnStale((STALE))
    CheckStale -- No --> Wait[Wait 30s]
    Wait --> Poll

    Status -- AWAITING_PLAN_APPROVAL --> AutoApprove[Auto-approve plan]
    AutoApprove --> Wait

    Status -- FAILED --> ReturnFail((FAIL))
    Status -- COMPLETED --> CheckOutputs[Get PR from session.outputs]

    subgraph "Apply Changes"
      CheckOutputs --> FetchPR[git fetch pull/NUMBER/head]
      FetchPR --> Merge[git merge --no-edit FETCH_HEAD]
      Merge --> DeleteBranch[git push origin --delete branch]
      DeleteBranch --> ParsePR[Parse PR description for STATUS block]
    end

    ParsePR --> MergeSuccess((SUCCESS))
    CheckOutputs -.-> ReturnFail
    FetchPR -.-> ReturnFail
```

### 3. Task Result Processing

```mermaid
---
config:
  layout: elk
---
flowchart TD
    Entry((Entry)) --> ParseStatus{Parse PR Status Block}

    ParseStatus -- "COMPLETED" --> RecordComplete[Record completion]

    ParseStatus -- "COMPLETED & 1+ TODO" --> ExpandTask["Split task into<br>completed/todo"]

    ParseStatus -- "No Marker" --> PartialWork[Partial work]

    ExpandTask --> PushUpdate[Git Push Updated Plan]
    RecordComplete --> PushUpdate
    PartialWork --> PushUpdate

    PushUpdate --> Exit((Exit))
```

## Prompt Template

See [prompt_template.txt](prompt_template.txt). By all means, edit it as you see fit.

## Tools

- **`tools/session_info.py`**: Inspects detailed status of a Jules session.
