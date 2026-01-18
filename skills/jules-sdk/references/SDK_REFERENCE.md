# Jules Agent SDK

A user-friendly Python SDK for the Jules API. This SDK provides a clean, Pythonic interface for interacting with Jules sessions, activities, and sources.

## Features

- 🚀 **Simple and intuitive API** - Easy-to-use client with straightforward methods
- 📦 **Modular design** - Organized into logical modules (sessions, activities, sources)
- 🔄 **Async support** - Full support for async/await with `aiohttp`
- 🛡️ **Type hints** - Complete type annotations for better IDE support
- ✅ **Error handling** - Clear, descriptive exceptions for different error cases
- 📖 **Well documented** - Comprehensive docstrings and examples

## Installation

Install the package via pip:

```bash
pip install jules-agent-sdk
```

For development with testing dependencies:

```bash
pip install jules-agent-sdk[dev]
```

## Quick Start

### Basic Usage (Synchronous)

```python
from jules_agent_sdk import JulesClient

# Initialize the client
client = JulesClient(api_key="your-api-key")

# Create a new session
session = client.sessions.create(
    prompt="Fix the authentication bug in the login module",
    source="sources/my-github-repo-id",
    starting_branch="main"
)

print(f"Session created: {session.id}")
print(f"Session state: {session.state}")

# Wait for the session to complete
completed_session = client.sessions.wait_for_completion(session.id)
print(f"Final state: {completed_session.state}")

# List all activities for the session
result = client.activities.list_all(session.id)
for activity in result:
    print(f"Activity: {activity.description}")

# Don't forget to close the client when done
client.close()
```

### Using Context Manager

```python
from jules_agent_sdk import JulesClient

# Automatically handles cleanup
with JulesClient(api_key="your-api-key") as client:
    session = client.sessions.create(
        prompt="Add user authentication",
        source="sources/repo-id",
        starting_branch="develop"
    )
    print(f"Session: {session.id}")
```

### Async Usage

```python
import asyncio
from jules_agent_sdk import AsyncJulesClient

async def main():
    async with AsyncJulesClient(api_key="your-api-key") as client:
        # Create session
        session = await client.sessions.create(
            prompt="Refactor the database layer",
            source="sources/my-repo",
            starting_branch="main"
        )

        # Wait for completion
        completed = await client.sessions.wait_for_completion(session.id)

        # Get all activities
        activities = await client.activities.list_all(session.id)
        for activity in activities:
            print(f"Activity: {activity.description}")

asyncio.run(main())
```

## API Reference

### Client Initialization

```python
from jules_agent_sdk import JulesClient, AsyncJulesClient

# Synchronous client
client = JulesClient(api_key="your-api-key")

# Async client
async_client = AsyncJulesClient(api_key="your-api-key")

# Custom base URL (optional)
client = JulesClient(
    api_key="your-api-key",
    base_url="https://custom-api-endpoint.com/v1alpha"
)
```

### Sessions API

#### Create a Session

```python
session = client.sessions.create(
    prompt="Your task description",
    source="sources/source-id",
    starting_branch="main",  # Optional, for GitHub repos
    title="Optional Session Title",  # Optional
    require_plan_approval=False  # Optional, defaults to False
)
```

#### Get a Session

```python
session = client.sessions.get("session-id")
print(session.state)  # SessionState enum
print(session.url)    # Web UI URL
```

#### List Sessions

```python
# List with pagination
result = client.sessions.list(page_size=10)
for session in result['sessions']:
    print(session.id, session.state)

# Get next page
if result['nextPageToken']:
    next_result = client.sessions.list(page_token=result['nextPageToken'])
```

#### Approve a Plan

```python
client.sessions.approve_plan("session-id")
```

#### Send a Message

```python
client.sessions.send_message(
    session_id="session-id",
    prompt="Please also add unit tests"
)
```

#### Wait for Completion

```python
# Poll until session completes or fails
final_session = client.sessions.wait_for_completion(
    session_id="session-id",
    poll_interval=5,  # seconds between polls
    timeout=3600      # optional timeout in seconds
)
```

### Activities API

#### Get an Activity

```python
activity = client.activities.get(
    session_id="session-id",
    activity_id="activity-id"
)
```

#### List Activities

```python
# With pagination
result = client.activities.list(
    session_id="session-id",
    page_size=20
)

for activity in result['activities']:
    print(activity.description)

    # Check activity type
    if activity.agent_messaged:
        print(f"Agent message: {activity.agent_messaged['agentMessage']}")
    elif activity.plan_generated:
        plan = activity.plan_generated['plan']
        print(f"Plan steps: {len(plan['steps'])}")
```

#### List All Activities

```python
# Automatically handles pagination
all_activities = client.activities.list_all("session-id")
print(f"Total activities: {len(all_activities)}")
```

### Sources API

#### Get a Source

```python
source = client.sources.get("source-id")

if source.github_repo:
    print(f"Repo: {source.github_repo.owner}/{source.github_repo.repo}")
    print(f"Default branch: {source.github_repo.default_branch.display_name}")
```

#### List Sources

```python
# With optional filter
result = client.sources.list(
    filter_str="type:github",  # Optional filter
    page_size=10
)

for source in result['sources']:
    print(source.id)
```

#### List All Sources

```python
all_sources = client.sources.list_all()
github_repos = [s for s in all_sources if s.github_repo]
print(f"Total GitHub sources: {len(github_repos)}")
```

