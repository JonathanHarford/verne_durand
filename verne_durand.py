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
    
    # Silence third-party logs entirely unless CRITICAL
    logging.getLogger("jules_agent_sdk").setLevel(logging.CRITICAL)
    logging.getLogger("urllib3").setLevel(logging.CRITICAL)
    logging.getLogger("google").setLevel(logging.CRITICAL)

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

def is_git_dirty() -> bool:
    """Checks if there are uncommitted changes (staged or unstaged)."""
    ret = subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True)
    if ret.returncode != 0:
        return True # Assume dirty/error if we can't check
    return bool(ret.stdout.strip())

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
    ret = subprocess.run(["git", "show-ref", "--verify", "--quiet", f"refs/heads/{target_branch}"])
    is_new = ret.returncode != 0
    
    suffix = " # New branch" if is_new else ""
    logging.info(f"git checkout '{target_branch}'{suffix}")
    
    if is_new:
        subprocess.run(["git", "checkout", "-b", target_branch], check=True, capture_output=True)
    else:
        subprocess.run(["git", "checkout", target_branch], check=True, capture_output=True)

def push_changes(branch: str, message: str = "Verne Durand: Automated update") -> bool:
    """
    Stages all changes, commits them, and pushes to origin.
    Returns True on success, False on failure.
    """
    try:
        # Check if there are any changes to commit
        status_proc = run_git_cmd(["status", "--porcelain"])
        status_out = status_proc.stdout.strip()
        if not status_out:
            # Check if we need to push anyway (e.g. initial setup)
            remote_proc = run_git_cmd(["remote"], check=False)
            if "origin" in remote_proc.stdout:
                # We want to propagate failure here if push fails (e.g. protected branch)
                push_res = run_git_cmd(["push", "-u", "origin", branch], check=False)
                if push_res.returncode != 0:
                    logging.error(f"Git push failed: {push_res.stderr}")
                    return False
            return True

        run_git_cmd(["add", "."])
        logging.info(f"git commit -m '{message}'")
        run_git_cmd(["commit", "-m", message])
        
        ret = run_git_cmd(["remote"], check=False)
        if "origin" in ret.stdout:
            logging.info(f"git push '{branch}' origin")
            push_res = run_git_cmd(["push", "-u", "origin", branch], check=False)
            if push_res.returncode != 0:
                 logging.error(f"Git push failed: {push_res.stderr}")
                 return False
        return True
    except subprocess.CalledProcessError as e:
        logging.error(f"Git operation failed: {e.stderr}")
        return False

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

def wait_for_session(client: JulesClient, session_name: str, timeout: int) -> Tuple[bool, str, Optional[Any], str]:
    """Polls session status until completion or timeout. Returns (success, status, session_info, session_name)"""
    
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
                state = getattr(session, "state", "STATE_UNSPECIFIED")
                
                # Activity check for stale detection AND progress visualization
                has_changed = False
                try:
                    activities = client.activities.list_all(session_name)
                    curr_count = len(activities)
                    if curr_count > last_act_count:
                        last_act_count = curr_count
                        last_act_time = time.time()
                        has_changed = True
                except:
                    pass

                # Determine status character
                char = status_map.get(state, "?")
                if state == "IN_PROGRESS" and has_changed:
                    char = ","
                
                # Print character for status
                print(char, end="", flush=True)
                
                if state == "COMPLETED":
                    print()
                    return True, "COMPLETED", session, session_name
                if state == "FAILED":
                    print()
                    return False, "FAILED", session, session_name
                
                if state == "AWAITING_PLAN_APPROVAL":
                    client.sessions.approve_plan(session_name)
                
                if (time.time() - last_act_time) > (STALE_THRESHOLD_MIN * 60):
                    logging.warning(f"Session {short_id(session_name)} stale. Giving up.")
                    print()
                    return False, "STALE", None, session_name

                time.sleep(POLL_INTERVAL_SEC)
            except (JulesAPIError, Exception):
                # Recoverable/transient error in the loop
                print("?", end="", flush=True)
                time.sleep(POLL_INTERVAL_SEC)
    except Exception:
        return False, "TIMEOUT", None, session_name

    print()
    return False, "TIMEOUT", None, session_name

