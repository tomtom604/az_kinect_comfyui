"""Hardware-independent KinectFrame data model.

This module defines the typed contract for a single captured frame from an
Azure Kinect device.  It is deliberately free of any Azure Kinect SDK imports
so that it can be exercised entirely with synthetic fixtures during Phase 0.
"""

from __future__ import annotations

import enum
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class TrackingState(enum.IntEnum):
    """Represents the tracking confidence for a joint or the overall frame."""
    NOT_TRACKED = 0
    INFERRED = 1
    TRACKED = 2


class JointId(enum.IntEnum):
    """Azure Kinect body-tracking joint identifiers (2020 SDK mapping)."""
    PELVIS = 0
    SPINE_NAVEL = 1
    SPINE_CHEST = 2
    NECK = 3
    CLAVICLE_LEFT = 4
    SHOULDER_LEFT = 5
    ELBOW_LEFT = 6
    WRIST_LEFT = 7
    HAND_LEFT = 8
    HANDTIP_LEFT = 9
    THUMB_LEFT = 10
    CLAVICLE_RIGHT = 11
    SHOULDER_RIGHT = 12
    ELBOW_RIGHT = 13
    WRIST_RIGHT = 14
    HAND_RIGHT = 15
    HANDTIP_RIGHT = 16
    THUMB_RIGHT = 17
    HIP_LEFT = 18
    KNEE_LEFT = 19
    ANKLE_LEFT = 20
    FOOT_LEFT = 21
    HIP_RIGHT = 22
    KNEE_RIGHT = 23
    ANKLE_RIGHT = 24
    FOOT_RIGHT = 25
    HEAD = 26
    NOSE = 27
    EYE_LEFT = 28
    EAR_LEFT = 29
    EYE_RIGHT = 30
    EAR_RIGHT = 31
    COUNT = 32


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Joint:
    """A single skeletal joint with 3-D position and tracking state."""
    joint_id: JointId
    position: Tuple[float, float, float]  # (x, y, z) in metres
    state: TrackingState = TrackingState.NOT_TRACKED


@dataclass(frozen=True)
class Calibration:
    """Intrinsic / extrinsic calibration metadata for a frame."""
    color_width: int = 1920
    color_height: int = 1080
    depth_width: int = 640
    depth_height: int = 576
    color_focal_length: Tuple[float, float] = (0.0, 0.0)
    depth_focal_length: Tuple[float, float] = (0.0, 0.0)
    depth_mode: str = "NFOV_UNBINNED"
    color_format: str = "BGRA32"
    extra: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class KinectFrame:
    """A single hardware-independent Kinect capture frame.

    Attributes
    ----------
    frame_id : int
        Monotonically increasing sequence number.
    timestamp_us : int
        Capture timestamp in microseconds.
    color : Optional[List[List[List[int]]]]
        Synthetic colour image as H×W×C pixel values (BGRA).  ``None`` when
        the colour camera is unavailable.
    depth : Optional[List[List[int]]]
        Synthetic depth image as H×W millimetre values.  ``None`` when the
        depth camera is unavailable.
    joints : Dict[int, Joint]
        Mapping from ``JointId`` value to ``Joint`` for the tracked body.
    tracking_state : TrackingState
        Overall body-tracking state for this frame.
    calibration : Calibration
        Calibration metadata associated with this frame.
    body_id : Optional[int]
        Opaque body-tracking identifier assigned by the runtime.
    """
    frame_id: int
    timestamp_us: int
    color: Optional[List[List[List[int]]]] = None
    depth: Optional[List[List[int]]] = None
    joints: Dict[int, Joint] = field(default_factory=dict)
    tracking_state: TrackingState = TrackingState.NOT_TRACKED
    calibration: Calibration = field(default_factory=Calibration)
    body_id: Optional[int] = None
