#!/usr/bin/env bash
set -Eeuo pipefail
umask 077

ROOT="$(git rev-parse --show-toplevel)"
EXPECTED="/home/thard/az_kinnect_comfyUI"

usage() {
  cat <<'EOF'
Usage:
  scripts/submit_for_review.sh --task TASK-ID --status-file PATH

Example:
  scripts/submit_for_review.sh \
    --task CAPTURE-001 \
    --status-file /home/thard/az_kinnect_comfyUI.worktrees/capture/worker_status.json

This command validates a completed worker result and creates a pending human-review
record. It never merges, deploys, or launches another agent.
EOF
}

TASK_ID=""
STATUS_FILE=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --task)
      [[ $# -ge 2 ]] || { echo "--task requires a value." >&2; exit 2; }
      TASK_ID="$2"
      shift 2
      ;;
    --status-file)
      [[ $# -ge 2 ]] || { echo "--status-file requires a value." >&2; exit 2; }
      STATUS_FILE="$2"
      shift 2
      ;;
    --auto|--yes|-y|--merge|--deploy)
      echo "Refusing: this command only submits for validation and human review." >&2
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
  echo "Refusing: run only from $EXPECTED." >&2
  exit 1
}

[[ "$TASK_ID" =~ ^[A-Z]+-[0-9]{3}$ ]] || {
  echo "Refusing: invalid task ID." >&2
  exit 2
}

[[ -f "$ROOT/tasks/backlog/${TASK_ID}.json" ]] || {
  echo "Refusing: unknown backlog task: $TASK_ID" >&2
  exit 1
}

[[ -n "$STATUS_FILE" && -f "$STATUS_FILE" ]] || {
  echo "Refusing: status file does not exist: $STATUS_FILE" >&2
  exit 1
}

command -v python3 >/dev/null || {
  echo "Refusing: python3 is required." >&2
  exit 1
}

mkdir -p "$ROOT/state/results" "$ROOT/state/approvals"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
RESULT_FILE="$ROOT/state/results/${TASK_ID}_${STAMP}_worker_status.json"
APPROVAL_FILE="$ROOT/state/approvals/${TASK_ID}_${STAMP}_review.json"

python3 - "$STATUS_FILE" "$RESULT_FILE" "$TASK_ID" <<'PY'
import json
import sys
from pathlib import Path

source = Path(sys.argv[1])
target = Path(sys.argv[2])
expected_task_id = sys.argv[3]

try:
    payload = json.loads(source.read_text(encoding="utf-8"))
except json.JSONDecodeError as exc:
    raise SystemExit(f"Refusing: worker status is not valid JSON: {exc}")

if not isinstance(payload, dict):
    raise SystemExit("Refusing: worker status must be one JSON object.")

if payload.get("task_id") != expected_task_id:
    raise SystemExit(
        f"Refusing: status task_id {payload.get('task_id')!r} "
        f"does not match {expected_task_id!r}."
    )

target.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
print(target)
PY

echo "Copied worker status to runtime evidence:"
echo "  $RESULT_FILE"

if ! python3 "$ROOT/scripts/validate_worker_result.py" \
  --task "$TASK_ID" \
  --status-file "$RESULT_FILE"; then
  echo
  echo "Validation failed. No approval record was created; no merge occurred." >&2
  exit 1
fi

REVIEW_RECORD="$(find "$ROOT/state/review" -maxdepth 1 \
  -type f -name "${TASK_ID}_*_validated.json" -printf '%T@ %p\n' \
  | sort -nr | head -n 1 | cut -d' ' -f2-)"

[[ -n "$REVIEW_RECORD" && -f "$REVIEW_RECORD" ]] || {
  echo "Validation passed but review record was not found; refusing approval creation." >&2
  exit 1
}

python3 - "$APPROVAL_FILE" "$TASK_ID" "$RESULT_FILE" "$REVIEW_RECORD" <<'PY'
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

output = Path(sys.argv[1])
task_id = sys.argv[2]
result_file = Path(sys.argv[3])
review_record = Path(sys.argv[4])

review = json.loads(review_record.read_text(encoding="utf-8"))
approval = {
    "approval_id": output.stem,
    "task_id": task_id,
    "status": "pending_human_review",
    "requested_action": "Review validated worker branch; explicitly approve or reject integration.",
    "worker_branch": review["worker_branch"],
    "commit": review["commit"],
    "changed_files": review["changed_files"],
    "worker_status_evidence": str(result_file),
    "validation_evidence": str(review_record),
    "created_at": datetime.now(timezone.utc).isoformat(),
    "constraints": [
        "No merge has occurred.",
        "No deployment has occurred.",
        "No follow-up worker was launched.",
        "Explicit human approval remains required."
    ]
}
output.write_text(json.dumps(approval, indent=2) + "\n", encoding="utf-8")
print(output)
PY

echo
echo "SUBMISSION VALIDATED"
echo "Pending human-review record:"
echo "  $APPROVAL_FILE"
echo
echo "No branch was merged. No deployment occurred. No new agent was launched."