def safe_get_val(obj: Any, keys: List[str], default: Any = None) -> Any:
    """Safely gets a value from a dict or object using a list of possible keys/attributes."""
    if obj is None:
        return default
    for key in keys:
        if isinstance(obj, dict):
            val = obj.get(key)
            if val is not None:
                return val
        else:
            val = getattr(obj, key, None)
            if val is not None:
                return val
    return default

def apply_jules_changes(session: Any, work_branch: str) -> Tuple[bool, Dict[str, Any]]:
    """
    Applies the changes from Jules by fetching the PR directly using git.
    Uses GitHub's PR ref (refs/pull/NUMBER/head) which doesn't require knowing the branch name.
    """
    outputs = getattr(session, "outputs", [])
    pr_data = None
    
    for o in outputs:
        # Check if it's an object with pull_request attribute
        pr = getattr(o, "pull_request", None)
        if pr:
            pr_data = pr
            break
        # Check if it's a dict with pullRequest or pull_request key
        if isinstance(o, dict):
            pr = o.get("pullRequest") or o.get("pull_request")
            if pr:
                pr_data = pr
                break
    
    if not pr_data:
        logging.error("No Pull Request output found in session. Cannot apply changes automatically yet.")
        return False, {}

    # Get PR URL safely
    pr_url = safe_get_val(pr_data, ["url", "pull_request_url"])
    if not pr_url:
        logging.error("No PR URL found in pull request output")
        return False, {}
    
    # Get Branch name safely (for deletion later)
    # Jules SDK might use 'branch', 'branch_name', or 'head_branch'
    branch_name = safe_get_val(pr_data, ["branch", "branch_name", "head_branch"])
    
    # Extract PR number from URL (e.g., https://github.com/owner/repo/pull/123)
    match = re.search(r"/pull/(\d+)", pr_url)
    if not match:
        logging.error(f"Could not extract PR number from URL: {pr_url}")
        return False, {}
    
    pr_number = match.group(1)
    
    try:
        logging.info(f"git fetch origin pull/{pr_number}/head")
        run_git_cmd(["fetch", "origin", f"pull/{pr_number}/head"])
        
        logging.info(f"git merge --no-edit FETCH_HEAD")
        run_git_cmd(["merge", "--no-edit", "FETCH_HEAD"])

        # Delete the remote branch now that it's merged
        if branch_name:
            logging.info(f"git push origin --delete {branch_name}")
            try:
                run_git_cmd(["push", "origin", "--delete", branch_name])
            except:
                pass

        # Parse completion status from PR title/description
        pr_title = safe_get_val(pr_data, ["title", "subject"]) or ""
        pr_desc = safe_get_val(pr_data, ["description", "body"]) or ""
        full_text = f"{pr_title}\n{pr_desc}"

        parsed_response = parse_jules_response(full_text)
        
        return True, parsed_response
    except subprocess.CalledProcessError as e:
        logging.error(f"Git fetch/merge failed: {e.stderr}")
        return False, {}

