```mermaid
flowchart LR
    Start((Start)) --> Init[Initialize: Check JULES_API_KEY, Chdir]
    Init --> ParsePlan[Parse PLAN.md for Unchecked Tasks]
    ParsePlan --> HasTasks{Tasks left?}
    
    HasTasks -- No --> Done((Done))
    
    HasTasks -- Yes --> GetNextTask[Select Next Task]
    GetNextTask --> InitRetry[Set attempts = 0]
    InitRetry --> RetryLoop{attempts < 3?}
    
    RetryLoop -- No --> CritFail((Critical Failure))
    
    RetryLoop -- Yes --> IncAttempts[attempts++]
    IncAttempts --> EnsureBranch[Ensure Work Branch]
    EnsureBranch --> CheckExisting{Find Active Sessions via API?}
    
    CheckExisting -- Yes --> UseExisting[Set resume_id]
    CheckExisting -- No --> StartNew[API: create_session]
    
    UseExisting --> WaitLoop
    StartNew --> WaitLoop[Wait Loop]
    
    subgraph Execution [run_jules_task]
        direction TB
        WaitLoop --> Poll[API: get_session status]
        Poll --> Status{Status?}
        Status -- RUNNING --> Wait5[Wait 10s]
        Wait5 --> WaitLoop
        Status -- FAILED/ERROR/CANCELLED --> ReturnFail[Return failure status]
        Status -- COMPLETED/SUCCEEDED --> ApplyChanges[Apply Changes]
        
        subgraph MergeWorkflow [Apply Changes Flow]
            direction TB
            CheckOutputs[Check Session Outputs for Pull Request] --> Fetch[Git Fetch Origin]
            Fetch --> FindBranch[Find Jules Remote Branch]
            FindBranch --> Merge[Git Merge Remote Branch]
            Merge --> MergeSuccess{Merge OK?}
            MergeSuccess -- Yes --> ReturnSuccess[Return SUCCESS]
            MergeSuccess -- No --> ReturnApplyFail[Return APPLY_FAILED]
        end
        ApplyChanges --> MergeWorkflow
    end
    
    GetNextTask --> Execution
    Execution --> Result{Result?}
    
    Result -- SUCCESS --> Push[Git Push Work Branch]
    Push --> HasTasks
    
    Result -- Others --> RetryWait[Wait 10s]
    RetryWait --> RetryLoop
```

## Ralph Wiggum: Autonomous Jules API Harness

This script automates the execution of multiple tasks using the Jules API. It parses a markdown checklist (e.g., `PLAN.md`) and executes unchecked tasks sequentially.

### Key Features
- **API-Based**: Uses direct REST API calls via `httpx`, removing dependency on the `jules` CLI.
- **`uv` Ready**: Includes inline dependency metadata for zero-setup execution.
- **Resilient**: Automatically resumes active sessions or retries failed tasks (up to 3 times).
- **Git Integration**: Automatically manages branch creation, remote pushing, and merging Jules' generated changes.

### Usage
Run the harness using `uv`:
```bash
export JULES_API_KEY="your-api-key"
uv run ralph-wiggum-jules.py --plan PLAN.md --project /path/to/project
```

### Flow Architecture
The diagram above illustrates the polling and merge logic used to coordinate between the local repository and the Jules autonomous agent.