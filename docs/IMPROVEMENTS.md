# Verne Durand Script Improvements

This document outlines potential improvements for the `verne_durand.py` script to enhance its robustness, flexibility, and maintainability.

## 1. Configuration Management

**Current State:**
Configuration values (e.g., `TIMEOUT_LIMIT_MIN`, `MAX_RETRIES`) are hardcoded constants.

**Improvement:**
-   Support environment variables to override defaults.
    -   `VERNE_TIMEOUT_MIN`
    -   `VERNE_MAX_RETRIES`
    -   `VERNE_STALE_THRESHOLD_MIN`
    -   `VERNE_AUTOMATION_MODE`
-   Allow command-line arguments to override both defaults and environment variables.

## 2. Plan Flexibility

**Current State:**
Only Markdown checklists (`- [ ] Task`) are supported.

**Improvement:**
-   **YAML Support**: Allow plan files to be in YAML format.
    ```yaml
    tasks:
      - title: "Refactor login"
        status: "pending"
      - title: "Update docs"
        status: "completed"
    ```
-   **JSON Support**: Similar to YAML, useful for machine-generated plans.

## 3. Observability

**Current State:**
-   Basic logging to stderr.
-   Status characters (`?`, `Q`, `P`) printed to stdout.
-   No direct link to the Jules session in the output.

**Improvement:**
-   **Session URL**: Print the full URL to the Jules session upon creation or resumption.
-   **Structured Logging**: Option to log in JSON format for ingestion by monitoring tools.
-   **File Logging**: Write logs to a file (e.g., `verne_durand.log`) in addition to stderr.

## 4. Resiliency & Session Management

**Current State:**
-   Resumes the most recent session for the repo.
-   Retries failed tasks up to 3 times.

**Improvement:**
-   **Context-Aware Resuming**: Verify that the resumed session's prompt actually matches the current task, not just the repo.
-   **Stuck Session Handling**: Better detection of "stuck" sessions (e.g., no activity for X minutes) and option to force-kill and restart.

## 5. Concurrency

**Current State:**
-   Tasks are executed strictly sequentially.

**Improvement:**
-   **Parallel Execution**: Allow running multiple independent tasks in parallel (requires dependency tracking in the plan).

## 6. Code Structure

**Current State:**
-   Single monolithic script.

**Improvement:**
-   **Modularization**: Split into:
    -   `jules_client.py`: API interactions.
    -   `git_utils.py`: Git operations.
    -   `plan_parser.py`: Parsing logic for MD/YAML.
    -   `config.py`: Configuration handling.
-   **Type Hinting**: Improve type coverage and use `mypy` for validation.

## 7. Testing

**Current State:**
-   No automated tests.

**Improvement:**
-   **Unit Tests**: Add tests for `parse_plan`, `is_recent`, and git helpers.
-   **Integration Tests**: Mock the Jules API to test the full loop without spending credits.
