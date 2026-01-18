---
name: jules-sdk
description: A skill for interacting with the Jules API using the jules-agent-sdk Python library.
allowed-tools: [run_command, write_to_file, read_url_content]
---

# Jules Agent SDK Skill

Use this skill to automate tasks using the Jules AI agent through its official Python SDK.

## Core Capabilities

- **Session Management**: Create, list, resumed, and wait for Jules sessions.
- **Activity Monitoring**: Track session progress and retrieve agent/user messages.
- **Plan Approval**: Automatically or manually approve generated plans.
- **Source Integration**: List and filter available code sources (GitHub repositories).

## SDK Installation

Ensure dependencies are installed:
```bash
pip install jules-agent-sdk python-dotenv
```

## Attribute Handling (CRITICAL)

The SDK returns Pydantic-like models. Use **snake_case** attributes, NOT camelCase or dictionary keys.

- ✅ `session.source_context`
- ✅ `session.update_time`
- ✅ `session.state`
- ❌ `session.sourceContext`
- ❌ `session.get("state")`

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

# Access the internal client to POST raw JSON
response = client.sessions.client.post("sessions", json=data)
session = Session.from_dict(response)
```

## Robust Polling (404 Handling)

Backend resources like activities may return transient 404s immediately after session creation. Always wrap polling in a retry loop:

```python
import time
from jules_agent_sdk.exceptions import JulesAPIError

try:
    activities = client.activities.list_all(session_id)
except JulesAPIError as e:
    if "404" in str(e):
        # Ignore transient 404 and continue polling
        pass
    else:
        raise e
```

## Resume Logic

Before creating a new session, check for active ones to avoid duplicates.

```python
# List sessions for a specific repo
resp = client.sessions.list(page_size=100)
sessions = resp.get("sessions", [])

# Filter by source and status
active_sessions = [
    s for s in sessions 
    if s.source_context and "my-repo" in s.source_context.source
    and s.state not in ["COMPLETED", "FAILED"]
]

if active_sessions:
    session_id = active_sessions[0].id
    # Resume monitoring...
```
