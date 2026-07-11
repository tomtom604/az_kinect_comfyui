#!/usr/bin/env bash
set -Eeuo pipefail

ROOT="$(git rev-parse --show-toplevel)"
EXPECTED="/home/thard/az_kinnect_comfyUI"
WT_ROOT="/home/thard/az_kinnect_comfyUI.worktrees"

[[ "$ROOT" == "$EXPECTED" ]] || {
  echo "Refusing: run from $EXPECTED" >&2
  exit 1
}

if [[ -n "$(git status --porcelain)" ]]; then
  echo "Refusing: main worktree is not clean. Commit or stash changes first." >&2
  exit 1
fi

mkdir -p "$WT_ROOT"

declare -A BRANCHES=(
  [capture]="agent/capture"
  [pose]="agent/pose"
  [comfy]="agent/comfy"
  [review]="agent/review"
)

for worker in capture pose comfy review; do
  path="$WT_ROOT/$worker"
  branch="${BRANCHES[$worker]}"

  if [[ -d "$path" ]]; then
    echo "Already exists: $path"
    continue
  fi

  if git show-ref --verify --quiet "refs/heads/$branch"; then
    git worktree add "$path" "$branch"
  else
    git worktree add -b "$branch" "$path" main
  fi
done

echo
git worktree list
