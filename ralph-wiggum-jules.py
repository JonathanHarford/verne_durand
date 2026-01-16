#!/usr/bin/env python3
import argparse
import os
import re
import signal
import subprocess
import sys
import time
from datetime import datetime


# CONFIGURATION
JULES_BIN = "jules"  # Assumes 'jules' is in your PATH
JULES_API_KEY = "9642c385554e5a1931f1eafc6db4eeba8a2f94ab"   # OPTIONAL (DO NOT COMMIT)
DEFAULT_TIMEOUT_SEC = 600
MAX_RETRIES = 3


class Colors:
    HEADER = "\033[95m"
    OKBLUE = "\033[94m"
    OKGREEN = "\033[92m"
    WARNING = "\033[93m"
    FAIL = "\033[91m"
    ENDC = "\033[0m"


def log(message, level="INFO"):
    timestamp = datetime.now().strftime("%H:%M:%S")
    color = Colors.OKBLUE
    if level == "SUCCESS":
        color = Colors.OKGREEN
    elif level == "WARNING":
        color = Colors.WARNING
    elif level == "ERROR":
        color = Colors.FAIL
    elif level == "GIT":
        color = Colors.HEADER

    print(f"{color}[{timestamp}] [{level}] {message}{Colors.ENDC}")


# --- GIT HELPERS ---


def get_current_branch():
    result = subprocess.run(
        ["git", "rev-parse", "--abbrev-ref", "HEAD"], capture_output=True, text=True
    )
    if result.returncode != 0:
        return None
    return result.stdout.strip()


def run_git_cmd(args, check=True):
    return subprocess.run(
        ["git"] + args, check=check, capture_output=True, text=True
    )

def ensure_repo_initialized():
    """
    Ensures the repo has at least one commit so branches can extend from it.
    """
    ret = subprocess.run(
        ["git", "rev-parse", "HEAD"], capture_output=True
    )
    if ret.returncode != 0:
        log("Repository has no commits. Creating initial empty commit.", "GIT")
        try:
            # Check if user needs to set identity, though usually global config handles this.
            # We'll just try to commit.
            subprocess.run(["git", "commit", "--allow-empty", "-m", "Initial commit"], check=True, capture_output=True)
        except subprocess.CalledProcessError as e:
            log(f"Failed to create initial commit: {e}", "ERROR")
            sys.exit(1)


def ensure_work_branch(target_branch):
    """
    Switches to the target branch, creating it if it doesn't exist.
    """
    ensure_repo_initialized()

    current = get_current_branch()
    if current == target_branch:
        return

    log(f"Switching to work branch: '{target_branch}'", "GIT")

    # Try checking out existing branch
    ret = subprocess.run(["git", "checkout", target_branch], capture_output=True)

    if ret.returncode != 0:
        # If failure, assume it doesn't exist and create it
        log(f"Branch '{target_branch}' not found. Creating it.", "GIT")
        try:
            subprocess.run(
                ["git", "checkout", "-b", target_branch],
                check=True,
                stdout=subprocess.DEVNULL,
            )
        except subprocess.CalledProcessError:
            log(
                f"Failed to create branch '{target_branch}'. Is this a git repo?",
                "ERROR",
            )
            sys.exit(1)


def commit_changes(branch, message):
    try:
        run_git_cmd(["add", "."])
        # Allow empty commits
        run_git_cmd(["commit", "--allow-empty", "-m", message])
        log(f"Committed changes: {message}", "GIT")
        
        # Push to origin if remote exists
        ret = run_git_cmd(["remote"], check=False)
        if "origin" in ret.stdout:
            log(f"Pushing '{branch}' to origin...", "GIT")
            # Set upstream if needed
            run_git_cmd(["push", "-u", "origin", branch])
        else:
            log("No 'origin' remote found. Skipping push.", "WARNING")
            
    except subprocess.CalledProcessError as e:
        log(f"Failed to commit/push changes: {e.stderr}", "ERROR")


