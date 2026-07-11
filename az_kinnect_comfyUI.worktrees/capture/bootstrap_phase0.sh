#!/usr/bin/env bash
set -Eeuo pipefail
umask 077

ROOT="$(pwd -P)"
EXPECTED="/home/thard/az_kinnect_comfyUI"

if [[ "$ROOT" != "$EXPECTED" ]]; then
  echo "Refusing: expected $EXPECTED, got $ROOT" >&2
  exit 1
fi

if [[ -e ".phase0_bootstrapped" ]]; then
  echo "Phase 0 already bootstrapped. Nothing changed."
  exit 0
fi

command -v git >/dev/null || {
  echo "Git is required but not installed." >&2
  exit 1
}

mkdir -p \
  .opencode/agents \
  .opencode/skills \
  contracts \
  docs \
  fixtures/depth \
  fixtures/skeletons \
  orchestrator \
  scripts \
  state/approvals \
  state/audit \
  state/events \
  tests \
  src/azure_kinect_comfyui \
  worktrees

cat > .gitignore <<'EOF'
.venv/
__pycache__/
*.py[cod]
.pytest_cache/
.ruff_cache/
.mypy_cache/
coverage.xml
htmlcov/
state/*.db
state/events/*
state/audit/*
state/approvals/*
!state/.gitkeep
!state/events/.gitkeep
!state/audit/.gitkeep
!state/approvals/.gitkeep
.env
.env.*
*.k4a
*.mkv
*.npy
*.npz
*.onnx
*.safetensors
models/
output/
EOF

touch state/.gitkeep state/approvals/.gitkeep state/audit/.gitkeep state/events/.gitkeep

cat > AGENTS.md <<'EOF'
# Azure Kinect ComfyUI Project Constitution

## Mission
Build a hardware-independent Phase 0 foundation for an Azure Kinect to
ComfyUI pose/depth bridge. Live device capture is out of scope until explicitly
approved after hardware connectivity is available.

## Non-negotiable safety rules
1. Work only inside this repository and the assigned Git worktree.
2. Never access /mnt/f, other project directories, user home data, secrets,
   model directories, ComfyUI installations, or hardware devices unless a task
   explicitly grants access and a human approval token exists.
3. Never run sudo, package-manager installs, driver/firmware actions, service
   changes, network publishing, git push, git merge, git reset --hard, or
   destructive deletion.
4. Never edit AGENTS.md, opencode.json, .opencode/, contracts/, scripts/policy*,
   or orchestrator policy files unless the task explicitly owns that path and a
   human approval token is present.
5. One worker owns one worktree and one declared path scope. Do not modify files
   outside owned_paths. Do not inspect other worker worktrees.
6. Do not change shared interfaces opportunistically. Emit
   BLOCKED_INTERFACE_CHANGE with options and a recommendation.
7. Use synthetic fixtures only. Do not claim hardware, depth alignment, body
   tracking, or FLUX/Klein behavior was tested without an artifact proving it.
8. Make small atomic changes. Run only task-approved tests. Report the exact
   commit SHA and structured status before declaring a task complete.
9. Never fabricate test results, SDK behavior, model availability, or source
   citations. State uncertainty and request an approval or research task.

## Required worker result
Every worker completion must include:
- task_id and status: completed | blocked | needs_approval | failed
- scope actually changed
- files_changed
- tests run and exact results
- commit SHA
- known risks and next action
EOF

cat > opencode.json <<'EOF'
{
  "$schema": "https://opencode.ai/config.json",
  "share": "disabled",
  "autoupdate": "notify",
  "default_agent": "orchestrator",
  "instructions": ["AGENTS.md"],
  "watcher": {
    "ignore": [
      ".git/**",
      ".venv/**",
      "state/**",
      "worktrees/**",
      "models/**",
      "output/**"
    ]
  },
  "permission": {
    "external_directory": "deny",
    "webfetch": "ask",
    "websearch": "ask",
    "question": "allow",
    "doom_loop": "ask",
    "task": "deny",
    "bash": {
      "*": "ask"
    },
    "edit": {
      "*": "ask"
    }
  },
  "agent": {
    "orchestrator": {
      "description": "Read-only project planner and dispatcher. It never edits, merges, installs, or deploys.",
      "mode": "primary",
      "model": "REPLACE_WITH_STRONG_REASONING_MODEL",
      "temperature": 0.1,
      "maxSteps": 12,
      "prompt": ".opencode/agents/orchestrator.md",
      "permission": {
        "read": "allow",
        "glob": "allow",
        "grep": "allow",
        "list": "allow",
        "edit": "deny",
        "bash": {
          "*": "deny",
          "git status*": "allow",
          "git log*": "allow",
          "git diff*": "allow"
        },
        "task": {
          "capture-worker": "allow",
          "pose-worker": "allow",
          "comfy-worker": "allow",
          "reviewer": "allow"
        }
      }
    }
  }
}
EOF

cat > .opencode/agents/orchestrator.md <<'EOF'
---
description: Read-only orchestrator for the Azure Kinect ComfyUI project
mode: primary
hidden: false
---

You are the orchestrator. You plan, delegate, inspect worker reports, and request
human decisions. You NEVER edit files, run package installations, merge branches,
push Git, deploy, access hardware, or override policy.

Before delegating:
1. Read AGENTS.md and contracts/task.schema.json.
2. Ensure every task has one owner, explicit owned_paths, acceptance criteria,
   test commands, maximum attempts, and an approval requirement if applicable.
3. Prefer parallel tasks only when owned_paths do not overlap.
4. Give each worker only the minimum relevant context.
5. If an interface or policy change is needed, create a needs_approval request.

Worker retry policy:
- One routine repair attempt is allowed for a deterministic test/lint failure.
- After two failed attempts, stop and request human review.
- Never silently upgrade a model, expand scope, grant permissions, install
  dependencies, or modify shared contracts.
EOF

cat > .opencode/agents/capture-worker.md <<'EOF'
---
description: Builds mocked Azure Kinect frame-source abstractions only
mode: subagent
hidden: true
temperature: 0.2
maxSteps: 18
permission:
  external_directory: deny
  task: deny
  webfetch: ask
  websearch: ask
  bash:
    "*": deny
    "git status*": allow
    "git diff*": allow
    "git add src/azure_kinect_comfyui/capture/* tests/capture/* fixtures/*": allow
    "git commit -m *": ask
    "python -m pytest tests/capture/*": allow
  edit:
    "*": deny
    "src/azure_kinect_comfyui/capture/**": allow
    "tests/capture/**": allow
    "fixtures/**": allow
---

You own only mocked/replay capture code. Do not import or install Azure Kinect SDKs.
Implement against synthetic fixtures and the project contracts. Never access hardware.
EOF

cat > .opencode/agents/pose-worker.md <<'EOF'
---
description: Builds Kinect skeleton remap and pose-map rendering against fixtures
mode: subagent
hidden: true
temperature: 0.2
maxSteps: 22
permission:
  external_directory: deny
  task: deny
  webfetch: ask
  websearch: ask
  bash:
    "*": deny
    "git status*": allow
    "git diff*": allow
    "git add src/azure_kinect_comfyui/pose/* tests/pose/* fixtures/*": allow
    "git commit -m *": ask
    "python -m pytest tests/pose/*": allow
  edit:
    "*": deny
    "src/azure_kinect_comfyui/pose/**": allow
    "tests/pose/**": allow
    "fixtures/**": allow
---

You own only skeleton mapping and deterministic pose rendering. Do not modify capture,
ComfyUI, FLUX, shared contracts, or project configuration. Treat ambiguous mappings
as BLOCKED_INTERFACE_CHANGE requests rather than guessing.
EOF

cat > .opencode/agents/comfy-worker.md <<'EOF'
---
description: Builds ComfyUI node scaffolding using mock-file input only
mode: subagent
hidden: true
temperature: 0.2
maxSteps: 20
permission:
  external_directory: deny
  task: deny
  webfetch: ask
  websearch: ask
  bash:
    "*": deny
    "git status*": allow
    "git diff*": allow
    "git add src/azure_kinect_comfyui/comfy/* tests/comfy/*": allow
    "git commit -m *": ask
    "python -m pytest tests/comfy/*": allow
  edit:
    "*": deny
    "src/azure_kinect_comfyui/comfy/**": allow
    "tests/comfy/**": allow
---

You own only mock-backed ComfyUI node scaffolding. Do not write into an installed
ComfyUI directory, download models, or change FLUX/Klein workflow behavior.
EOF

cat > .opencode/agents/reviewer.md <<'EOF'
---
description: Read-only verifier for task contracts, diffs, and test evidence
mode: subagent
hidden: true
temperature: 0.1
maxSteps: 12
permission:
  read: allow
  glob: allow
  grep: allow
  list: allow
  edit: deny
  external_directory: deny
  task: deny
  webfetch: ask
  websearch: ask
  bash:
    "*": deny
    "git status*": allow
    "git diff*": allow
    "git show*": allow
    "python -m pytest tests/*": allow
---

You are an independent reviewer. Never modify files or approve your own work.
Verify path ownership, test evidence, contract compliance, and unsupported claims.
Return PASS, FAIL, or NEEDS_HUMAN_DECISION with concise evidence.
EOF

cat > contracts/task.schema.json <<'EOF'
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "Agent Task Contract",
  "type": "object",
  "required": [
    "task_id", "owner", "objective", "owned_paths",
    "acceptance_criteria", "allowed_tests", "max_attempts"
  ],
  "properties": {
    "task_id": { "type": "string", "pattern": "^[A-Z]+-[0-9]{3}$" },
    "owner": {
      "type": "string",
      "enum": ["capture-worker", "pose-worker", "comfy-worker", "reviewer"]
    },
    "objective": { "type": "string", "minLength": 20 },
    "owned_paths": { "type": "array", "minItems": 1, "items": { "type": "string" } },
    "read_only_paths": { "type": "array", "items": { "type": "string" } },
    "forbidden_paths": { "type": "array", "items": { "type": "string" } },
    "acceptance_criteria": { "type": "array", "minItems": 1, "items": { "type": "string" } },
    "allowed_tests": { "type": "array", "items": { "type": "string" } },
    "max_attempts": { "type": "integer", "minimum": 1, "maximum": 2 },
    "requires_human_approval": { "type": "boolean", "default": false }
  },
  "additionalProperties": false
}
EOF

cat > contracts/status.schema.json <<'EOF'
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "Worker Status Contract",
  "type": "object",
  "required": [
    "task_id", "status", "summary", "files_changed",
    "tests", "commit", "risks", "next_action"
  ],
  "properties": {
    "task_id": { "type": "string" },
    "status": {
      "type": "string",
      "enum": ["completed", "blocked", "needs_approval", "failed"]
    },
    "summary": { "type": "string" },
    "files_changed": { "type": "array", "items": { "type": "string" } },
    "tests": { "type": "array", "items": { "type": "object" } },
    "commit": { "type": "string" },
    "risks": { "type": "array", "items": { "type": "string" } },
    "next_action": { "type": "string" }
  },
  "additionalProperties": false
}
EOF

cat > docs/PHASE0.md <<'EOF'
# Phase 0: Hardware-independent foundation

## In scope
- Agent orchestration safety harness
- Synthetic KinectFrame fixtures
- Mock/replay frame source
- Skeleton remapping and pose rendering
- Mock-backed ComfyUI custom-node package scaffolding
- Unit tests and contract tests

## Explicitly out of scope
- Azure Kinect SDK/driver install
- Live camera access
- Kinect hardware validation
- ComfyUI installation/deployment
- FLUX.2 Klein model download or inference
- Any changes under /mnt/f

## Human approval required
- Dependency or SDK installation
- Any hardware/device access
- Interface contract changes
- Git branch merge
- Deployment into ComfyUI
EOF

cat > scripts/check_root.sh <<'EOF'
#!/usr/bin/env bash
set -Eeuo pipefail
ROOT="$(git rev-parse --show-toplevel)"
EXPECTED="/home/thard/az_kinnect_comfyUI"
[[ "$ROOT" == "$EXPECTED" ]] || {
  echo "Wrong repository root: $ROOT" >&2
  exit 1
}
echo "Project root verified: $ROOT"
EOF
chmod +x scripts/check_root.sh

cat > scripts/request_approval.sh <<'EOF'
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
EOF
chmod +x scripts/request_approval.sh

git init -q
git branch -M main
git add .
git commit -qm "chore: initialize Phase 0 safe agent foundation"
git tag phase0-foundation

touch .phase0_bootstrapped
echo
echo "Phase 0 foundation created successfully."
echo "Next: inspect with 'git status' and 'find . -maxdepth 3 -type f | sort'."
