#!/usr/bin/env python3
import argparse
import logging
import os
import re
import shutil
import signal
import subprocess
import sys
import time
from datetime import datetime
from typing import List, Optional, Set, Tuple


# CONFIGURATION
JULES_BIN = "jules"  # Can be overridden by --jules-bin
DEFAULT_TIMEOUT_SEC = 600
MAX_RETRIES = 3


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
    """
    Verifies that the current directory is a git repository.
    Exits if it is not.
    """
    ret = subprocess.run(
        ["git", "rev-parse", "--is-inside-work-tree"], capture_output=True
    )
    if ret.returncode != 0:
        logging.error("Current directory is not a git repository.")
        sys.exit(1)


def ensure_repo_initialized() -> None:
    """
    Ensures the repo has at least one commit so branches can extend from it.
    """
    ensure_git_repo()

    ret = subprocess.run(
        ["git", "rev-parse", "HEAD"], capture_output=True
    )
    if ret.returncode != 0:
        logging.info("[GIT] Repository has no commits. Creating initial empty commit.")
        try:
            # Check if user needs to set identity, though usually global config handles this.
            # We'll just try to commit.
            subprocess.run(["git", "commit", "--allow-empty", "-m", "Initial commit"], check=True, capture_output=True)
        except subprocess.CalledProcessError as e:
            logging.error(f"Failed to create initial commit: {e}")
            sys.exit(1)


def ensure_work_branch(target_branch: str) -> None:
    """
    Switches to the target branch, creating it if it doesn't exist.
    """
    ensure_repo_initialized()

    current = get_current_branch()
    if current == target_branch:
        return

    logging.info(f"[GIT] Switching to work branch: '{target_branch}'")

    # Try checking out existing branch
    ret = subprocess.run(["git", "checkout", target_branch], capture_output=True)

    if ret.returncode != 0:
        # If failure, assume it doesn't exist and create it
        logging.info(f"[GIT] Branch '{target_branch}' not found. Creating it.")
        try:
            subprocess.run(
                ["git", "checkout", "-b", target_branch],
                check=True,
                stdout=subprocess.DEVNULL,
            )
        except subprocess.CalledProcessError:
            logging.error(f"Failed to create branch '{target_branch}'. Is this a git repo?")
            sys.exit(1)


def push_changes(branch: str) -> None:
    """Pushes the branch to origin if it exists."""
    try:
        # Push to origin if remote exists
        ret = run_git_cmd(["remote"], check=False)
        if "origin" in ret.stdout:
            logging.info(f"[GIT] Pushing '{branch}' to origin...")
            # Set upstream if needed
            run_git_cmd(["push", "-u", "origin", branch])
        else:
            logging.warning("No 'origin' remote found. Skipping push.")
            
    except subprocess.CalledProcessError as e:
        logging.error(f"Failed to push changes: {e.stderr}")


def get_repo_slug() -> Optional[str]:
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

def get_active_sessions(repo_filter: Optional[str] = None, active_only: bool = False) -> Set[str]:
    """
    Returns a set of active session IDs.
    """
    cmd = [JULES_BIN, "remote", "list", "--session"]
    if repo_filter:
        cmd.extend(["--repo", repo_filter])

    ret = subprocess.run(cmd, capture_output=True, text=True)
    
    if ret.returncode != 0:
        logging.error(f"Failed to list sessions: {ret.stderr}")
        return set()

    sessions = set()
    lines = ret.stdout.splitlines()
    for line in lines:
        line_upper = line.upper()
        parts = line.strip().split()
        if not parts or parts[0] == "ID" or "SESSION" in parts[0]:
            continue
        
        # Determine status. It's usually the last column.
        # Fixed statuses that are terminal:
        if active_only:
            if any(term in line_upper for term in ["COMPLETED", "FAILED", "ABORTED", "DONE"]):
                continue
            # If line ends with 'COMPLETED' or 'FAILED' etc.
            status = parts[-1].upper()
            if status in ["COMPLETED", "FAILED", "ABORTED", "DONE"]:
                continue

        sessions.add(parts[0])
    
    return sessions


def wait_for_session(session_id: str, timeout: int) -> Tuple[bool, str]:
    """
    Polls session status until completion or timeout.
    Returns: (success: bool, status: str)
    """
    start_time = time.time()
    
    logging.info(f"Waiting for session {session_id}...")
    
    while (time.time() - start_time) < timeout:
        cmd = [JULES_BIN, "remote", "list", "--session"]
        ret = subprocess.run(cmd, capture_output=True, text=True)
        
        if ret.returncode != 0:
            logging.warning("Error polling session list. Retrying...")
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


