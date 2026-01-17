#!/usr/bin/env -S uv run --script
# /// script
# dependencies = [
#   "jules-agent-sdk",
#   "python-dotenv",
#   "PyYAML",
# ]
# ///

import argparse
import logging
import os
import re
import subprocess
import sys
import time
import yaml
from datetime import datetime, timezone
from typing import List, Optional, Tuple, Dict, Any
from dotenv import load_dotenv
from jules_agent_sdk import JulesClient
from jules_agent_sdk.models import Session
from jules_agent_sdk.exceptions import JulesAPIError

# CONFIGURATION
TIMEOUT_LIMIT_MIN = 24 * 60    # Maximum time for a single Jules task
STALE_THRESHOLD_MIN = 20      # Minutes of inactivity before considering a session stalled
MAX_RETRIES = 3                # Maximum number of times to retry a failed task
DEFAULT_WORK_BRANCH = "verne_durand" # Persistent git branch where changes are applied
AUTOMATION_MODE = "AUTO_CREATE_PR"   # Jules behavior (AUTO_CREATE_PR results in a branch/PR)
POLL_INTERVAL_SEC = 30         # Seconds between polling the Jules API for status updates
RETRY_DELAY_SEC = 15           # Seconds to wait between retries of a failed task

class ColorFormatter(logging.Formatter):
    """Custom formatter to add ANSI colors to logs."""
    GREY = "\x1b[38;20m"
    YELLOW = "\x1b[33;20m"
    RED = "\x1b[31;20m"
    BOLD_RED = "\x1b[31;1m"
    GREEN = "\x1b[32;20m"
    CYAN = "\x1b[36;20m"
    RESET = "\x1b[0m"
    
    FORMAT = "[%(asctime)s] [%(levelname)s] %(message)s"

    LEVEL_COLORS = {
        "I": GREY,
        "W": YELLOW,
        "E": RED,
        "D": CYAN
    }

    def format(self, record):
        log_fmt = self.LEVEL_COLORS.get(record.levelname, self.RESET) + self.FORMAT + self.RESET
        
        # Special coloring for specific message patterns
        if "git " in record.msg:
            record.msg = f"{self.CYAN}{record.msg}{self.RESET}"
        elif "verified as COMPLETED" in record.msg:
            record.msg = f"{self.GREEN}{record.msg}{self.RESET}"
        elif "todo->started" in record.msg:
            # Highlight the status transition in yellow
            record.msg = record.msg.replace("(todo->started)", f"{self.YELLOW}(todo->started){self.RESET}")

        formatter = logging.Formatter(log_fmt, datefmt="%H:%M:%S")
        return formatter.format(record)

def configure_logging(verbose: bool = False) -> None:
    """Configures the logging module."""
    logging.addLevelName(logging.INFO, "I")
    logging.addLevelName(logging.WARNING, "W")
    logging.addLevelName(logging.ERROR, "E")
    logging.addLevelName(logging.DEBUG, "D")
    
    level = logging.DEBUG if verbose else logging.INFO
    handler = logging.StreamHandler()
    handler.setFormatter(ColorFormatter())
    
    root = logging.getLogger()
    root.setLevel(level)
    root.addHandler(handler)

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
    logging.info(f"git checkout '{target_branch}'")
    ret = subprocess.run(["git", "checkout", target_branch], capture_output=True)
    if ret.returncode != 0:
        subprocess.run(["git", "checkout", "-b", target_branch], check=True)

def push_changes(branch: str, message: str = "Verne Durand: Automated update") -> None:
    """Stages all changes, commits them, and pushes to origin."""
    try:
        # Check if there are any changes to commit
        status = run_git_cmd(["status", "--porcelain"])
        if status.stdout.strip():
            logging.info("git commit")
            run_git_cmd(["add", "."])
            run_git_cmd(["commit", "-m", message])
        
        ret = run_git_cmd(["remote"], check=False)
        if "origin" in ret.stdout:
            logging.info(f"git push '{branch}' origin")
            run_git_cmd(["push", "-u", "origin", branch])
    except subprocess.CalledProcessError as e:
        logging.error(f"Git operation failed: {e.stderr}")

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

