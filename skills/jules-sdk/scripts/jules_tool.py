#!/usr/bin/env -S uv run --script
# /// script
# dependencies = [
#   "jules-agent-sdk",
#   "python-dotenv",
# ]
# ///

import os
import argparse
from dotenv import load_dotenv
from jules_agent_sdk import JulesClient

def main():
    parser = argparse.ArgumentParser(description="Jules SDK Reference Tool")
    parser.add_argument("--action", choices=["list-sessions", "list-sources"], default="list-sessions")
    args = parser.parse_args()

    load_dotenv()
    api_key = os.environ.get("JULES_API_KEY")
    if not api_key:
        print("Error: JULES_API_KEY not found in environment or .env file.")
        return

    with JulesClient(api_key=api_key) as client:
        if args.action == "list-sessions":
            resp = client.sessions.list(page_size=10)
            sessions = resp.get("sessions", [])
            print(f"Found {len(sessions)} recent sessions:")
            for s in sessions:
                print(f"- {s.id}: {s.state} (Updated: {s.update_time})")
        
        elif args.action == "list-sources":
            sources = client.sources.list_all()
            print(f"Found {len(sources)} sources:")
            for src in sources:
                print(f"- {src.id}: {src.name}")

if __name__ == "__main__":
    main()
