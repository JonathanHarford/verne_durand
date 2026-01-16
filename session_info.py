#!/usr/bin/env -S uv run --script
# /// script
# dependencies = [
#   "jules-agent-sdk",
#   "python-dotenv",
# ]
# ///

import argparse
import os
import sys
import json
from datetime import datetime
from typing import Any, Dict, List, Optional
from jules_agent_sdk import JulesClient
from jules_agent_sdk.exceptions import JulesAPIError
from dotenv import load_dotenv

def format_timestamp(ts: Optional[str]) -> str:
    if not ts:
        return "N/A"
    try:
        # Jules API uses RFC 3339
        dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
        return dt.strftime("%Y-%m-%d %H:%M:%S UTC")
    except Exception:
        return ts

def wrap_text(text: str, width: int = 80) -> List[str]:
    if not text:
        return [""]
    words = text.split()
    lines = []
    current_line = []
    current_length = 0
    for word in words:
        if current_length + len(word) + 1 <= width:
            current_line.append(word)
            current_length += len(word) + 1
        else:
            lines.append(" ".join(current_line))
            current_line = [word]
            current_length = len(word)
    if current_line:
        lines.append(" ".join(current_line))
    return lines

def print_section(title: str):
    print()
    print(f"╔{'═' * (len(title) + 2)}╗")
    print(f"║ {title} ║")
    print(f"╚{'═' * (len(title) + 2)}╝")
    print()

def print_field(label: str, value: Any, indent: int = 0, wrap_width: int = 80):
    padding = " " * indent
    label_str = f"{padding}{label}: "
    if isinstance(value, str):
        first_line_width = wrap_width - len(label_str)
        lines = wrap_text(value, wrap_width)
        if not lines:
            print(f"{label_str}")
            return
        
        first_line = lines[0]
        if len(first_line) <= first_line_width:
            print(f"{label_str}{first_line}")
        else:
            print(f"{padding}{label}:")
            print(f"{padding}  {first_line}")
        
        for line in lines[1:]:
            print(f"{padding}  {line}")
    else:
        print(f"{label_str}{value}")

def print_session_report(client: JulesClient, session_id: str):
    try:
        # Handle if user provides 'sessions/ID' or just 'ID'
        resource_name = session_id if "/" in session_id else f"sessions/{session_id}"
        
        session = client.sessions.get(resource_name)
        activities = client.activities.list_all(resource_name)
        
        print("\n" + "═" * 70)
        print(f"  JULES SESSION REPORT: {session_id}")
        print("═" * 70)

        # Basic Info
        print_section("BASIC INFORMATION")
        print_field("Session ID", getattr(session, "id", "N/A"))
        print_field("State", getattr(session, "state", "N/A"))
        print_field("Created", format_timestamp(getattr(session, "create_time", None)))
        print_field("Updated", format_timestamp(getattr(session, "update_time", None)))
        print_field("URL", getattr(session, "url", "N/A"))

        # Source Context
        source_context = getattr(session, "source_context", None)
        if source_context:
            print_section("SOURCE CONTEXT")
            print_field("Source", getattr(source_context, "source", "N/A"))
            github_ctx = getattr(source_context, "github_repo_context", None)
            if github_ctx:
                print_field("Starting Branch", getattr(github_ctx, "starting_branch", "N/A"))

        # Initial Prompt
        prompt = getattr(session, "prompt", None)
        if prompt:
            print_section("INITIAL PROMPT")
            for line in wrap_text(prompt, 75):
                print(f"  {line}")

        # Outputs
        outputs = getattr(session, "outputs", [])
        if outputs:
            print_section("OUTPUTS")
            for output in outputs:
                # Determine if output is dict or object
                pr = None
                if isinstance(output, dict):
                    pr = output.get("pullRequest")
                else:
                    pr = getattr(output, "pull_request", getattr(output, "pullRequest", None))
                
                if pr:
                    if isinstance(pr, dict):
                        print_field("Pull Request URL", pr.get("url", "N/A"))
                        desc = pr.get("description")
                    else:
                        print_field("Pull Request URL", getattr(pr, "url", "N/A"))
                        desc = getattr(pr, "description", None)
                    
                    if desc:
                        print("\n  PR Description:")
                        for line in wrap_text(desc, 73):
                            print(f"    {line}")

        # Activities
        if activities:
            print_section("ACTIVITIES")
            # Activities in SDK list_all should be chronological
            for act in reversed(activities):
                # Extract act type (e.g. 'progressUpdated', 'agentMessaged')
                # In SDK, activity is usually a dict or object
                act_data = act if isinstance(act, dict) else act.__dict__
                
                # Filter out standard fields to find the union type field
                type_fields = [k for k in act_data.keys() if k not in ['id', 'name', 'createTime', 'originator', 'description', 'artifacts']]
                act_type = type_fields[0] if type_fields else "Activity"
                
                # Format type for display
                display_type = act_type.replace("([A-Z])", " $1").capitalize()
                timestamp = format_timestamp(act_data.get("create_time") if isinstance(act_data, dict) else getattr(act, "create_time", None))
                
                print(f"  [{timestamp}] {display_type}")
                
                details = None
                if act_type == "progressUpdated" or act_type == "progress_updated":
                    prog = act_data.get("progress_updated") if isinstance(act_data, dict) else getattr(act, "progress_updated", None)
                    if prog:
                        details = (prog.get("description") or prog.get("title")) if isinstance(prog, dict) else (getattr(prog, "description", None) or getattr(prog, "title", None))
                elif act_type == "agentMessaged" or act_type == "agent_messaged":
                    msg = act_data.get("agent_messaged") if isinstance(act_data, dict) else getattr(act, "agent_messaged", None)
                    if msg:
                        details = msg.get("agent_message") if isinstance(msg, dict) else getattr(msg, "agent_message", None)
                elif act_type == "userMessaged" or act_type == "user_messaged":
                    msg = act_data.get("user_messaged") if isinstance(act_data, dict) else getattr(act, "user_messaged", None)
                    if msg:
                        details = msg.get("user_message") if isinstance(msg, dict) else getattr(msg, "user_message", None)
                
                if details:
                    preview = (details[:97] + "...") if len(details) > 100 else details
                    print(f"    → {preview.replace('\n', ' ')}")

    except JulesAPIError as e:
        print(f"\n❌ API Error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)

def main():
    parser = argparse.ArgumentParser(description="Jules Session Inspector")
    parser.add_argument("session_id", help="Session ID or Resource Name")
    
    args = parser.parse_args()
    
    load_dotenv()
    api_key = os.environ.get("JULES_API_KEY")
    if not api_key:
        print("Error: JULES_API_KEY environment variable is missing.")
        sys.exit(1)
        
    client = JulesClient(api_key=api_key)
    try:
        print_session_report(client, args.session_id)
    finally:
        client.close()

if __name__ == "__main__":
    main()
