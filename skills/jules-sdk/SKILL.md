---
name: jules-sdk
description: "Automates Jules AI sessions via the jules-agent-sdk Python library, handling session creation, polling, plan approval, and PR retrieval. Use when building Jules automation scripts, creating or resuming Jules sessions, polling session status, auto-approving plans, or integrating Jules API into Python workflows."
allowed-tools: "run_command, write_to_file, read_url_content"
---

# Jules Agent SDK Skill

Automate tasks using the Jules AI agent through its official Python SDK (`jules-agent-sdk`). For full API reference and data models, see [SDK_REFERENCE.md](references/SDK_REFERENCE.md).

## Workflow

1. **Install** the SDK: `pip install jules-agent-sdk python-dotenv`
2. **Initialize** the client with `JULES_API_KEY`
3. **Check for active sessions** before creating new ones (avoid duplicates)
4. **Create or resume** a session with a prompt and source repo
5. **Poll** session status, handling transient 404s gracefully
6. **Auto-approve** plans when `AWAITING_PLAN_APPROVAL` is detected
7. **Retrieve outputs** (PRs) from completed sessions

## Attribute Handling (CRITICAL)

The SDK returns Pydantic-like models. Use **snake_case** attributes, NOT camelCase or dictionary keys.

- `session.source_context` — correct
- `session.update_time` — correct
- `session.state` — correct
- `session.sourceContext` — wrong, will fail
- `session.get("state")` — wrong, not a dict

## automationMode Workaround

The high-level `client.sessions.create` method may miss the `automationMode` field. Use the internal client to send a raw request:

```python
from jules_agent_sdk.models import Session

data = {
    "prompt": "Your prompt",
    "sourceContext": {
        "source": "sources/github/owner/repo",
        "githubRepoContext": {"startingBranch": "main"}
    },
    "automationMode": "AUTO_CREATE_PR",
    "title": "Session Title",
    "requirePlanApproval": True
}

response = client.sessions.client.post("sessions", json=data)
session = Session.from_dict(response)
```

## Robust Polling (404 Handling)

Backend resources like activities may return transient 404s immediately after session creation. Always wrap polling in a retry loop:

```python
from jules_agent_sdk.exceptions import JulesAPIError

try:
    activities = client.activities.list_all(session_id)
except JulesAPIError as e:
    if "404" in str(e):
        pass  # Ignore transient 404 and continue polling
    else:
        raise e
```

## Resume Logic

Before creating a new session, check for active ones to avoid duplicates:

```python
resp = client.sessions.list(page_size=100)
sessions = resp.get("sessions", [])

active_sessions = [
    s for s in sessions
    if s.source_context and "my-repo" in s.source_context.source
    and s.state not in ["COMPLETED", "FAILED"]
]

if active_sessions:
    session_id = active_sessions[0].id
    # Resume monitoring...
```
