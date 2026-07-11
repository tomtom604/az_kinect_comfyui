#!/usr/bin/env bash
set -Eeuo pipefail
umask 077

ROOT="$(git rev-parse --show-toplevel)"
EXPECTED="/home/thard/az_kinnect_comfyUI"
WT_ROOT="/home/thard/az_kinnect_comfyUI.worktrees"

usage() {
  cat <<'EOF'
Usage:
  scripts/launch_worker.sh --task TASK-ID [--dry-run]

Examples:
  scripts/launch_worker.sh --task CAPTURE-001 --dry-run
  scripts/launch_worker.sh --task POSE-001
EOF
}

TASK_ID=""
DRY_RUN=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --task)
      [[ $# -ge 2 ]] || { echo "--task requires a value" >&2; exit 2; }
      TASK_ID="$2"
      shift 2
      ;;
    --dry-run)
      DRY_RUN=1
      shift
      ;;
    --auto|--yes|-y)
      echo "Refusing: automatic approval is never permitted by this launcher." >&2
      exit 2
      ;;
    --help|-h)
      usage
      exit 0
      ;;
    *)
      echo "Unknown argument: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

[[ "$ROOT" == "$EXPECTED" ]] || {
  echo "Refusing: launcher must run from $EXPECTED" >&2
  exit 1
}

[[ -n "$TASK_ID" ]] || {
  echo "Refusing: --task TASK-ID is required." >&2
  usage >&2
  exit 2
}

[[ "$TASK_ID" =~ ^[A-Z]+-[0-9]{3}$ ]] || {
  echo "Refusing: invalid task ID format: $TASK_ID" >&2
  exit 2
}

TASK_FILE="$ROOT/tasks/backlog/${TASK_ID}.json"
[[ -f "$TASK_FILE" ]] || {
  echo "Refusing: task not found: $TASK_FILE" >&2
  exit 1
}

command -v opencode >/dev/null || {
  echo "Refusing: opencode was not found in PATH." >&2
  exit 1
}

command -v flock >/dev/null || {
  echo "Refusing: flock was not found; install util-linux before launching workers." >&2
  exit 1
}

readarray -t TASK_META < <(python3 - "$TASK_FILE" <<'PY'
import json, sys
from pathlib import PurePosixPath

path = sys.argv[1]
with open(path, encoding="utf-8") as f:
    task = json.load(f)

required = {
    "task_id", "owner", "objective", "owned_paths",
    "read_only_paths", "forbidden_paths",
    "acceptance_criteria", "allowed_tests",
    "max_attempts", "requires_human_approval"
}
missing = sorted(required - task.keys())
if missing:
    raise SystemExit(f"Invalid task contract; missing: {', '.join(missing)}")

owners = {
    "capture-worker": ("capture", "agent/capture"),
    "pose-worker": ("pose", "agent/pose"),
    "comfy-worker": ("comfy", "agent/comfy")
}
owner = task["owner"]
if owner not in owners:
    raise SystemExit(f"Unsupported launchable owner: {owner}")

worktree_name, branch = owners[owner]
print(owner)
print(worktree_name)
print(branch)
print(str(task["max_attempts"]))
PY
)

OWNER="${TASK_META[0]}"
WORKER_NAME="${TASK_META[1]}"
EXPECTED_BRANCH="${TASK_META[2]}"
MAX_ATTEMPTS="${TASK_META[3]}"
WORKTREE="$WT_ROOT/$WORKER_NAME"

[[ -d "$WORKTREE/.git" || -f "$WORKTREE/.git" ]] || {
  echo "Refusing: expected worktree does not exist: $WORKTREE" >&2
  exit 1
}

CURRENT_BRANCH="$(git -C "$WORKTREE" branch --show-current)"
[[ "$CURRENT_BRANCH" == "$EXPECTED_BRANCH" ]] || {
  echo "Refusing: $WORKTREE is on '$CURRENT_BRANCH'; expected '$EXPECTED_BRANCH'." >&2
  exit 1
}

if [[ -n "$(git -C "$WORKTREE" status --porcelain)" ]]; then
  echo "Refusing: worker worktree is dirty: $WORKTREE" >&2
  echo "Inspect it with: git -C '$WORKTREE' status" >&2
  exit 1
fi

mkdir -p \
  "$ROOT/state/audit" \
  "$ROOT/state/events" \
  "$ROOT/state/locks"