def run_jules_task(
    task: str,
    project_path: str,
    timeout: int,
    work_branch: str,
    plan_path: str,
    resume_session_id: Optional[str] = None
) -> Tuple[bool, str]:
    """
    Runs a Jules task using the async workflow:
    1. Snapshot sessions
    2. Start new session (with instruction to mark task finished)
    3. Identify new ID
    4. Wait for completion
    5. Merge changes and delete auxiliary branch
    """
    
    session_id = resume_session_id
    repo_id = get_repo_slug() or os.path.abspath(project_path)

    if not session_id:
        # 1. Snapshot
        existing_sessions = get_active_sessions(repo_filter=repo_id)

        # 2. Start Session (ensure repo is pushed first so Jules sees the latest)
        # We already push at the end of the previous task, but let's be sure.
        logging.info(f"Spawning Jules for task: '{task}'")

        # Sync to remote if available
        ret = run_git_cmd(["remote"], check=False)
        if "origin" in ret.stdout:
             logging.info(f"[GIT] Syncing '{work_branch}' to origin before starting Jules...")
             run_git_cmd(["push", "origin", work_branch], check=False)

        # Instruction for Jules to mark the task completed in the plan file
        full_prompt = (
            f"{task}\n\n"
            f"Use your best judgment, and ask absolutely no questions.\n\n"
            f"As your final step, update the '{plan_path}' file to mark this task as completed "
            f"by changing '[ ] {task}' to '[x] {task}'. If you inadvertently completed any subsequent tasks, mark them off as well."
        )

        cmd = [JULES_BIN, "new", "--repo", repo_id, full_prompt]

        ret = subprocess.run(cmd, capture_output=True, text=True)

        # Check for known error patterns even if returncode is 0
        if "Error:" in ret.stdout or "Error:" in ret.stderr:
            err_msg = ret.stderr if ret.stderr else ret.stdout
            logging.error(f"Jules reported an error: {err_msg.strip()}")
            return False, "JULES_ERROR"

        if ret.returncode != 0:
            logging.error(f"Failed to start Jules session (Exit {ret.returncode}): {ret.stderr}")
            return False, ret.stderr

        # 3. Identify ID
        new_sessions = get_active_sessions(repo_filter=repo_id)
        diff = new_sessions - existing_sessions

        if len(diff) == 1:
            session_id = diff.pop()
        elif len(diff) > 1:
            # Ambiguous, try to find the one that matches our anticipated latest one?
            match = re.search(r"(?:Session ID:|session|id)\s*[:=]?\s*([a-zA-Z0-9_-]+)", ret.stdout + ret.stderr, re.IGNORECASE)
            if match:
                session_id = match.group(1)
            else:
                session_id = list(diff)[0]
                logging.warning(f"Multiple new sessions found, picking {session_id}")
        else:
            # Fallback to parsing stdout/stderr
            # Pattern covers "Session ID: 123", "Created session 123", "ID: 123", etc.
            match = re.search(r"(?:Session ID:|session|id)\s*[:=]?\s*([a-zA-Z0-9_-]+)", ret.stdout + ret.stderr, re.IGNORECASE)
            if match:
                session_id = match.group(1)
            else:
                # Maybe it's just a raw alphanumeric string on a line?
                # Exclude common status words that might appear alone
                ignored_words = {"error", "warning", "success", "failed", "done", "completed"}

                for line in (ret.stdout + ret.stderr).splitlines():
                    stripped = line.strip()
                    if re.match(r"^[a-zA-Z0-9_-]+$", stripped):
                        if stripped.lower() not in ignored_words:
                            session_id = stripped
                            break

                if not session_id:
                    logging.error("Could not identify new Session ID.")
                    logging.debug(f"STDOUT: {ret.stdout}")
                    logging.debug(f"STDERR: {ret.stderr}")
                    return False, "NO_ID"

        logging.info(f"Session started: {session_id}")
    else:
        logging.info(f"Resuming existing session: {session_id}")

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
    logging.info(f"[GIT] Applying changes via temporary branch '{temp_branch}'...")
    
    try:
        # Create and switch to temp branch
        run_git_cmd(["checkout", "-b", temp_branch])
        
        # Pull changes
        pull_cmd = [JULES_BIN, "remote", "pull", "--session", session_id, "--apply"]
        pull_ret = subprocess.run(pull_cmd, capture_output=True, text=True)
        if pull_ret.returncode != 0:
            logging.error(f"Failed to pull changes: {pull_ret.stderr}")
            # Don't fail the whole script yet, try to recover
            run_git_cmd(["checkout", work_branch])
            run_git_cmd(["branch", "-D", temp_branch])
            return False, "APPLY_FAILED"

        # Commit on temp branch
        run_git_cmd(["add", "."])
        run_git_cmd(["commit", "--allow-empty", "-m", f"Jules Task: {task}"])
        
        # Merge into work_branch
        run_git_cmd(["checkout", work_branch])
        logging.info(f"[GIT] Merging '{temp_branch}' into '{work_branch}'...")
        run_git_cmd(["merge", temp_branch])
        
        # Delete temp branch
        logging.info(f"[GIT] Deleting auxiliary branch '{temp_branch}'.")
        run_git_cmd(["branch", "-D", temp_branch])
        
    except subprocess.CalledProcessError as e:
        logging.error(f"Git error during merge/delete: {e.stderr}")
        # Try to return to safety
        subprocess.run(["git", "checkout", work_branch], capture_output=True)
        return False, f"GIT_ERROR: {e.stderr[:100]}"
        
    return True, "SUCCESS"


