#!/usr/bin/env bash
set -Eeuo pipefail
ROOT="$(git rev-parse --show-toplevel)"
EXPECTED="/home/thard/az_kinnect_comfyUI"
[[ "$ROOT" == "$EXPECTED" ]] || {
  echo "Wrong repository root: $ROOT" >&2
  exit 1
}
echo "Project root verified: $ROOT"
