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