def short_id(name: str) -> str:
    """Returns the short ID from a session name (e.g. 'sessions/123' -> '123')."""
    return name.split("/")[-1] if "/" in name else name

def wait_for_session(client: JulesClient, session_name: str, timeout: int) -> Tuple[bool, str, Optional[Any]]:
    """Polls session status until completion or timeout."""
    logging.info(f"Waiting for session {short_id(session_name)}...")
    
    try:
        start_time = time.time()
        last_act_time = time.time()
        last_act_count = 0
        
        # Initial sleep to avoid race condition immediately after creation
        time.sleep(5)
        
        status_map = {
            "STATE_UNSPECIFIED": "?",
            "QUEUED": "Q",
            "PLANNING": "P",
            "AWAITING_PLAN_APPROVAL": "W",
            "AWAITING_USER_FEEDBACK": "U",
            "IN_PROGRESS": ".",
            "PAUSED": "Z",
            "FAILED": "F",
            "COMPLETED": "C"
        }
        
        while (time.time() - start_time) < timeout:
            try:
                session = client.sessions.get(session_name)
            except JulesAPIError as e:
                if "404" in str(e):
                    logging.debug(f"Session {short_id(session_name)} not found yet (transient 404). Retrying...")
                    time.sleep(2)
                    continue
                raise e

            state = getattr(session, "state", "STATE_UNSPECIFIED")
            
            # Print character for status
            print(status_map.get(state, "?"), end="", flush=True)
            
            if state == "COMPLETED":
                print()
                return True, "COMPLETED", session
            if state == "FAILED":
                print()
                return False, "FAILED", session
            
            if state == "AWAITING_PLAN_APPROVAL":
                logging.info(f"Session {short_id(session_name)} awaiting plan approval. Approving...")
                client.sessions.approve_plan(session_name)
            
            # Stale check via activity count
            try:
                activities = client.activities.list_all(session_name)
                if len(activities) > last_act_count:
                    last_act_count = len(activities)
                    last_act_time = time.time()
                    logging.debug(f"New activity detected. Total: {last_act_count}")
                elif (time.time() - last_act_time) > (STALE_THRESHOLD_MIN * 60):
                    logging.warning(f"Session {short_id(session_name)} has been stale for > {STALE_THRESHOLD_MIN} minutes. Giving up.")
                    print()
                    return False, "STALE", None
            except JulesAPIError as e:
                # If 404, it might just be too early for activities
                if "404" in str(e):
                    logging.debug("Activity list returned 404 (possibly too early). Continuing...")
                else:
                    raise e

            time.sleep(POLL_INTERVAL_SEC)
    except JulesAPIError as e:
        print()
        logging.error(f"SDK Error: {e}")
        return False, "ERROR", None
    except Exception as e:
        print()
        logging.warning(f"Error polling session: {e}")

    print()
    return False, "TIMEOUT", None

