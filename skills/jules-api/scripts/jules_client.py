import httpx
import os
import asyncio
import json
import argparse
from typing import Optional, Dict, Any

class JulesAPIClient:
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.environ.get("JULES_API_KEY")
        if not self.api_key:
            raise ValueError("JULES_API_KEY must be provided or set in environment.")
        self.base_url = "https://jules.googleapis.com/v1alpha"

    async def _request(self, method: str, endpoint: str, json_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        url = f"{self.base_url}/{endpoint}"
        params = {"key": self.api_key}
        async with httpx.AsyncClient() as client:
            response = await client.request(method, url, params=params, json=json_data)
            response.raise_for_status()
            return response.json()

    async def create_session(self, prompt: str, repo: str, branch: str = "main", require_approval: bool = True) -> Dict[str, Any]:
        payload = {
            "prompt": prompt,
            "sourceContext": {
                "source": f"sources/github/{repo}",
                "githubRepoContext": {
                    "startingBranch": branch
                }
            },
            "requirePlanApproval": require_approval
        }
        return await self._request("POST", "sessions", payload)

    async def get_session(self, session_id: str) -> Dict[str, Any]:
        return await self._request("GET", f"sessions/{session_id}")

    async def list_activities(self, session_id: str) -> Dict[str, Any]:
        return await self._request("GET", f"sessions/{session_id}/activities")

    async def approve_plan(self, session_id: str) -> Dict[str, Any]:
        return await self._request("POST", f"sessions/{session_id}:approvePlan")

    async def send_message(self, session_id: str, message: str) -> Dict[str, Any]:
        payload = {"message": message}
        return await self._request("POST", f"sessions/{session_id}:sendMessage", payload)

async def main():
    parser = argparse.ArgumentParser(description="Simple Jules API Client")
    parser.add_argument("command", choices=["create", "get", "list", "approve", "send"])
    parser.add_argument("--session", help="Session ID")
    parser.add_argument("--prompt", help="Prompt for creation")
    parser.add_argument("--repo", help="Repo slug (owner/repo)")
    parser.add_argument("--branch", default="main", help="Starting branch")
    parser.add_argument("--message", help="Message to send")

    args = parser.parse_args()
    client = JulesAPIClient()

    try:
        if args.command == "create":
            if not args.prompt or not args.repo:
                print("Error: --prompt and --repo are required for 'create'")
                return
            result = await client.create_session(args.prompt, args.repo, args.branch)
        elif args.command == "get":
            if not args.session:
                print("Error: --session is required")
                return
            result = await client.get_session(args.session)
        elif args.command == "list":
            if not args.session:
                print("Error: --session is required")
                return
            result = await client.list_activities(args.session)
        elif args.command == "approve":
            if not args.session:
                print("Error: --session is required")
                return
            result = await client.approve_plan(args.session)
        elif args.command == "send":
            if not args.session or not args.message:
                print("Error: --session and --message are required")
                return
            result = await client.send_message(args.session, args.message)
        
        print(json.dumps(result, indent=2))
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(main())