def get_repo_slug():
    """
    Attempts to extract 'owner/repo' from the git remote.
    """
    try:
        ret = subprocess.run(
            ["git", "remote", "get-url", "origin"], 
            capture_output=True, text=True, check=False
        )
        if ret.returncode != 0:
            return None
        url = ret.stdout.strip()
        # Match git@github.com:owner/repo.git or https://github.com/owner/repo.git
        match = re.search(r"github\.com[:/]([^/]+/[^/.]+)(?:\.git)?", url)
        if match:
            return match.group(1)
    except Exception:
        pass
    return None


# --- JULES INTERACTION ---

def get_active_sessions():
    """
    Returns a set of active session IDs.
    """
    cmd = [JULES_BIN, "remote", "list", "--session"]
    ret = subprocess.run(cmd, capture_output=True, text=True)
    
    if ret.returncode != 0:
        log(f"Failed to list sessions: {ret.stderr}", "ERROR")
        return set()

    sessions = set()
    lines = ret.stdout.splitlines()
    for line in lines:
        parts = line.strip().split()
        if not parts:
            continue
        if "SESSION" in parts[0].upper() or "ID" == parts[0].upper():
            continue
        sessions.add(parts[0])
    
    return sessions


def wait_for_session(session_id, timeout):
    """
    Polls session status until completion or timeout.
    Returns: (success: bool, status: str)
    """
    start_time = time.time()
    
    log(f"Waiting for session {session_id}...", "INFO")
    
    while (time.time() - start_time) < timeout:
        cmd = [JULES_BIN, "remote", "list", "--session"]
        ret = subprocess.run(cmd, capture_output=True, text=True)
        
        if ret.returncode != 0:
            log("Error polling session list. Retrying...", "WARNING")
            time.sleep(5)
            continue
            
        status = None
        for line in ret.stdout.splitlines():
            parts = line.split()
            if parts and parts[0] == session_id:
                line_upper = line.upper()
                if "COMPLETED" in line_upper or "PROPOSED_CHANGES" in line_upper or "DONE" in line_upper:
                    return True, "COMPLETED"
                if "ERROR" in line_upper or "FAILED" in line_upper:
                    return False, "FAILED"
                status = "RUNNING"
                break
        
        if status is None:
            return False, "LOST"
            
        time.sleep(5)

    return False, "TIMEOUT"


