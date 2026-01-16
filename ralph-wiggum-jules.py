#!/usr/bin/env -S uv run --script
# /// script
# dependencies = [
#   "httpx",
#   "jules-agent-sdk",
#   "python-dotenv",
# ]
# ///

import argparse
import logging
import os
import re
import subprocess
import sys
import time
from datetime import datetime, timezone
from typing import List, Optional, Tuple, Dict, Any
from jules_agent_sdk import JulesClient
from jules_agent_sdk.exceptions import JulesAPIError
from dotenv import load_dotenv

# CONFIGURATION
DEFAULT_TIMEOUT_SEC = 600
MAX_RETRIES = 3
STALE_THRESHOLD_SEC = 1200 # 20 minutes

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
    
    # Check if branch exists
    ret = subprocess.run(["git", "show-ref", "--verify", f"refs/heads/{target_branch}"], capture_output=True)
    if ret.returncode == 0:
        logging.info(f"[GIT] Switching to existing branch '{target_branch}'")
        subprocess.run(["git", "checkout", target_branch], check=True)
    else:
        logging.info(f"[GIT] Creating and switching to branch '{target_branch}'")
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

# --- UTILS ---

def parse_api_timestamp(ts: str) -> datetime:
    """Parses RFC 3339 timestamp from API."""
    return datetime.fromisoformat(ts.replace("Z", "+00:00"))

def is_recent(ts_str: Optional[str], threshold_sec: int) -> bool:
    """Checks if a timestamp string is within the threshold from now."""
    if not ts_str:
        return False
    try:
        ts = parse_api_timestamp(ts_str)
        now = datetime.now(timezone.utc)
        return (now - ts).total_seconds() < threshold_sec
    except Exception:
        return False

# --- JULES INTERACTION ---

def wait_for_session(client: JulesClient, session_name: str, timeout: int) -> Tuple[bool, str, Optional[Any]]:
    """Polls session status until completion or timeout."""
    logging.info(f"Waiting for session {session_name}...")
    
    try:
        start_time = time.time()
        last_act_time = time.time()
        last_act_count = 0
        
        while (time.time() - start_time) < timeout:
            session = client.sessions.get(session_name)
            state = getattr(session, "state", "STATE_UNSPECIFIED")
            
            if state == "COMPLETED":
                return True, "COMPLETED", session
            if state == "FAILED":
                return False, "FAILED", session
            
            if state == "AWAITING_PLAN_APPROVAL":
                logging.info(f"Session {session_name} awaiting plan approval. Approving...")
                client.sessions.approve_plan(session_name)
            
            # Stale check via activity count
            try:
                activities = client.activities.list_all(session_name)
                if len(activities) > last_act_count:
                    last_act_count = len(activities)
                    last_act_time = time.time()
                    logging.debug(f"New activity detected. Total: {last_act_count}")
                elif (time.time() - last_act_time) > STALE_THRESHOLD_SEC:
                    logging.warning(f"Session {session_name} has been stale for > {STALE_THRESHOLD_SEC}s. Giving up.")
                    return False, "STALE", None
            except JulesAPIError as e:
                # If 404, it might just be too early for activities
                if "404" in str(e):
                    logging.debug("Activity list returned 404 (possibly too early). Continuing...")
                else:
                    raise e

            time.sleep(10)
    except JulesAPIError as e:
        logging.error(f"SDK Error: {e}")
        return False, "ERROR", None
    except Exception as e:
        logging.warning(f"Error polling session: {e}")

    return False, "TIMEOUT", None