## Data Models

All API responses are returned as strongly-typed dataclasses:

### Session

```python
@dataclass
class Session:
    name: str
    id: str
    prompt: str
    source_context: SourceContext
    title: str
    state: SessionState  # Enum
    url: str
    create_time: str
    update_time: str
    outputs: List[SessionOutput]
    require_plan_approval: bool
```

### SessionState Enum

```python
class SessionState(str, Enum):
    STATE_UNSPECIFIED = "STATE_UNSPECIFIED"
    QUEUED = "QUEUED"
    PLANNING = "PLANNING"
    AWAITING_PLAN_APPROVAL = "AWAITING_PLAN_APPROVAL"
    AWAITING_USER_FEEDBACK = "AWAITING_USER_FEEDBACK"
    IN_PROGRESS = "IN_PROGRESS"
    PAUSED = "PAUSED"
    FAILED = "FAILED"
    COMPLETED = "COMPLETED"
```

### Activity

```python
@dataclass
class Activity:
    name: str
    id: str
    description: str
    create_time: str
    originator: str
    artifacts: List[Artifact]
    # One of these will be set:
    agent_messaged: Optional[Dict]
    user_messaged: Optional[Dict]
    plan_generated: Optional[Dict]
    plan_approved: Optional[Dict]
    progress_updated: Optional[Dict]
    session_completed: Optional[Dict]
    session_failed: Optional[Dict]
```

### Source

```python
@dataclass
class Source:
    name: str
    id: str
    github_repo: Optional[GitHubRepo]
```

## Error Handling

The SDK provides specific exception types for different error cases:

```python
from jules_agent_sdk.exceptions import (
    JulesAPIError,           # Base exception
    JulesAuthenticationError,  # 401 errors
    JulesNotFoundError,        # 404 errors
    JulesValidationError,      # 400 errors
    JulesRateLimitError,       # 429 errors
)

try:
    session = client.sessions.create(
        prompt="Task",
        source="sources/invalid"
    )
except JulesAuthenticationError:
    print("Invalid API key")
except JulesValidationError as e:
    print(f"Validation error: {e.message}")
except JulesAPIError as e:
    print(f"API error: {e.status_code} - {e.message}")
```

## Advanced Examples

### Monitor Session Progress

```python
import time
from jules_agent_sdk import JulesClient
from jules_agent_sdk.models import SessionState

client = JulesClient(api_key="your-api-key")

# Create session
session = client.sessions.create(
    prompt="Implement new feature",
    source="sources/repo-id",
    starting_branch="main"
)

# Poll and display progress
while True:
    session = client.sessions.get(session.id)
    print(f"State: {session.state}")

    if session.state in [SessionState.COMPLETED, SessionState.FAILED]:
        break

    # Get latest activities
    activities = client.activities.list(session.id, page_size=5)
    for activity in activities['activities']:
        if activity.progress_updated:
            update = activity.progress_updated
            print(f"Progress: {update['title']} - {update['description']}")

    time.sleep(5)
```

### Handle Plan Approval

```python
from jules_agent_sdk import JulesClient
from jules_agent_sdk.models import SessionState

client = JulesClient(api_key="your-api-key")

session = client.sessions.create(
    prompt="Complex refactoring task",
    source="sources/repo-id",
    require_plan_approval=True  # Require manual approval
)

# Wait for plan to be generated
while True:
    session = client.sessions.get(session.id)

    if session.state == SessionState.AWAITING_PLAN_APPROVAL:
        # Get the plan from activities
        activities = client.activities.list_all(session.id)
        for activity in activities:
            if activity.plan_generated:
                plan = activity.plan_generated['plan']
                print("Generated Plan:")
                for step in plan['steps']:
                    print(f"  {step['index']}: {step['title']}")

                # Approve the plan
                client.sessions.approve_plan(session.id)
                print("Plan approved!")
                break
        break

    time.sleep(2)
```

### Async Concurrent Operations

```python
import asyncio
from jules_agent_sdk import AsyncJulesClient

async def create_and_monitor_session(client, prompt, source):
    """Create a session and return when complete."""
    session = await client.sessions.create(
        prompt=prompt,
        source=source,
        starting_branch="main"
    )
    completed = await client.sessions.wait_for_completion(session.id)
    return completed

async def main():
    async with AsyncJulesClient(api_key="your-api-key") as client:
        # Run multiple sessions concurrently
        tasks = [
            create_and_monitor_session(client, "Fix bug A", "sources/repo1"),
            create_and_monitor_session(client, "Fix bug B", "sources/repo2"),
            create_and_monitor_session(client, "Add feature C", "sources/repo3"),
        ]

        results = await asyncio.gather(*tasks)

        for i, session in enumerate(results):
            print(f"Session {i+1}: {session.state}")

asyncio.run(main())
```

## Development

### Running Tests

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Run with coverage
pytest --cov=jules_agent_sdk --cov-report=html
```

### Code Quality

```bash
# Format code
black src tests

# Type checking
mypy src

# Linting
flake8 src tests
```

## License

MIT License - see LICENSE file for details.

## Support

- **Documentation**: [Jules API Documentation](https://jules.googleapis.com/docs)
- **Issues**: [GitHub Issues](https://github.com/jules/jules-agent-sdk/issues)
- **Email**: support@jules.ai

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request