def apply_jules_changes(session: Any, work_branch: str) -> bool:
    """
    Applies the changes from Jules by fetching the PR directly using git.
    Uses GitHub's PR ref (refs/pull/NUMBER/head) which doesn't require knowing the branch name.
    """
    outputs = getattr(session, "outputs", [])
    pr_data = next((o.pull_request for o in outputs if hasattr(o, "pull_request") and o.pull_request), None)
    if not pr_data:
        # Fallback if it's still a dict
        pr_data = next((o.get("pullRequest") or o.get("pull_request") for o in outputs if isinstance(o, dict)), None)
    
    if not pr_data:
        logging.error("No Pull Request output found in session. Cannot apply changes automatically yet.")
        return False

    # Get PR URL
    pr_url = getattr(pr_data, "url", None) if hasattr(pr_data, "url") else pr_data.get("url")
    if not pr_url:
        logging.error("No PR URL found in pull request output")
        return False
    
    logging.info(f"[PR] {pr_url}")
    
    # Extract PR number from URL (e.g., https://github.com/owner/repo/pull/123)
    match = re.search(r"/pull/(\d+)", pr_url)
    if not match:
        logging.error(f"Could not extract PR number from URL: {pr_url}")
        return False
    
    pr_number = match.group(1)
    logging.info(f"[GIT] Fetching PR #{pr_number} using GitHub's PR ref...")
    
    # Get Branch name (to delete later)
    branch_name = getattr(pr_data, "branch", None) if hasattr(pr_data, "branch") else pr_data.get("branch")
    
    try:
        # Fetch the PR directly using GitHub's special PR refs
        # This works without needing to know the branch name
        run_git_cmd(["fetch", "origin", f"pull/{pr_number}/head"])
        
        logging.info(f"[GIT] Merging PR #{pr_number} into {work_branch}...")
        run_git_cmd(["merge", "--no-edit", "FETCH_HEAD"])

        # Delete the remote branch now that it's merged
        if branch_name:
            logging.info(f"[GIT] Deleting remote branch '{branch_name}'...")
            try:
                run_git_cmd(["push", "origin", "--delete", branch_name])
            except subprocess.CalledProcessError as e:
                # Often branches are auto-deleted by GitHub if configured, so we don't treat failure as fatal
                logging.debug(f"Remote branch deletion failed (possibly already deleted): {e.stderr}")
        
        return True
    except subprocess.CalledProcessError as e:
        logging.error(f"Git fetch/merge failed: {e.stderr}")
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
    repo_sessions = [s for s in sessions if s.source_context and repo_slug in s.source_context.source]
    active_sessions = [
        s for s in repo_sessions 
        if s.state not in ["COMPLETED", "FAILED"] 
        and is_recent(s.update_time, STALE_THRESHOLD_MIN * 60)
    ]
    
    session_name = None
    if active_sessions:
        session_name = active_sessions[0].name
        logging.info(f"Resuming existing session: {short_id(session_name)}")
    else:
        # 2. Start Session (Load prompt from template)
        try:
            script_dir = os.path.dirname(os.path.abspath(__file__))
            template_path = os.path.join(script_dir, "prompt_template.txt")
            with open(template_path, "r") as f:
                template = f.read().strip()
            full_prompt = template.format(task=task, plan_path=plan_path)
        except Exception as e:
            logging.error(f"Failed to load prompt template: {e}")
            return False, "PROMPT_LOAD_FAILED"
        
        logging.info(f"Starting new Jules session for: '{task}'")
        # Use raw POST to support automationMode which is missing in high-level SDK
        data = {
            "prompt": full_prompt,
            "sourceContext": {
                "source": f"sources/github/{repo_slug}",
                "githubRepoContext": {"startingBranch": work_branch}
            },
            "automationMode": AUTOMATION_MODE,
            "title": f"Verne Task: {task[:30]}...",
            "requirePlanApproval": True
        }
        
        # client.sessions.client is the internal JulesAPI object
        response = client.sessions.client.post("sessions", json=data)
        session = Session.from_dict(response)
        
        session_name = session.name
        web_url = getattr(session, "url", "N/A")
        logging.info(f"Jules session started: {web_url}")

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