def run_jules_task(
    client: JulesClient,
    task: str,
    project_path: str,
    timeout: int,
    work_branch: str,
    plan_path: str,
    rejected_session_ids: List[str] = None
) -> Tuple[bool, Dict[str, Any], str, str, str]:
    repo_slug = get_repo_slug()
    if not repo_slug:
        logging.error("Could not determine GitHub repo slug from 'origin' remote.")
        return False, {}, "", "NO_REPO_SLUG", ""

    # 1. Check for existing active sessions (Resume logic)
    session_list_resp = client.sessions.list(page_size=100)
    sessions = session_list_resp.get("sessions", [])
    rejected_ids = set(rejected_session_ids or [])
    
    # Filter by repo AND recency to avoid re-joining stalled sessions
    repo_sessions = [s for s in sessions if s.source_context and repo_slug in s.source_context.source]
    active_sessions = [
        s for s in repo_sessions 
        if s.state not in ["COMPLETED", "FAILED"] 
        and is_recent(s.update_time, STALE_THRESHOLD_MIN * 60)
        and short_id(s.name) not in rejected_ids
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
            return False, {}, "", "PROMPT_LOAD_FAILED", ""
        
        # 2. Start Session (Load prompt from template)
        # Use raw POST to support automationMode which is missing in high-level SDK
        data = {
            "prompt": full_prompt,
            "sourceContext": {
                "source": f"sources/github/{repo_slug}",
                "githubRepoContext": {"startingBranch": work_branch}
            },
            "automationMode": AUTOMATION_MODE,
            "title": f"Verne Task: {task[:100]}{'...' if len(task) > 100 else ''}",
            "requirePlanApproval": True
        }
        
        # client.sessions.client is the internal JulesAPI object
        response = client.sessions.client.post("sessions", json=data)
        session = Session.from_dict(response)
        
        session_name = session.name
        web_url = getattr(session, "url", "N/A")
        logging.info(f"Jules session started: {web_url}")

    # 3. Wait
    success, status, session_info, active_session_name = wait_for_session(client, session_name, timeout)
    curr_session_id = short_id(active_session_name)

    if not success:
        return False, {}, curr_session_id, status, ""

    # 4. Apply changes (Returns: success, parsed_resp)
    if session_info:
        success, parsed_resp = apply_jules_changes(session_info, work_branch)
        if success:
             # Get commit hash
             commit_hash_proc = run_git_cmd(["rev-parse", "HEAD"])
             commit_hash = commit_hash_proc.stdout.strip()
             return True, parsed_resp, curr_session_id, "COMPLETED", commit_hash
        else:
             return False, {}, curr_session_id, "APPLY_FAILED", ""
    else:
        return False, {}, curr_session_id, "NO_SESSION_INFO", ""

# --- CORE LOGIC ---

class PlanManager:
    def __init__(self, filepath: str):
        self.filepath = filepath

    def load(self) -> Dict[str, List[str]]:
        if not os.path.exists(self.filepath):
             return {"todo": [], "started": [], "completed": [], "rejected": []}
        with open(self.filepath, 'r') as f:
            data = yaml.safe_load(f) or {}
        return {
            "todo": data.get("todo") or [],
            "started": data.get("started") or [],
            "completed": data.get("completed") or [],
            "rejected": data.get("rejected") or []
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
            # Ensure task is not already in started (deduplicate)
            if task not in data["started"]:
                data["started"].append(task)
            self.save(data)
            return True
        elif task in data["started"]:
            return False
        else:
            return False

    def move_to_completed(self, task: str) -> bool:
        data = self.load()
        # Ensure structure
        if "started" not in data: data["started"] = []
        if "completed" not in data: data["completed"] = []

        if task in data["started"]:
            data["started"].remove(task)
            if task not in data["completed"]:
                data["completed"].append(task)
            self.save(data)
            return True
        return False

    def record_completion(self, task: str, session_id: str, commit_hash: str) -> None:
        """Moves a task from started to completed, adding metadata."""
        data = self.load()
        if "started" not in data: data["started"] = []
        if "completed" not in data: data["completed"] = []

        if task in data["started"]:
            data["started"].remove(task)

        # Add to completed as object
        entry = {
            "task": task,
            "session_id": session_id,
            "commit_hash": commit_hash
        }
        data["completed"].append(entry)
        self.save(data)

    def expand_task(self, original_task: str, completed_items: List[str], todo_items: List[str], session_id: str, commit_hash: str) -> None:
        """Splits a task into completed parts and future todos. First TODO becomes next started."""
        data = self.load()
        if "started" not in data: data["started"] = []
        if "completed" not in data: data["completed"] = []
        if "todo" not in data: data["todo"] = []

        # Remove original
        if original_task in data["started"]:
            data["started"].remove(original_task)

        # Add completed items
        for item in completed_items:
            # Check if it was in started and remove it
            if item in data["started"]:
                data["started"].remove(item)
            
            entry = {
                "task": item,
                "session_id": session_id,
                "commit_hash": commit_hash
            }
            # Only add if not already in completed (by task name)
            if not any(e.get("task") == item for e in data["completed"] if isinstance(e, dict)):
                data["completed"].append(entry)

        # Filter todos
        new_todos = []
        if todo_items:
            new_todos = [t for t in todo_items if t not in data["todo"] and t not in data["started"]]
        
        # If there are new todos, the first one is the "next" task (put in started or top of todo)
        # We'll put them all at the top of TODO. The orchestrator pulls from starts then todo.
        # But we want to ensure the very next thing pulled is the first todo.
        # If started is empty (which it is, since we removed original), the plan manager just pulls todo[0].
        # So prepending all to todo is sufficient.
        
        if new_todos:
             data["todo"] = new_todos + data["todo"]

        self.save(data)

    def reject_session(self, session_id: str, task: str, reason: str = "stale") -> None:
        """Adds a session to the rejected list to prevent re-joining."""
        data = self.load()
        if "rejected" not in data:
            data["rejected"] = []
        
        # Avoid duplicate rejections
        if not any(r.get("session_id") == session_id for r in data["rejected"] if isinstance(r, dict)):
            data["rejected"].append({
                "session_id": session_id,
                "task": task,
                "reason": reason,
                "timestamp": datetime.now(timezone.utc).isoformat()
            })
            self.save(data)

def parse_jules_response(text: str) -> Dict[str, Any]:
    """
    Parses the commit message/PR description from Jules.
    Returns a dict with keys: is_done, completed (list), next (str), todo (list).
    """
    result = {
        "is_done": False,
        "completed": [],
        "next": None,
        "todo": []
    }

    if not text:
        return result


    # Check for [STATUS] block
    lines = text.splitlines()
    in_status_block = False

    for line in lines:
        line = line.strip()
        if line.upper() == "[STATUS]":
            in_status_block = True
            continue

        if in_status_block:
            upper_line = line.upper()
            if upper_line == "COMPLETED":
                # Simple completion of the entire current task
                result["is_done"] = True
            elif upper_line.startswith("COMPLETED:"):
                val = line[len("COMPLETED:"):].strip()
                if val: result["completed"].append(val)
            elif upper_line.startswith("TODO:"):
                val = line[len("TODO:"):].strip()
                if val: result["todo"].append(val)
            elif upper_line.startswith("NEXT:"):
                 # Legacy/Ignore, or treat as Todo if present? 
                 # User explicitly said "get rid of NEXT", so we ignore or treat as TODO 
                 # if the agent hallucinates it. Let's ignore to enforce strictness 
                 # or map to TODO. Mapping to TODO is safer.
                 val = line[len("NEXT:"):].strip()
                 if val: result["todo"].append(val)

    return result

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
    # Changed default to None so we can detect if user provided it
    parser.add_argument("--branch", default=None, help="The work branch (defaults to current branch)")
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

    # Ensure we are in a git repo before checking status
    ensure_git_repo()

    # 1. FAIL IF DIRTY
    if is_git_dirty():
        logging.error("Working directory has uncommitted changes. Please commit or stash them before running.")
        sys.exit(1)

    # 2. DETERMINE BRANCH
    if args.branch:
        target_branch = args.branch
        ensure_work_branch(target_branch)
    else:
        target_branch = get_current_branch()
        if not target_branch or target_branch == "HEAD":
            logging.error("Could not determine current branch (or in detached HEAD state).")
            sys.exit(1)
        logging.info(f"Running on current branch: {target_branch}")
        # Ensure work branch calls ensure_repo_initialized, which is safe
        ensure_work_branch(target_branch)

    # Initialize SDK Client
    client = JulesClient(api_key=api_key)

    # Initialize Git - Check for Protected Branch via Push
    if not push_changes(target_branch):
        logging.error("Initial push failed. Branch might be protected or network is down. Exiting.")
        sys.exit(1)

    # Initialize manager
    manager = PlanManager(args.plan)

    # Track stats for summary
    _, total_at_start, completed_count_at_start = parse_plan(args.plan)

    try:
        while True:
            # Re-parse plan every iteration to pick up external/Jules updates
            tasks, total_count, completed_count = parse_plan(args.plan)
            if not tasks:
                logging.info("All tasks completed.")
                break

            # Always pick the first available task (started first, then todo)
            task_data = tasks[0]
            task_name = task_data["task"]
            task_status = task_data["status"]

            # Display status
            display_status = f"{completed_count + 1}/{total_count}"
            status_text = f"{task_status if task_status != 'todo' else 'todo->started'}"
            logging.info(f"Task {display_status} ({status_text}):")
            logging.info(f"{task_name}")

            if task_status == "todo":
                if manager.move_to_started(task_name):
                    push_changes(target_branch, message=f"verne: start task '{task_name[:100]}{'...' if len(task_name) > 100 else ''}'")
            
            attempts = 0
            success = False
            while attempts < MAX_RETRIES and not success:
                attempts += 1
                plan_data = manager.load()
                rejected_ids = [r.get("session_id") for r in plan_data.get("rejected", []) if isinstance(r, dict)]
                
                task_success, parsed_resp, session_id, status, commit_hash = run_jules_task(
                    client, task_name, ".", args.timeout, target_branch, args.plan, rejected_ids
                )
                
                if not task_success and status == "STALE":
                    logging.warning(f"Task '{task_name}' stale. Recording rejected session {session_id}.")
                    manager.reject_session(session_id, task_name, reason="stale")
                    push_changes(target_branch, message=f"verne: reject stale session {session_id}")
                    # We continue the retry loop, but next time run_jules_task will skip this session
                    time.sleep(RETRY_DELAY_SEC)
                    continue

                if task_success:
                    # NEW LOGIC: check for is_done (simple status) or completed items (split status)
                    if parsed_resp.get("is_done") and not parsed_resp.get("completed"):
                        # Simple completion
                        manager.record_completion(task_name, session_id, commit_hash)
                        logging.info(f"Task verified as COMPLETED.")
                        push_changes(target_branch, message=f"verne: complete task '{task_name[:100]}{'...' if len(task_name) > 100 else ''}'")
                        success = True
                    elif parsed_resp.get("completed"):
                        # Split / Partial completion
                        logging.info("Applying structured status update (Task Split)...")
                        manager.expand_task(
                            original_task=task_name,
                            completed_items=parsed_resp["completed"],
                            todo_items=parsed_resp["todo"], # Passed as-is, expands_task handles dedup and ordering
                            session_id=session_id,
                            commit_hash=commit_hash
                        )
                        push_changes(target_branch, message=f"verne: update tasks from '{task_name[:100]}{'...' if len(task_name) > 100 else ''}'")
                        success = True
                    elif parsed_resp.get("is_done"): 
                        # Fallback if both present? 
                        manager.record_completion(task_name, session_id, commit_hash)
                        logging.info(f"Task verified as COMPLETED.")
                        push_changes(target_branch, message=f"verne: complete task '{task_name[:100]}{'...' if len(task_name) > 100 else ''}'")
                        success = True
                    else:
                        logging.warning(f"Jules submitted changes but did NOT mark task as completed (Partial work).")
                        logging.info("Pushing partial work and continuing.")
                        push_changes(target_branch, message=f"verne: partial work for '{task_name[:100]}{'...' if len(task_name) > 100 else ''}'")
                        success = True # Move to next task cycle
                else:
                    logging.warning(f"Task failed (Attempt {attempts}).")
                    if attempts < MAX_RETRIES: 
                        time.sleep(RETRY_DELAY_SEC)

            if not success:
                logging.error(f"CRITICAL FAILURE: Task failed after {MAX_RETRIES} attempts.")
                sys.exit(1)

    finally:
        # Final progression log
        try:
             # Reload plan to get final counts
             _, new_total, new_completed = parse_plan(args.plan)
             tasks_done = new_completed - completed_count_at_start
             
             last_commit = "N/A"
             try:
                 last_commit_proc = run_git_cmd(["rev-parse", "HEAD"])
                 last_commit = last_commit_proc.stdout.strip()
             except:
                 pass

             logging.info("--- SESSION SUMMARY ---")
             logging.info(f"Tasks completed this session: {max(0, tasks_done)}")
             logging.info(f"Total progress: {new_completed}/{new_total}")
             logging.info(f"Final git commit: {last_commit}")
             logging.info("-----------------------")
        except:
             pass
        client.close()

if __name__ == "__main__":
    main()
