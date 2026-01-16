# /// script
# dependencies = [
#   "httpx",
# ]
# ///
#!/usr/bin/env python3
import argparse
import logging
import os
import re
import shutil
import subprocess
import sys
import time
from typing import List, Optional, Set, Tuple, Dict, Any
import httpx

# CONFIGURATION
DEFAULT_TIMEOUT_SEC = 600
MAX_RETRIES = 3
API_BASE_URL = "https://jules.googleapis.com/v1alpha"

class JulesAPI:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.client = httpx.Client(timeout=30.0)

    def _request(self, method: str, path: str, json_data: Optional[Dict] = None, params: Optional[Dict] = None) -> Dict:
        url = f"{API_BASE_URL}/{path}"
        if params is None:
            params = {}
        params["key"] = self.api_key
        
        resp = self.client.request(method, url, json=json_data, params=params)
        if resp.status_code >= 400:
            logging.error(f"API Error ({resp.status_code}): {resp.text}")
            resp.raise_for_status()
        return resp.json()

    def list_sessions(self, repo_filter: Optional[str] = None) -> List[Dict]:
        # The API doesn't seem to have a direct repo filter in the list sessions call in the docs,
        # but jules_mgr.bb shows it uses page size and then filters manually.
        data = self._request("GET", "sessions", params={"pageSize": 100})
        sessions = data.get("sessions", [])
        if repo_filter:
            # Match repo slug in sourceContext.source
            sessions = [s for s in sessions if repo_filter in s.get("sourceContext", {}).get("source", "")]
        return sessions

    def get_session(self, session_id: str) -> Dict:
        # Check if session_id is a full name like "sessions/123" or just "123"
        path = session_id if "/" in session_id else f"sessions/{session_id}"
        return self._request("GET", path)

    def create_session(self, prompt: str, repo: str, branch: str, title: Optional[str] = None) -> Dict:
        payload = {
            "prompt": prompt,
            "sourceContext": {
                "source": f"sources/github/{repo}",
                "githubRepoContext": {
                    "startingBranch": branch
                }
            },
            "automationMode": "AUTO_CREATE_PR", # Standard way to get changes back via API
            "title": title or f"Ralph Task: {prompt[:30]}..."
        }
        return self._request("POST", "sessions", json_data=payload)

    def list_activities(self, session_id: str) -> List[Dict]:
        path = session_id if "/" in session_id else f"sessions/{session_id}"
        data = self._request("GET", f"{path}/activities", params={"pageSize": 100})
        return data.get("activities", [])

def configure_logging(verbose: bool = False) -> None:
    """Configures the logging module."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="[%(asctime)s] [%(levelname)s] %(message)s",
        datefmt="%H:%M:%S",
        stream=sys.stderr
    )

# --- GIT HELPERS ---

def get_current_branch() -> Optional[str]:
    """Returns the name of the current git branch, or None if failed."""
    result = subprocess.run(
        ["git", "rev-parse", "--abbrev-ref", "HEAD"], capture_output=True, text=True
    )
    if result.returncode != 0:
        return None
    return result.stdout.strip()

def run_git_cmd(args: List[str], check: bool = True) -> subprocess.CompletedProcess:
    """Runs a git command with the given arguments."""
    return subprocess.run(
        ["git"] + args, check=check, capture_output=True, text=True
    )

def ensure_git_repo() -> None:
    """Verifies that the current directory is a git repository."""
    ret = subprocess.run(["git", "rev-parse", "--is-inside-work-tree"], capture_output=True)
    if ret.returncode != 0:
        logging.error("Current directory is not a git repository.")
        sys.exit(1)

def ensure_repo_initialized() -> None:
    """Ensures the repo has at least one commit."""
    ensure_git_repo()
    ret = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True)
    if ret.returncode != 0:
        logging.info("[GIT] Creating initial empty commit.")
        subprocess.run(["git", "commit", "--allow-empty", "-m", "Initial commit"], check=True)

def ensure_work_branch(target_branch: str) -> None:
    """Switches to the target branch, creating it if it doesn't exist."""
    ensure_repo_initialized()
    current = get_current_branch()
    if current == target_branch:
        return
    logging.info(f"[GIT] Switching to '{target_branch}'")
    ret = subprocess.run(["git", "checkout", target_branch], capture_output=True)
    if ret.returncode != 0:
        subprocess.run(["git", "checkout", "-b", target_branch], check=True)