def apply_jules_changes(session: Any, work_branch: str) -> bool:
    """
    Applies the changes from Jules. 
    If automationMode was AUTO_CREATE_PR, we fetch the branch.
    """
    outputs = getattr(session, "outputs", [])
    # Outputs are usually objects or dicts depending on the model
    # Based on inspection, it seems they might be models or dicts within the list
    pr_data = None
    for o in outputs:
        # Check if it's an object or dict
        if isinstance(o, dict):
            if "pullRequest" in o:
                pr_data = o.get("pullRequest")
                break
        else:
            if hasattr(o, "pull_request") and o.pull_request:
                pr_data = o.pull_request
                break
            elif hasattr(o, "pullRequest") and o.pullRequest:
                pr_data = o.pullRequest
                break
    
    if not pr_data:
        logging.error("No Pull Request output found in session. Cannot apply changes automatically yet.")
        return False

    # Pull Request URL format is usually https://github.com/owner/repo/pull/123
    # Standard Jules behavior for AUTO_CREATE_PR is to push to a branch named like 'jules-session-ID'
    session_id = getattr(session, "id", None)
    if not session_id:
        # Try to extract from name if id is missing
        name = getattr(session, "name", "")
        session_id = name.split("/")[-1] if "/" in name else name

    jules_branch = f"jules-{session_id}"
    
    logging.info(f"[GIT] Fetching changes from Jules branch '{jules_branch}'...")
    try:
        run_git_cmd(["fetch", "origin"])
        
        ret = run_git_cmd(["branch", "-r"], check=False)
        remote_branch = f"origin/{jules_branch}"
        if remote_branch not in ret.stdout:
            match = re.search(f"origin/(.*{session_id}.*)", ret.stdout)
            if match:
                remote_branch = match.group(0).strip()
                logging.info(f"[GIT] Found alternative remote branch: {remote_branch}")
            else:
                logging.error(f"Could not find remote branch for session {session_id}")
                return False

        logging.info(f"[GIT] Merging {remote_branch} into {work_branch}...")
        run_git_cmd(["merge", "--no-edit", remote_branch])
        return True
    except subprocess.CalledProcessError as e:
        logging.error(f"Git merge failed: {e.stderr}")
        return False

def run_jules_task(
    client: JulesClient,
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
    session_list_resp = client.sessions.list(page_size=100)
    sessions = session_list_resp.get("sessions", [])
    
    # Filter by repo AND recency to avoid re-joining stalled sessions
    # Using snake_case attributes: source_context.source, state, update_time
    repo_sessions = [
        s for s in sessions 
        if s.source_context and repo_slug in (s.source_context.source or "")
    ]
    active_sessions = [
        s for s in repo_sessions 
        if s.state not in ["COMPLETED", "FAILED"] 
        and is_recent(s.update_time, STALE_THRESHOLD_SEC)
    ]
    
    session_name = None
    if active_sessions:
        session_name = active_sessions[0].name
        logging.info(f"Resuming existing session: {session_name}")
    else:
        # 2. Start Session
        full_prompt = (
            f"{task}\n\n"
            f"Use your best judgment, and ask absolutely no questions.\n\n"
            f"As your final step, update the '{plan_path}' file to mark this task as completed "
            f"by changing '[ ] {task}' to '[x] {task}'. If you inadvertently completed any subsequent tasks, mark them off as well."
        )
        
        logging.info(f"Starting new Jules session for: '{task}'")
        session = client.sessions.create(
            prompt=full_prompt,
            source=f"sources/github/{repo_slug}",
            starting_branch=work_branch,
            title=f"Ralph Task: {task[:30]}...",
            require_plan_approval=True
        )
        session_name = session.name
        logging.info(f"Session started: {session_name}")

    # 3. Wait
    success, status, session_info = wait_for_session(client, session_name, timeout)
    if not success:
        return False, status

    # 4. Apply changes
    if session_info and apply_jules_changes(session_info, work_branch):
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
    parser = argparse.ArgumentParser(description="Ralph Wiggum: Autonomous Jules SDK Harness")
    parser.add_argument("--plan", required=True, help="Path to markdown checklist file")
    parser.add_argument("--project", default=".", help="Root path of the project")
    parser.add_argument("--branch", default="ralph-wiggum", help="The persistent work branch")
    parser.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT_SEC, help="Task timeout in seconds")
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable verbose logging")

    args = parser.parse_args()
    configure_logging(verbose=args.verbose)

    load_dotenv()
    api_key = os.environ.get("JULES_API_KEY")
    if not api_key:
        logging.error("JULES_API_KEY environment variable is missing.")
        sys.exit(1)

    abs_project_path = os.path.abspath(args.project)
    if not os.path.exists(abs_project_path):
        logging.error(f"Project path does not exist: {abs_project_path}")
        sys.exit(1)
    os.chdir(abs_project_path)

    # Initialize SDK Client
    client = JulesClient(api_key=api_key)

    # Initialize Git
    ensure_work_branch(args.branch)
    push_changes(args.branch)

    tasks, total_count = parse_plan(args.plan)
    if not tasks:
        logging.info("No tasks to perform.")
        sys.exit(0)

    try:
        for i, (abs_idx, task) in enumerate(tasks):
            logging.info(f"--- Task {abs_idx}/{total_count}: {task} ---")
            
            attempts = 0
            success = False
            while attempts < MAX_RETRIES and not success:
                attempts += 1
                task_success, status = run_jules_task(client, task, ".", args.timeout, args.branch, args.plan)
                
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
    finally:
        client.close()

if __name__ == "__main__":
    main()
