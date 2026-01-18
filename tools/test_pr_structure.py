#!/usr/bin/env -S uv run --script
# /// script
# dependencies = [
#   "jules-agent-sdk",
#   "python-dotenv",
# ]
# ///

import os
import sys
import json
from dotenv import load_dotenv
from jules_agent_sdk import JulesClient

load_dotenv()
api_key = os.environ.get("JULES_API_KEY")
if not api_key:
    print("Error: JULES_API_KEY environment variable is missing.")
    sys.exit(1)

client = JulesClient(api_key=api_key)

# List recent sessions
response = client.sessions.list(page_size=10)
sessions = response.get("sessions", [])

print("Looking for sessions with outputs...\n")

for session in sessions:
    outputs = getattr(session, "outputs", [])
    if not outputs:
        continue
        
    print(f"Session: {session.id}")
    print(f"Session Name: {session.name}")
    print(f"Number of Outputs: {len(outputs)}\n")
    
    for i, output in enumerate(outputs):
        print(f"Output #{i+1}:")
        print(f"  Type: {type(output)}")
        
        # Check all attributes
        if hasattr(output, '__dict__'):
            print(f"  Attributes: {list(output.__dict__.keys())}")
            print(f"  Full dict: {json.dumps(output.__dict__, indent=4, default=str)}")
        elif isinstance(output, dict):
            print(f"  Dict keys: {list(output.keys())}")
            print(f"  Full dict: {json.dumps(output, indent=4, default=str)}")
        
        print()
    
    print("="*70)
    print()
    
    # Only show first 3 sessions with outputs
    if sessions.index(session) >= 2:
        break

print("\nDone")
client.close()
