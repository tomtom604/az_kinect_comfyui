"""Kinect 32-joint to BODY_25 pose mapping and rendering.

This package provides:
- A documented, deterministic mapping from Azure Kinect 32-joint skeletons
  to OpenPose BODY_25-compatible intermediate keypoints.
- A pure-Python renderer that produces deterministic PPM pose-map images
  from BODY_25 keypoints, requiring no external dependencies.
"""

from azure_kinect_comfyui.pose.mapping import (
    BODY_25_NAMES,
    BODY_25_SKELETON,
    BODY_25_SYNTHETIC_INDICES,
    KINECT_OMITTED_JOINTS,
    Body25Keypoint,
    Body25Pose,
    KinectToBody25Mapper,
)
from azure_kinect_comfyui.pose.renderer import PoseRenderer

__all__ = [
    "BODY_25_NAMES",
    "BODY_25_SKELETON",
    "BODY_25_SYNTHETIC_INDICES",
    "KINECT_OMITTED_JOINTS",
    "Body25Keypoint",
    "Body25Pose",
    "KinectToBody25Mapper",
    "PoseRenderer",
]
