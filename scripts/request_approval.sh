#!/usr/bin/env bash
set -Eeuo pipefail
[[ $# -ge 2 ]] || {
  echo "Usage: $0 <category> <reason...>" >&2
  exit 2
}
ROOT="$(git rev-parse --show-toplevel)"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
ID="APR-${STAMP}-${RANDOM}"
OUT="$ROOT/state/approvals/${ID}.json"
python3 - "$OUT" "$1" "${*:2}" <<'PY'
import json, sys
from datetime import datetime, timezone
path, category, reason = sys.argv[1:]
payload = {
  "approval_id": path.rsplit("/", 1)[-1].removesuffix(".json"),
  "status": "pending",
  "category": category,
  "reason": reason,
  "created_at": datetime.now(timezone.utc).isoformat()
}
with open(path, "w", encoding="utf-8") as f:
  json.dump(payload, f, indent=2)
  f.write("\n")
print(path)
PY
