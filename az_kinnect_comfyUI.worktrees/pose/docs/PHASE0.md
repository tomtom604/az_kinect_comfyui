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
