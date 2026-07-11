"""ComfyUI custom-node package for Azure Kinect pose/depth bridge.

The module exposes ``NODE_CLASS_MAPPINGS`` and
``NODE_DISPLAY_NAME_MAPPINGS`` using ComfyUI-compatible registration
structures. This repository does not install, copy, or symlink the package
into any ComfyUI directory.

All nodes are mock-backed: they read from synthetic JSON fixtures only.
"""

from __future__ import annotations

from .nodes import AzureKinectMockFrame, AzureKinectPoseOverlay

# ---------------------------------------------------------------------------
# ComfyUI registration contract
# ---------------------------------------------------------------------------

NODE_CLASS_MAPPINGS = {
    "AzureKinectMockFrame": AzureKinectMockFrame,
    "AzureKinectPoseOverlay": AzureKinectPoseOverlay,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "AzureKinectMockFrame": "Azure Kinect Mock Frame",
    "AzureKinectPoseOverlay": "Azure Kinect Pose Overlay",
}

__all__ = [
    "NODE_CLASS_MAPPINGS",
    "NODE_DISPLAY_NAME_MAPPINGS",
    "AzureKinectMockFrame",
    "AzureKinectPoseOverlay",
]
