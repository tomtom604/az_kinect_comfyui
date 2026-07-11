#!/usr/bin/env python3
from __future__ import annotations

import argparse
import fnmatch
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path("/home/thard/az_kinnect_comfyUI").resolve()
WT_ROOT = Path("/home/thard/az_kinnect_comfyUI.worktrees").resolve()

OWNER_MAP = {
    "capture-worker": ("capture", "agent/capture"),
    "pose-worker": ("pose", "agent/pose"),
    "comfy-worker": ("comfy", "agent/comfy"),
}


class ValidationError(RuntimeError):
    pass


def run(*args: str, cwd: Path = ROOT) -> str:
    result = subprocess.run(
        list(args),
        cwd=cwd,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if result.returncode != 0:
        command = " ".join(args)
        raise ValidationError(
            f"Command failed ({result.returncode}): {command}\n{result.stderr.strip()}"
        )
    return result.stdout.strip()


def load_json(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ValidationError(f"File not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise ValidationError(f"Invalid JSON in {path}: {exc}") from exc

    if not isinstance(data, dict):
        raise ValidationError(f"Expected a JSON object in {path}")
    return data


def require_keys(data: dict[str, Any], keys: set[str], label: str) -> None:
    missing = sorted(keys - data.keys())
    if missing:
        raise ValidationError(f"{label} is missing required keys: {', '.join(missing)}")


def path_allowed(path: str, patterns: list[str]) -> bool:
    clean = path.replace("\\", "/").lstrip("./")
    for pattern in patterns:
        normalized = pattern.replace("\\", "/").lstrip("./")
        if normalized.endswith("/**"):
            prefix = normalized[:-3].rstrip("/")
            if clean == prefix or clean.startswith(prefix + "/"):
                return True
        if fnmatch.fnmatchcase(clean, normalized):
            return True
    return False


def require_clean(worktree: Path) -> None:
    status = run("git", "status", "--porcelain", cwd=worktree)
    if status:
        raise ValidationError(
            f"Worker worktree is dirty; validation requires a committed result:\n{status}"
        )


def validate_task_and_status(
    task: dict[str, Any], status: dict[str, Any], task_id: str
) -> tuple[str, Path, str]:
    require_keys(
        task,
        {
            "task_id", "owner", "owned_paths", "allowed_tests",
            "acceptance_criteria", "max_attempts"
        },
        "Task contract",
    )
    require_keys(
        status,
        {
            "task_id", "status", "summary", "files_changed",
            "tests", "commit", "risks", "next_action"
        },
        "Worker status",
    )

    if task["task_id"] != task_id:
        raise ValidationError("Task filename ID and task JSON task_id do not match.")
    if status["task_id"] != task_id:
        raise ValidationError("Worker status task_id does not match requested task.")

    if task["owner"] not in OWNER_MAP:
        raise ValidationError(f"Task owner is not launchable: {task['owner']}")

    if status["status"] != "completed":
        raise ValidationError(
            f"Only status='completed' can be validated for review; got {status['status']!r}."
        )

    commit = status["commit"]
    if not isinstance(commit, str) or len(commit) < 7:
        raise ValidationError("Worker status must contain a non-empty Git commit SHA.")

    worker_name, branch = OWNER_MAP[task["owner"]]
    worktree = WT_ROOT / worker_name
    if not worktree.is_dir():
        raise ValidationError(f"Expected worker worktree is missing: {worktree}")

    current_branch = run("git", "branch", "--show-current", cwd=worktree)
    if current_branch != branch:
        raise ValidationError(
            f"Worker is on {current_branch!r}; expected {branch!r}."
        )

    require_clean(worktree)

    resolved_commit = run("git", "rev-parse", "--verify", f"{commit}^{{commit}}")
    branch_tip = run("git", "rev-parse", branch)

    if resolved_commit != branch_tip:
        raise ValidationError(
            "Claimed commit must be the current tip of the worker branch. "
            f"Claimed={resolved_commit}, branch_tip={branch_tip}"
        )

    ancestor_code = subprocess.run(
        ["git", "merge-base", "--is-ancestor", resolved_commit, branch],
        cwd=ROOT,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    ).returncode
    if ancestor_code != 0:
        raise ValidationError("Claimed commit is not reachable from expected worker branch.")

    return branch, worktree, resolved_commit


def validate_changed_paths(
    task: dict[str, Any], branch: str, commit: str
) -> list[str]:
    base = run("git", "merge-base", "main", branch)
    changed_raw = run("git", "diff", "--name-only", f"{base}..{commit}")
    changed = [line for line in changed_raw.splitlines() if line.strip()]

    if not changed:
        raise ValidationError("Worker commit contains no changed files.")

    out_of_scope = [
        path for path in changed
        if not path_allowed(path, task["owned_paths"])
    ]
    if out_of_scope:
        raise ValidationError(
            "Worker changed paths outside owned_paths:\n- "
            + "\n- ".join(out_of_scope)
        )

    claimed = status_files = task.get("_status_files", [])
    if claimed:
        missing_claims = sorted(set(changed) - set(claimed))
        extra_claims = sorted(set(claimed) - set(changed))
        if missing_claims or extra_claims:
            details = []
            if missing_claims:
                details.append("Missing from worker files_changed: " + ", ".join(missing_claims))
            if extra_claims:
                details.append("Not actually changed: " + ", ".join(extra_claims))
            raise ValidationError("; ".join(details))

    return changed


def validate_tests(task: dict[str, Any], status: dict[str, Any], worktree: Path) -> list[str]:
    tests = status["tests"]
    if not isinstance(tests, list) or not tests:
        raise ValidationError("Worker status must include at least one test result.")

    reported_names = set()
    for item in tests:
        if not isinstance(item, dict):
            raise ValidationError("Each status.tests entry must be an object.")
        name = item.get("name")
        result = item.get("status")
        if not isinstance(name, str) or not name:
            raise ValidationError("Each status.tests entry needs a non-empty name.")
        if result != "passed":
            raise ValidationError(f"Worker reported non-passing test {name!r}: {result!r}")
        reported_names.add(name)

    allowed = set(task["allowed_tests"])
    if not allowed.intersection(reported_names):
        raise ValidationError(
            "Worker did not report any task-approved test command. "
            f"Allowed: {sorted(allowed)}; reported: {sorted(reported_names)}"
        )

    executed = []
    for command in task["allowed_tests"]:
        parts = command.split()
        if not parts:
            continue
        result = subprocess.run(
            parts,
            cwd=worktree,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            check=False,
        )
        if result.returncode != 0:
            raise ValidationError(
                f"Independent required test failed: {command}\n{result.stdout[-4000:]}"
            )
        executed.append(command)

    return executed


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Independently validate a completed worker result."
    )
    parser.add_argument("--task", required=True, help="Task ID, e.g. CAPTURE-001")
    parser.add_argument(
        "--status-file",
        required=True,
        help="Path to exact worker final JSON status object",
    )
    args = parser.parse_args()

    if Path.cwd().resolve() != ROOT:
        raise ValidationError(f"Run only from {ROOT}")

    if not args.task or not args.task.replace("-", "").isalnum():
        raise ValidationError("Task ID has invalid characters.")

    task_path = ROOT / "tasks" / "backlog" / f"{args.task}.json"
    task = load_json(task_path)
    status_path = Path(args.status_file).resolve()
    status = load_json(status_path)

    task["_status_files"] = status["files_changed"]

    branch, worktree, commit = validate_task_and_status(task, status, args.task)
    changed = validate_changed_paths(task, branch, commit)
    executed_tests = validate_tests(task, status, worktree)

    result_dir = ROOT / "state" / "review"
    result_dir.mkdir(parents=True, exist_ok=True)
    result_path = result_dir / f"{args.task}_{commit[:12]}_validated.json"

    result = {
        "task_id": args.task,
        "validation_status": "pending_human_review",
        "worker_branch": branch,
        "worker_worktree": str(worktree),
        "commit": commit,
        "changed_files": changed,
        "independently_executed_tests": executed_tests,
        "next_action": (
            "Human review required. No merge, deployment, or follow-up worker "
            "dispatch is authorized by this validation result."
        ),
    }
    result_path.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")

    print("VALIDATION PASSED")
    print(f"Review record: {result_path}")
    print("Result is pending_human_review; nothing was merged.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ValidationError as exc:
        print(f"VALIDATION FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1)
