#!/usr/bin/env -S uv run --script
# /// script
# dependencies = [
#   "jules-agent-sdk",
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
import jules_sdk_patch
jules_sdk_patch.apply_patch()

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
        print_field("Created", format_timestamp(getattr(session, "createTime", None)))
        print_field("Updated", format_timestamp(getattr(session, "updateTime", None)))
        print_field("URL", getattr(session, "url", "N/A"))

        # Source Context
        source_context = getattr(session, "sourceContext", {})
        if source_context:
            print_section("SOURCE CONTEXT")
            print_field("Source", source_context.get("source", "N/A"))
            github_ctx = source_context.get("githubRepoContext", {})
            if github_ctx:
                print_field("Starting Branch", github_ctx.get("startingBranch", "N/A"))

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
                pr = output.get("pullRequest")
                if pr:
                    print_field("Pull Request URL", pr.get("url", "N/A"))
                    desc = pr.get("description")
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
                timestamp = format_timestamp(act_data.get("createTime"))
                
                print(f"  [{timestamp}] {display_type}")
                
                details = None
                if act_type == "progressUpdated":
                    details = act_data.get("progressUpdated", {}).get("description") or act_data.get("progressUpdated", {}).get("title")
                elif act_type == "agentMessaged":
                    details = act_data.get("agentMessaged", {}).get("agentMessage")
                elif act_type == "userMessaged":
                    details = act_data.get("userMessaged", {}).get("userMessage")
                
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
