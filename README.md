

## Verne Durand: Autonomous Jules SDK Harness

This script automates the execution of multiple tasks using the Jules AI agent. It parses a markdown checklist (e.g., `PLAN.md`) and executes unchecked tasks sequentially.

### Key Features
- **SDK-Based**: Uses the official `jules-agent-sdk`, ensuring robust communication and automatic retries.
- **`uv` Ready**: Includes inline dependency metadata for zero-setup execution.
- **Resilient**: Automatically resumes active sessions or retries failed tasks (up to 3 times).
- **Auto-Approval**: Detects when a plan requires approval and automatically approves it to maintain autonomy.
- **Git Integration**: Automatically manages branch creation, remote pushing, and merging Jules' generated changes.

### Usage
Run the harness using `uv`:
```bash
export JULES_API_KEY="your-api-key"
uv run verne_durand.py --plan PLAN.md --project /path/to/project
```

### Flow Architecture
```mermaid
---
config:
  layout: elk
---
flowchart TD
    Start((Start)) --> Init[Initialize: Check JULES_API_KEY, Chdir]
    Init --> ParsePlan[Parse PLAN.md for Unchecked Tasks]
    ParsePlan --> HasTasks{Tasks left?}
    
    HasTasks -- No --> Done((Done))
    
    HasTasks -- Yes --> GetNextTask[Select Next Task]
    GetNextTask --> InitRetry[Set attempts = 0]
    InitRetry --> RetryLoop{attempts < 3?}
    
    RetryLoop -- No --> CritFail((Critical Failure))
    
    RetryLoop -- Yes --> IncAttempts[attempts++]
    
    subgraph Execution [run_jules_task]
        direction TB
        Entry[Ensure Work Branch] --> CheckExisting{Active sessions already?}
        
        CheckExisting -- Yes --> UseExisting[Set resume_name]
        CheckExisting -- No --> StartNew[SDK: sessions.create]
        
        UseExisting --> WaitLoop
        StartNew --> WaitLoop[Wait Loop]
        
        WaitLoop --> Poll[SDK: sessions.get status]
        Poll --> Status{Status?}
        
        Status -- AWAITING_PLAN_APPROVAL --> Approve[SDK: sessions.approve_plan]
        Approve --> WaitWait
        
        Status -- IN_PROGRESS/PLANNING --> WaitWait[Wait 10s]
        WaitWait --> WaitLoop
        
        Status -- RUNNING --> WaitWait
        
        Status -- FAILED/ERROR --> ReturnFail[Return failure status]
        Status -- COMPLETED --> ApplyChanges[Apply Changes]
        
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
    
    IncAttempts --> Entry
    
    ReturnSuccess --> Result
    ReturnFail --> Result
    ReturnApplyFail --> Result
    
    Result{Result?} -- SUCCESS --> Push[Git Push Work Branch]
    Push --> HasTasks
    
    Result -- Others --> RetryWait[Wait 10s]
    RetryWait --> RetryLoop
```