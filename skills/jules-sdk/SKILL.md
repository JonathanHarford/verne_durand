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

## Usage Patterns

### Basic Session Flow

Always load environment variables and use the `with` statement for clean resource management.

```python
import os
from dotenv import load_dotenv
from jules_agent_sdk import JulesClient

load_dotenv()

with JulesClient(api_key=os.environ["JULES_API_KEY"]) as client:
    # Create session
    session = client.sessions.create(
        prompt="Fix the bug in auth.py",
        source="sources/github/owner/repo",
        starting_branch="main",
        require_plan_approval=True
    )
    
    # Wait for completion
    final_session = client.sessions.wait_for_completion(session.id)
    print(f"Final state: {final_session.state}")
```

### Resume Logic

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

### Handling Attributes (CRITICAL)

The SDK returns Pydantic-like models. Use **snake_case** attributes, NOT camelCase or dictionary keys.

- ✅ `session.source_context`
- ✅ `session.update_time`
- ✅ `session.state`
- ❌ `session.sourceContext`
- ❌ `session.get("state")`

## Error Handling

Handle specific Jules exceptions for better resilience:

```python
from jules_agent_sdk.exceptions import JulesAPIError, JulesAuthenticationError

try:
    client.sessions.create(...)
except JulesAuthenticationError:
    # Fix API key
except JulesAPIError as e:
    # Handle API specific errors
```