def run_jules_task(task, project_path, timeout, work_branch, plan_path):
    """
    Runs a Jules task using the async workflow:
    1. Snapshot sessions
    2. Start new session (with instruction to mark task finished)
    3. Identify new ID
    4. Wait for completion
    5. Merge changes and delete auxiliary branch
    """
    
    # 1. Snapshot
    existing_sessions = get_active_sessions()
    
    # 2. Start Session (ensure repo is pushed first so Jules sees the latest)
    # We already push at the end of the previous task, but let's be sure.
    log(f"Spawning Jules for task: '{task}'", "SYSTEM")
    
    # Instruction for Jules to mark the task completed in the plan file
    full_prompt = (
        f"{task}\n\n"
        f"Use your best judgment, and ask absolutely no questions.\n\n"
        f"As your final step, update the '{plan_path}' file to mark this task as completed "
        f"by changing '[ ] {task}' to '[x] {task}'. If you inadvertently completed any subsequent tasks, mark them off as well."
    )
    
    repo_id = get_repo_slug() or os.path.abspath(project_path)
    cmd = [JULES_BIN, "new", "--repo", repo_id, full_prompt]
    
    ret = subprocess.run(cmd, capture_output=True, text=True)
    
    # Check for known error patterns even if returncode is 0
    if "Error:" in ret.stdout or "Error:" in ret.stderr:
        err_msg = ret.stderr if ret.stderr else ret.stdout
        log(f"Jules reported an error: {err_msg.strip()}", "ERROR")
        return False, "JULES_ERROR"

    if ret.returncode != 0:
        log(f"Failed to start Jules session (Exit {ret.returncode}): {ret.stderr}", "ERROR")
        return False, ret.stderr

    # 3. Identify ID
    new_sessions = get_active_sessions()
    diff = new_sessions - existing_sessions
    
    session_id = None
    if len(diff) == 1:
        session_id = diff.pop()
    elif len(diff) > 1:
        # Ambiguous, try to find the one that matches our anticipated latest one? 
        match = re.search(r"(?:Session ID:|session)\s*([a-zA-Z0-9_-]+)", ret.stdout + ret.stderr, re.IGNORECASE)
        if match:
            session_id = match.group(1)
        else:
             session_id = list(diff)[0]
             log(f"Warning: Multiple new sessions found, picking {session_id}", "WARNING")
    else:
        # Fallback to parsing stdout/stderr
        # Pattern covers "Session ID: 123", "Created session 123", etc.
        match = re.search(r"(?:Session ID:|session)\s*([a-zA-Z0-9_-]+)", ret.stdout + ret.stderr, re.IGNORECASE)
        if match:
            session_id = match.group(1)
        else:
            # Maybe it's just a raw alphanumeric string on a line?
            for line in (ret.stdout + ret.stderr).splitlines():
                if re.match(r"^[a-zA-Z0-9_-]+$", line.strip()):
                    session_id = line.strip()
                    break
            
            if not session_id:
                log("Could not identify new Session ID.", "ERROR")
                log(f"STDOUT: {ret.stdout}", "DEBUG")
                log(f"STDERR: {ret.stderr}", "DEBUG")
                return False, "NO_ID"

    log(f"Session started: {session_id}", "INFO")

    # 4. Wait
    success, status = wait_for_session(session_id, timeout)
    
    if not success:
        return False, status

    # 5. Merge and Delete Flow
    # The user wants to "merge the new branch, and delete it".
    # Implementation: 
    # a) Create a temporary branch to apply the patch.
    # b) Apply Jules changes to that branch.
    # c) Commit on that branch.
    # d) Switch back to work_branch and merge.
    # e) Delete temporary branch.
    
    temp_branch = f"jules-task-{session_id}"
    log(f"Applying changes via temporary branch '{temp_branch}'...", "GIT")
    
    try:
        # Create and switch to temp branch
        run_git_cmd(["checkout", "-b", temp_branch])
        
        # Pull changes
        pull_cmd = [JULES_BIN, "remote", "pull", "--session", session_id, "--apply"]
        pull_ret = subprocess.run(pull_cmd, capture_output=True, text=True)
        if pull_ret.returncode != 0:
            log(f"Failed to pull changes: {pull_ret.stderr}", "ERROR")
            # Don't fail the whole script yet, try to recover
            run_git_cmd(["checkout", work_branch])
            run_git_cmd(["branch", "-D", temp_branch])
            return False, "APPLY_FAILED"

        # Commit on temp branch
        run_git_cmd(["add", "."])
        run_git_cmd(["commit", "--allow-empty", "-m", f"Jules Task: {task}"])
        
        # Merge into work_branch
        run_git_cmd(["checkout", work_branch])
        log(f"Merging '{temp_branch}' into '{work_branch}'...", "GIT")
        run_git_cmd(["merge", temp_branch])
        
        # Delete temp branch
        log(f"Deleting auxiliary branch '{temp_branch}'.", "GIT")
        run_git_cmd(["branch", "-D", temp_branch])
        
    except subprocess.CalledProcessError as e:
        log(f"Git error during merge/delete: {e.stderr}", "ERROR")
        # Try to return to safety
        subprocess.run(["git", "checkout", work_branch], capture_output=True)
        return False, f"GIT_ERROR: {e.stderr[:100]}"
        
    return True, "SUCCESS"


# --- CORE LOGIC ---


