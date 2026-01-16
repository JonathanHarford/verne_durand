---
name: jules-api
description: Manage and interact with Jules API sessions for autonomous coding tasks. Use this skill to create sessions, monitor activities, approve plans, and communicate with the Jules AI agent.
---

# Jules API

The Jules API allows you to programmatically manage autonomous coding sessions. Jules can perform complex development tasks, from environment setup to feature implementation and verification.

## Core Concepts

- **Session**: A container for an autonomous task. Sessions track the state of the agent's work.
- **Activity**: A record of events within a session, such as plan generation, progress updates, or user messages.
- **Source**: The location of the code (e.g., a GitHub repository).
- **SourceContext**: Additional information for a source, like the starting branch.

## Authentication

All requests to the Jules API require authentication via an API key. This is typically passed in the header or as a query parameter.
In many environments, the API key is stored in the `JULES_API_KEY` environment variable.

## Common Workflows

### 1. Create a New Session

To start a new Jules task, create a session by providing a prompt and a source.

```python
import httpx
import os

API_KEY = os.environ.get("JULES_API_KEY")
BASE_URL = "https://jules.googleapis.com/v1alpha"

async def create_session(prompt: str, repo: str, branch: str = "main"):
    url = f"{BASE_URL}/sessions?key={API_KEY}"
    payload = {
        "prompt": prompt,
        "sourceContext": {
            "source": f"sources/github/{repo}",
            "githubRepoContext": {
                "startingBranch": branch
            }
        },
        "requirePlanApproval": True
    }
    async with httpx.AsyncClient() as client:
        response = await client.post(url, json=payload)
        return response.json()
```

### 2. Poll for Session Status

Monitor the session to see when Jules has generated a plan or completed a task.

```python
async def get_session(session_name: str):
    url = f"{BASE_URL}/{session_name}?key={API_KEY}"
    async with httpx.AsyncClient() as client:
        response = await client.get(url)
        return response.json()
```

### 3. List Activities

Retrieve details about the progress Jules is making.

```python
async def list_activities(session_name: str):
    url = f"{BASE_URL}/{session_name}/activities?key={API_KEY}"
    async with httpx.AsyncClient() as client:
        response = await client.get(url)
        return response.json()
```

### 4. Approve a Plan

If `requirePlanApproval` was set to true, you must approve the plan before Jules proceeds.

```python
async def approve_plan(session_name: str):
    url = f"{BASE_URL}/{session_name}:approvePlan?key={API_KEY}"
    async with httpx.AsyncClient() as client:
        response = await client.post(url)
        return response.json()
```

### 5. Send a Message

Communicate with Jules during a session to provide feedback or additional instructions.

```python
async def send_message(session_name: str, message: str):
    url = f"{BASE_URL}/{session_name}:sendMessage?key={API_KEY}"
    payload = {"message": message}
    async with httpx.AsyncClient() as client:
        response = await client.post(url, json=payload)
        return response.json()
```

## Helper Script

A command-line helper script is included to facilitate direct API interaction:

- `scripts/jules_client.py`: Provides a wrapper around `httpx` for common API operations.

Example usage:
```bash
python scripts/jules_client.py create --prompt "Fix bug in main.py" --repo "user/repo"
python scripts/jules_client.py get --session 31415926535897932384
```

## Best Practices

- **Plan Approval**: Use `requirePlanApproval: True` for complex tasks to ensure Jules' intended changes align with your goals.
- **Context Preservation**: Always specify a `startingBranch` to ensure Jules works on the correct version of the code.
- **Error Handling**: Monitor activities for `progressUpdated` events with failures to catch issues early.
- **Git Hygiene**: When Jules finishes, pull and merge the changes into your main development branch.