LOCK_FILE="$ROOT/state/locks/${WORKER_NAME}.lock"
exec 9>"$LOCK_FILE"

if ! flock -n 9; then
  echo "Refusing: $WORKER_NAME already has an active launcher lock." >&2
  exit 1
fi

STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
EVENT_LOG="$ROOT/state/audit/${TASK_ID}_${STAMP}.jsonl"
EVENT_META="$ROOT/state/events/${TASK_ID}_${STAMP}.json"

python3 - "$EVENT_META" "$TASK_FILE" "$OWNER" "$WORKTREE" "$EXPECTED_BRANCH" "$MAX_ATTEMPTS" <<'PY'
import json, sys
from datetime import datetime, timezone

out, task_file, owner, worktree, branch, max_attempts = sys.argv[1:]
with open(task_file, encoding="utf-8") as f:
    task = json.load(f)

event = {
    "event_type": "worker_launch_requested",
    "timestamp": datetime.now(timezone.utc).isoformat(),
    "task_id": task["task_id"],
    "owner": owner,
    "branch": branch,
    "worktree": worktree,
    "max_attempts": int(max_attempts),
    "status": "pending"
}
with open(out, "w", encoding="utf-8") as f:
    json.dump(event, f, indent=2)
    f.write("\n")
PY

PROMPT="$(cat <<EOF
You are the ${OWNER} assigned task ${TASK_ID}.

Read AGENTS.md first. Then read:
- tasks/backlog/${TASK_ID}.json
- contracts/task.schema.json
- contracts/status.schema.json
- docs/PHASE0.md

Your worktree is ${WORKTREE} on branch ${EXPECTED_BRANCH}.
You may act only within the task contract's owned_paths and permitted test commands.

Non-negotiable runtime rules:
1. Never use --auto or seek a permission bypass.
2. Never access another worktree, /mnt/f, hardware devices, models, installed
   ComfyUI directories, secrets, or paths outside this worktree.
3. Do not install dependencies, alter project policy/configuration, change shared
   contracts, merge, push, rebase, reset, or delete project files.
4. If required behavior is ambiguous or requires a shared-interface change,
   stop and report BLOCKED_INTERFACE_CHANGE; do not guess.
5. Make no more than one cohesive implementation attempt.
6. Run only the exact allowed_tests declared by the task.
7. If successful, create one local Git commit with a conventional message.
8. In your final response, return ONLY valid JSON matching
   contracts/status.schema.json. Include the exact commit SHA; use an empty
   string if no commit was created.

Begin by restating your permitted owned_paths and out-of-scope boundaries.
EOF
)"

echo "Task:       $TASK_ID"
echo "Agent:      $OWNER"
echo "Worktree:   $WORKTREE"
echo "Branch:     $EXPECTED_BRANCH"
echo "Audit log:  $EVENT_LOG"

if [[ "$DRY_RUN" -eq 1 ]]; then
  echo
  echo "Dry run passed. No OpenCode session was started."
  exit 0
fi

set +e
(
  cd "$WORKTREE"
  opencode run \
    --agent "$OWNER" \
    --dir "$WORKTREE" \
    --format json \
    --title "$TASK_ID" \
    "$PROMPT"
) 2>&1 | tee "$EVENT_LOG"
OPEN_CODE_STATUS="${PIPESTATUS[0]}"
set -e

python3 - "$EVENT_META" "$OPEN_CODE_STATUS" "$EVENT_LOG" <<'PY'
import json, sys
from datetime import datetime, timezone

path, exit_code, log = sys.argv[1:]
with open(path, encoding="utf-8") as f:
    event = json.load(f)

event["event_type"] = "worker_launch_finished"
event["finished_at"] = datetime.now(timezone.utc).isoformat()
event["opencode_exit_code"] = int(exit_code)
event["audit_log"] = log
event["status"] = "completed_process" if int(exit_code) == 0 else "failed_process"

with open(path, "w", encoding="utf-8") as f:
    json.dump(event, f, indent=2)
    f.write("\n")
PY

echo
echo "OpenCode process exit code: $OPEN_CODE_STATUS"
echo "Audit log: $EVENT_LOG"
echo "Event metadata: $EVENT_META"
echo "Inspect the worker diff before any integration:"
echo "  git -C '$WORKTREE' status"
echo "  git -C '$WORKTREE' diff main...HEAD"
echo "  git -C '$WORKTREE' log --oneline main..HEAD"

exit "$OPEN_CODE_STATUS"