class PlanManager:
    def __init__(self, filepath: str):
        self.filepath = filepath

    def load(self) -> Dict[str, List[str]]:
        if not os.path.exists(self.filepath):
             return {"todo": [], "started": [], "completed": []}
        with open(self.filepath, 'r') as f:
            data = yaml.safe_load(f) or {}
        return {
            "todo": data.get("todo") or [],
            "started": data.get("started") or [],
            "completed": data.get("completed") or []
        }

    def save(self, data: Dict[str, List[str]]) -> None:
        with open(self.filepath, 'w') as f:
            yaml.dump(data, f, default_flow_style=False)

    def get_pending_tasks(self) -> List[Dict[str, str]]:
        """Returns a list of tasks that are either in started or todo."""
        data = self.load()
        tasks = []
        for t in data["started"]:
            tasks.append({"task": t, "status": "started"})
        for t in data["todo"]:
            tasks.append({"task": t, "status": "todo"})
        return tasks

    def get_completed_count(self) -> int:
        data = self.load()
        return len(data.get("completed", []))

    def get_total_count(self) -> int:
        data = self.load()
        return len(data["started"]) + len(data["todo"]) + len(data["completed"])

    def move_to_started(self, task: str) -> bool:
        data = self.load()
        # Ensure structure
        if "todo" not in data: data["todo"] = []
        if "started" not in data: data["started"] = []
        if "completed" not in data: data["completed"] = []

        if task in data["todo"]:
            data["todo"].remove(task)
            if task not in data["started"]:
                data["started"].append(task)
            self.save(data)
            return True
        elif task in data["started"]:
            return False
        else:
            return False

def parse_plan(plan_path: str) -> Tuple[List[Dict[str, str]], int, int]:
    manager = PlanManager(plan_path)
    if not os.path.exists(plan_path):
         logging.error(f"Plan file not found: {os.path.abspath(plan_path)}")
         sys.exit(1)

    pending_tasks = manager.get_pending_tasks()
    total_count = manager.get_total_count()
    completed_count = manager.get_completed_count()
    return pending_tasks, total_count, completed_count

def main() -> None:
    parser = argparse.ArgumentParser(description="Verne Durand: Autonomous Jules SDK Harness")
    parser.add_argument("--plan", required=True, help="Path to markdown checklist file")
    parser.add_argument("--project", default=".", help="Root path of the project")
    parser.add_argument("--branch", default=DEFAULT_WORK_BRANCH, help="The persistent work branch")
    parser.add_argument("--timeout", type=int, default=TIMEOUT_LIMIT_MIN * 60, help="Task timeout in seconds")
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

    tasks, total_count, initial_completed = parse_plan(args.plan)
    if not tasks:
        logging.info("No tasks to perform.")
        sys.exit(0)

    try:
        # Re-initialize manager here to be safe
        manager = PlanManager(args.plan)

        for i, task_data in enumerate(tasks):
            task_name = task_data["task"]
            task_status = task_data["status"]

            # Use total_completed + current index for correct numbering
            current_idx = initial_completed + i + 1
            
            # Transition logic for display
            if task_status == "todo":
                if manager.move_to_started(task_name):
                    logging.info(f"Task {current_idx}/{total_count} (todo->started): {task_name}")
                    push_changes(args.branch, message=f"verne: start task '{task_name[:30]}'")
            else:
                logging.info(f"Task {current_idx}/{total_count} ({task_status}): {task_name}")
            
            attempts = 0
            success = False
            while attempts < MAX_RETRIES and not success:
                attempts += 1
                task_success, status = run_jules_task(client, task_name, ".", args.timeout, args.branch, args.plan)
                
                if task_success:
                    # Verify if Jules actually marked it done via the tool
                    updated_plan = manager.load()
                    if task_name in updated_plan.get("completed", []):
                        logging.info(f"Task '{task_name}' verified as COMPLETED.")
                        push_changes(args.branch, message=f"verne: complete task '{task_name[:30]}'")
                        success = True
                    else:
                        logging.warning(f"Jules submitted changes but did NOT mark '{task_name}' as completed.")
                        logging.info("This likely means Jules considers the task partially finished. Stopping automation for review.")
                        push_changes(args.branch, message=f"verne: partial work for '{task_name[:30]}'")
                        sys.exit(0)
                else:
                    logging.warning(f"Task failed (Attempt {attempts}). Reason: {status}")
                    if attempts < MAX_RETRIES: 
                        time.sleep(RETRY_DELAY_SEC)

            if not success:
                logging.error(f"CRITICAL FAILURE: Task '{task_name}' failed after {MAX_RETRIES} attempts.")
                sys.exit(1)

        logging.info("All tasks completed.")
    finally:
        client.close()

if __name__ == "__main__":
    main()