def push_changes(branch: str) -> None:
    """Pushes the branch to origin if it exists."""
    try:
        ret = run_git_cmd(["remote"], check=False)
        if "origin" in ret.stdout:
            logging.info(f"[GIT] Pushing '{branch}' to origin...")
            run_git_cmd(["push", "-u", "origin", branch])
    except subprocess.CalledProcessError as e:
        logging.error(f"Failed to push: {e.stderr}")

def get_repo_slug() -> Optional[str]:
    """Extracts 'owner/repo' from the git remote."""
    try:
        ret = run_git_cmd(["remote", "get-url", "origin"], check=False)
        if ret.returncode != 0: return None
        url = ret.stdout.strip()
        match = re.search(r"github\.com[:/]([^/]+/[^/.]+)(?:\.git)?", url)
        if match: return match.group(1)
    except Exception: pass
    return None

# --- JULES INTERACTION ---

def wait_for_session(api: JulesAPI, session_id: str, timeout: int) -> Tuple[bool, str, Optional[Dict]]:
    """Polls session status until completion or timeout."""
    start_time = time.time()
    logging.info(f"Waiting for session {session_id}...")
    
    while (time.time() - start_time) < timeout:
        try:
            session = api.get_session(session_id)
            state = session.get("state", "UNKNOWN")
            
            if state in ["COMPLETED", "SUCCEEDED"]:
                return True, "COMPLETED", session
            if state in ["FAILED", "CANCELLED", "ERROR"]:
                return False, state, session
            
            # Progress update?
            logging.debug(f"Session {session_id} state: {state}")
            time.sleep(10)
        except Exception as e:
            logging.warning(f"Error polling session: {e}")
            time.sleep(5)

    return False, "TIMEOUT", None

def apply_jules_changes(session: Dict, work_branch: str) -> bool:
    """
    Applies the changes from Jules. 
    If automationMode was AUTO_CREATE_PR, we fetch the branch.
    Otherwise, we'd have to parse patches (not yet implemented).
    """
    outputs = session.get("outputs", [])
    pr_data = next((o.get("pullRequest") for o in outputs if "pullRequest" in o), None)
    
    if not pr_data:
        logging.error("No Pull Request output found in session. Cannot apply changes automatically yet.")
        return False

    pr_url = pr_data.get("url", "")
    # PR URL format is usually https://github.com/owner/repo/pull/123
    # We need the branch name. Sometimes it's in the description or we can fetch the PR ref.
    # Standard Jules behavior for AUTO_CREATE_PR is to push to a branch named like 'jules-session-ID'
    session_id = session.get("id")
    # Try to find branch name in description or assume standard format
    jules_branch = f"jules-{session_id}"
    
    logging.info(f"[GIT] Fetching changes from Jules branch '{jules_branch}'...")
    try:
        # Fetch all branches from origin
        run_git_cmd(["fetch", "origin"])
        
        # Check if jules_branch exists on remote
        ret = run_git_cmd(["branch", "-r"], check=False)
        remote_branch = f"origin/{jules_branch}"
        if remote_branch not in ret.stdout:
            # Maybe a different naming scheme? Let's check branches containing the session ID
            match = re.search(f"origin/(.*{session_id}.*)", ret.stdout)
            if match:
                remote_branch = match.group(0).strip()
                logging.info(f"[GIT] Found alternative remote branch: {remote_branch}")
            else:
                logging.error(f"Could not find remote branch for session {session_id}")
                return False

        # Merge remote branch into current work_branch
        logging.info(f"[GIT] Merging {remote_branch} into {work_branch}...")
        run_git_cmd(["merge", "--no-edit", remote_branch])
        return True
    except subprocess.CalledProcessError as e:
        logging.error(f"Git merge failed: {e.stderr}")
        return False