# --- CORE LOGIC ---


def check_prerequisites() -> None:
    """
    Checks if necessary tools are installed.
    """
    if not shutil.which("git"):
        logging.error("Git is not installed or not in PATH.")
        sys.exit(1)

    if not shutil.which(JULES_BIN):
        logging.error(f"Jules binary '{JULES_BIN}' not found. Please install it or set --jules-bin.")
        sys.exit(1)


def parse_plan(plan_path: str) -> Tuple[List[Tuple[int, str]], int]:
    # This runs AFTER os.chdir, so paths are relative to the project root
    if not os.path.exists(plan_path):
        logging.error(f"Plan file not found at: {os.path.abspath(plan_path)}")
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


def main() -> None:
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
    parser.add_argument(
        "--jules-bin",
        default="jules",
        help="Path to the jules executable (default: jules)",
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose logging",
    )

    args = parser.parse_args()

    # Setup logging based on verbosity
    configure_logging(verbose=args.verbose)

    # Global Configuration Override
    global JULES_BIN
    JULES_BIN = args.jules_bin

    # 1. API Key Check
    if not os.environ.get("JULES_API_KEY"):
        logging.error("Environment variable 'JULES_API_KEY' is missing.")
        logging.info("Please set JULES_API_KEY before running this script.")
        # Proceeding might be okay if user relies on gcloud auth, but typically API key is needed.
        # Original script exited, so we exit too.
        sys.exit(1)

    # Check tools
    check_prerequisites()

    # 2. Switch Context (Project Root)
    abs_project_path = os.path.abspath(args.project)

    if not os.path.exists(abs_project_path):
        logging.error(f"Project path does not exist: {abs_project_path}")
        sys.exit(1)

    os.chdir(abs_project_path)
    logging.info(f"Working directory set to: {os.getcwd()}")

    # 3. Initialize Branch
    try:
        ensure_work_branch(args.branch)
        # Push initial state if remote exists
        ret = run_git_cmd(["remote"], check=False)
        if "origin" in ret.stdout:
            logging.info(f"[GIT] Pushing initial state of '{args.branch}' to origin...")
            run_git_cmd(["push", "-u", "origin", args.branch], check=False)
    except subprocess.CalledProcessError as e:
        logging.error(f"Failed to initialize Git branch: {e}")
        sys.exit(1)

    # 4. Parse Plan
    # Now that we have chdir'd, args.plan is relative to the project root
    tasks, total_count = parse_plan(args.plan)

    if not tasks:
        logging.info("No unchecked tasks found.")
        sys.exit(0)

    logging.info(f"Found {len(tasks)} pending tasks out of {total_count} total.")

    # 5. Execution Loop
    for i, (abs_idx, task) in enumerate(tasks):
        logging.info(f"Starting Task {abs_idx}/{total_count}: {task}")

        attempts = 0
        success = False

        while attempts < MAX_RETRIES and not success:
            attempts += 1

            # Check for existing session for this repo before starting a new one
            repo_id = get_repo_slug() or os.path.abspath(args.project)
            existing_active = get_active_sessions(repo_filter=repo_id, active_only=True)
            
            current_resume_id = None
            if existing_active:
                current_resume_id = list(existing_active)[0]
                logging.info(f"Found existing active session {current_resume_id} for this repo. Resuming...")

            # Ensure we are on the work branch before starting
            ensure_work_branch(args.branch)

            # Run Jules
            task_success, status = run_jules_task(
                task, ".", args.timeout, args.branch, args.plan, 
                resume_session_id=current_resume_id
            )

            if task_success:
                # Local checkbox logic removed - Jules handles it now
                push_changes(args.branch)
                success = True
                logging.info(f"Task completed successfully.")
            else:
                if status == "JULES_ERROR":
                    logging.error("Aborting due to fatal Jules error.")
                    sys.exit(1)
                
                logging.warning(f"Task failed (Attempt {attempts}). Reason: {status}")
                if attempts < MAX_RETRIES:
                    time.sleep(5)

        if not success:
            logging.error(f"CRITICAL FAILURE: Task '{task}' failed {MAX_RETRIES} times.")
            sys.exit(1)

    logging.info("All tasks in plan completed.")


if __name__ == "__main__":
    main()