def parse_plan(plan_path):
    # This runs AFTER os.chdir, so paths are relative to the project root
    if not os.path.exists(plan_path):
        log(f"Plan file not found at: {os.path.abspath(plan_path)}", "ERROR")
        sys.exit(1)

    with open(plan_path, "r") as f:
        lines = f.readlines()

    pending_tasks = []
    all_task_count = 0
    for i, line in enumerate(lines):
        # Count all tasks (checked or unchecked) to get the total
        if re.match(r"^\s*[-*]\s*\[[ x]\]\s+(.*)", line):
            all_task_count += 1
            
            # If it's unchecked, add it to our pending list
            match = re.match(r"^\s*[-*]\s*\[ \]\s+(.*)", line)
            if match:
                pending_tasks.append((all_task_count, match.group(1).strip()))

    return pending_tasks, all_task_count


def main():
    parser = argparse.ArgumentParser(
        description="Ralph Wiggum: Autonomous Jules Harness"
    )
    parser.add_argument(
        "--plan",
        required=True,
        help="Path to markdown checklist file (relative to project root)",
    )
    parser.add_argument("--project", default=".", help="Root path of the project")
    parser.add_argument(
        "--branch", default="ralph-wiggum", help="The persistent work branch"
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=DEFAULT_TIMEOUT_SEC,
        help="Task timeout in seconds",
    )

    args = parser.parse_args()

    # 1. API Key Check
    if JULES_API_KEY:
        os.environ["JULES_API_KEY"] = JULES_API_KEY
    
    if not os.environ.get("JULES_API_KEY"):
        log("Environment variable 'JULES_API_KEY' is missing.", "ERROR")
        print("Tip: You can set it into the JULES_API_KEY variable at the top of this script.")
        sys.exit(1)

    # 2. Switch Context (Project Root)
    abs_project_path = os.path.abspath(args.project)

    if not os.path.exists(abs_project_path):
        log(f"Project path does not exist: {abs_project_path}", "ERROR")
        sys.exit(1)

    os.chdir(abs_project_path)
    log(f"Working directory set to: {os.getcwd()}", "INFO")

    # 3. Initialize Branch
    try:
        ensure_work_branch(args.branch)
        # Push initial state if remote exists
        ret = run_git_cmd(["remote"], check=False)
        if "origin" in ret.stdout:
            log(f"Pushing initial state of '{args.branch}' to origin...", "GIT")
            run_git_cmd(["push", "-u", "origin", args.branch], check=False)
    except subprocess.CalledProcessError as e:
        log(f"Failed to initialize Git branch: {e}", "ERROR")
        sys.exit(1)

    # 4. Parse Plan
    # Now that we have chdir'd, args.plan is relative to the project root
    tasks, total_count = parse_plan(args.plan)

    if not tasks:
        log("No unchecked tasks found.", "SUCCESS")
        sys.exit(0)

    log(f"Found {len(tasks)} pending tasks out of {total_count} total.", "INFO")

    # 5. Execution Loop
    for abs_idx, task in tasks:
        log(f"Starting Task {abs_idx}/{total_count}: {task}", "SYSTEM")

        attempts = 0
        success = False

        while attempts < MAX_RETRIES and not success:
            attempts += 1

            # Ensure we are on the work branch before starting
            ensure_work_branch(args.branch)

            # Run Jules (Now passing args.plan)
            task_success, status = run_jules_task(task, ".", args.timeout, args.branch, args.plan)

            if task_success:
                # Local checkbox logic removed - Jules handles it now
                commit_changes(args.branch, f"Jules Task: {task}")
                success = True
                log(f"Task completed successfully.", "SUCCESS")
            else:
                if status == "JULES_ERROR":
                    log("Aborting due to fatal Jules error.", "ERROR")
                    sys.exit(1)
                
                log(
                    f"Task failed (Attempt {attempts}). Reason: {status}",
                    "WARNING",
                )
                if attempts < MAX_RETRIES:
                    time.sleep(5)

        if not success:
            log(f"CRITICAL FAILURE: Task '{task}' failed {MAX_RETRIES} times.", "ERROR")
            sys.exit(1)

    log("All tasks in plan completed.", "SUCCESS")


if __name__ == "__main__":
    main()