def run_jules_task(
    api: JulesAPI,
    task: str,
    project_path: str,
    timeout: int,
    work_branch: str,
    plan_path: str
) -> Tuple[bool, str]:
    repo_slug = get_repo_slug()
    if not repo_slug:
        logging.error("Could not determine GitHub repo slug from 'origin' remote.")
        return False, "NO_REPO_SLUG"

    # 1. Check for existing active sessions (Resume logic)
    sessions = api.list_sessions(repo_filter=repo_slug)
    active_sessions = [s for s in sessions if s.get("state") not in ["COMPLETED", "FAILED", "CANCELLED", "ERROR"]]
    
    session_id = None
    if active_sessions:
        session_id = active_sessions[0]["id"]
        logging.info(f"Resuming existing session: {session_id}")
    else:
        # 2. Start Session
        # Prompt includes marking task as finished
        full_prompt = (
            f"{task}\n\n"
            f"Use your best judgment, and ask absolutely no questions.\n\n"
            f"As your final step, update the '{plan_path}' file to mark this task as completed "
            f"by changing '[ ] {task}' to '[x] {task}'. If you inadvertently completed any subsequent tasks, mark them off as well."
        )
        
        logging.info(f"Starting new Jules session for: '{task}'")
        session_resp = api.create_session(full_prompt, repo_slug, work_branch)
        session_id = session_resp["id"]
        logging.info(f"Session started: {session_id}")

    # 3. Wait
    success, status, session = wait_for_session(api, session_id, timeout)
    if not success:
        return False, status

    # 4. Apply changes
    if session and apply_jules_changes(session, work_branch):
        return True, "SUCCESS"
    else:
        return False, "APPLY_FAILED"

# --- CORE LOGIC ---

def parse_plan(plan_path: str) -> Tuple[List[Tuple[int, str]], int]:
    if not os.path.exists(plan_path):
        logging.error(f"Plan file not found: {os.path.abspath(plan_path)}")
        sys.exit(1)

    with open(plan_path, "r") as f:
        lines = f.readlines()

    pending_tasks = []
    all_task_count = 0
    for i, line in enumerate(lines):
        if re.match(r"^\s*[-*]\s*\[[ x]\]\s+(.*)", line):
            all_task_count += 1
            match = re.match(r"^\s*[-*]\s*\[ \]\s+(.*)", line)
            if match:
                pending_tasks.append((all_task_count, match.group(1).strip()))

    return pending_tasks, all_task_count

def main() -> None:
    parser = argparse.ArgumentParser(description="Ralph Wiggum: Autonomous Jules API Harness")
    parser.add_argument("--plan", required=True, help="Path to markdown checklist file")
    parser.add_argument("--project", default=".", help="Root path of the project")
    parser.add_argument("--branch", default="ralph-wiggum", help="The persistent work branch")
    parser.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT_SEC, help="Task timeout in seconds")
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable verbose logging")

    args = parser.parse_args()
    configure_logging(verbose=args.verbose)

    api_key = os.environ.get("JULES_API_KEY")
    if not api_key:
        logging.error("JULES_API_KEY environment variable is missing.")
        sys.exit(1)

    api = JulesAPI(api_key)
    
    abs_project_path = os.path.abspath(args.project)
    if not os.path.exists(abs_project_path):
        logging.error(f"Project path does not exist: {abs_project_path}")
        sys.exit(1)
    os.chdir(abs_project_path)

    # Initialize
    ensure_work_branch(args.branch)
    push_changes(args.branch)

    tasks, total_count = parse_plan(args.plan)
    if not tasks:
        logging.info("No tasks to perform.")
        sys.exit(0)

    for i, (abs_idx, task) in enumerate(tasks):
        logging.info(f"--- Task {abs_idx}/{total_count}: {task} ---")
        
        attempts = 0
        success = False
        while attempts < MAX_RETRIES and not success:
            attempts += 1
            task_success, status = run_jules_task(api, task, ".", args.timeout, args.branch, args.plan)
            
            if task_success:
                push_changes(args.branch)
                success = True
                logging.info(f"Task completed.")
            else:
                logging.warning(f"Task failed (Attempt {attempts}). Reason: {status}")
                if attempts < MAX_RETRIES: time.sleep(10)

        if not success:
            logging.error(f"CRITICAL FAILURE: Task '{task}' failed after {MAX_RETRIES} attempts.")
            sys.exit(1)

    logging.info("All tasks completed.")

if __name__ == "__main__":
    main()
