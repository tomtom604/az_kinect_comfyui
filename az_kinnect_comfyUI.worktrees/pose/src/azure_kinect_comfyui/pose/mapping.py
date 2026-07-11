"""Documented Kinect 32-joint to OpenPose BODY_25 mapping.

Mapping reference
=================

Retained BODY_25 keypoints (direct Kinect source)
-------------------------------------------------
+-------+-------------------+------------------------+-------------------+
| B25 # | BODY_25 name      | Kinect JointId         | Kinect name       |
+-------+-------------------+------------------------+-------------------+
|   0   | Nose              | 27                     | NOSE              |
|   1   | Neck              | 3                      | NECK              |
|   2   | Right Shoulder    | 12                     | SHOULDER_RIGHT    |
|   3   | Right Elbow       | 13                     | ELBOW_RIGHT       |
|   4   | Right Wrist       | 14                     | WRIST_RIGHT       |
|   5   | Left Shoulder     | 5                      | SHOULDER_LEFT     |
|   6   | Left Elbow        | 6                      | ELBOW_LEFT        |
|   7   | Left Wrist        | 7                      | WRIST_LEFT        |
|   9   | Right Hip         | 22                     | HIP_RIGHT         |
|  10   | Right Knee        | 23                     | KNEE_RIGHT        |
|  11   | Right Ankle       | 24                     | ANKLE_RIGHT       |
|  12   | Left Hip          | 18                     | HIP_LEFT          |
|  13   | Left Knee         | 19                     | KNEE_LEFT         |
|  14   | Left Ankle        | 20                     | ANKLE_LEFT        |
|  15   | Right Eye         | 30                     | EYE_RIGHT         |
|  16   | Left Eye          | 28                     | EYE_LEFT          |
|  17   | Right Ear         | 31                     | EAR_RIGHT         |
|  18   | Left Ear          | 29                     | EAR_LEFT          |
+-------+-------------------+------------------------+-------------------+

Synthetic BODY_25 keypoints (no direct Kinect source)
-----------------------------------------------------
+-------+-------------------+---------------------------------------------+
| B25 # | BODY_25 name      | Derivation / reason                         |
+-------+-------------------+---------------------------------------------+
|   8   | Mid Hip           | Midpoint of HIP_LEFT (18) and HIP_RIGHT(22) |
|  19   | Left Big Toe      | Not available in Kinect skeleton            |
|  20   | Left Small Toe    | Not available in Kinect skeleton            |
|  21   | Left Heel         | Ambiguous: Kinect FOOT_LEFT (21) is centre  |
|       |                   | of foot, not heel.  Documented, not guessed.|
|  22   | Right Big Toe     | Not available in Kinect skeleton            |
|  23   | Right Small Toe   | Not available in Kinect skeleton            |
|  24   | Right Heel        | Ambiguous: Kinect FOOT_RIGHT (25) is centre |
|       |                   | of foot, not heel.  Documented, not guessed.|
+-------+-------------------+---------------------------------------------+

Omitted Kinect joints (not represented in BODY_25)
--------------------------------------------------
+------+-------------------+----------------------------------------------+
| K #  | Kinect name       | Reason                                       |
+------+-------------------+----------------------------------------------+
|  1   | SPINE_NAVEL       | Internal torso; no BODY_25 equivalent        |
|  2   | SPINE_CHEST       | Internal torso; no BODY_25 equivalent        |
|  4   | CLAVICLE_LEFT     | Internal shoulder; no BODY_25 equivalent     |
|  8   | HAND_LEFT         | Ambiguous hand mapping; documented, not used |
|  9   | HANDTIP_LEFT      | Ambiguous hand mapping; documented, not used |
| 10   | THUMB_LEFT        | Ambiguous hand mapping; documented, not used |
| 11   | CLAVICLE_RIGHT    | Internal shoulder; no BODY_25 equivalent     |
| 15   | HAND_RIGHT        | Ambiguous hand mapping; documented, not used |
| 16   | HANDTIP_RIGHT     | Ambiguous hand mapping; documented, not used |
| 17   | THUMB_RIGHT       | Ambiguous hand mapping; documented, not used |
| 21   | FOOT_LEFT         | Ambiguous foot mapping; documented, not used |
| 25   | FOOT_RIGHT        | Ambiguous foot mapping; documented, not used |
| 26   | HEAD              | BODY_25 uses Nose (27) instead               |
+------+-------------------+----------------------------------------------+

Ambiguous mappings (documented, NOT guessed)
--------------------------------------------
- Hand joints (HAND_*, HANDTIP_*, THUMB_*): Kinect provides 6 hand joints
  per side but BODY_25 has no hand keypoints.  These are omitted.
- Foot joints (FOOT_LEFT, FOOT_RIGHT): Kinect FOOT joints are at the centre
  of the foot.  BODY_25 heel/toe keypoints require sub-foot precision that
  Kinect does not provide.  These are marked synthetic with zero confidence.
- HEAD (26): BODY_25 has no HEAD keypoint; Nose (27) is used instead.
"""

from __future__ import annotations

import enum
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from azure_kinect_comfyui.capture.models import (
    Calibration,
    Joint,
    JointId,
    KinectFrame,
    TrackingState,
)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

BODY_25_NAMES: Tuple[str, ...] = (
    "Nose",
    "Neck",
    "Right Shoulder",
    "Right Elbow",
    "Right Wrist",
    "Left Shoulder",
    "Left Elbow",
    "Left Wrist",
    "Mid Hip",
    "Right Hip",
    "Right Knee",
    "Right Ankle",
    "Left Hip",
    "Left Knee",
    "Left Ankle",
    "Right Eye",
    "Left Eye",
    "Right Ear",
    "Left Ear",
    "Left Big Toe",
    "Left Small Toe",
    "Left Heel",
    "Right Big Toe",
    "Right Small Toe",
    "Right Heel",
)

BODY_25_SKELETON: Tuple[Tuple[int, int], ...] = (
    (0, 1),    # Nose -> Neck
    (1, 2),    # Neck -> Right Shoulder
    (2, 3),    # Right Shoulder -> Right Elbow
    (3, 4),    # Right Elbow -> Right Wrist
    (1, 5),    # Neck -> Left Shoulder
    (5, 6),    # Left Shoulder -> Left Elbow
    (6, 7),    # Left Elbow -> Left Wrist
    (1, 8),    # Neck -> Mid Hip
    (8, 9),    # Mid Hip -> Right Hip
    (9, 10),   # Right Hip -> Right Knee
    (10, 11),  # Right Knee -> Right Ankle
    (8, 12),   # Mid Hip -> Left Hip
    (12, 13),  # Left Hip -> Left Knee
    (13, 14),  # Left Knee -> Left Ankle
    (0, 15),   # Nose -> Right Eye
    (15, 17),  # Right Eye -> Right Ear
    (0, 16),   # Nose -> Left Eye
    (16, 18),  # Left Eye -> Left Ear
    (14, 21),  # Left Ankle -> Left Heel
    (21, 19),  # Left Heel -> Left Big Toe
    (21, 20),  # Left Heel -> Left Small Toe
    (11, 24),  # Right Ankle -> Right Heel
    (24, 22),  # Right Heel -> Right Big Toe
    (24, 23),  # Right Heel -> Right Small Toe
)

# BODY_25 indices that are synthetic (no direct Kinect joint source)
BODY_25_SYNTHETIC_INDICES: Tuple[int, ...] = (8, 19, 20, 21, 22, 23, 24)

# Kinect JointId values that are omitted from BODY_25
KINECT_OMITTED_JOINTS: Tuple[int, ...] = (
    1,   # SPINE_NAVEL
    2,   # SPINE_CHEST
    4,   # CLAVICLE_LEFT
    8,   # HAND_LEFT
    9,   # HANDTIP_LEFT
    10,  # THUMB_LEFT
    11,  # CLAVICLE_RIGHT
    15,  # HAND_RIGHT
    16,  # HANDTIP_RIGHT
    17,  # THUMB_RIGHT
    21,  # FOOT_LEFT
    25,  # FOOT_RIGHT
    26,  # HEAD
)

# Mapping: BODY_25 index -> Kinect JointId (or None for synthetic)
_BODY25_TO_KINECT: Dict[int, Optional[int]] = {
    0: 27,   # Nose <- NOSE
    1: 3,    # Neck <- NECK
    2: 12,   # Right Shoulder <- SHOULDER_RIGHT
    3: 13,   # Right Elbow <- ELBOW_RIGHT
    4: 14,   # Right Wrist <- WRIST_RIGHT
    5: 5,    # Left Shoulder <- SHOULDER_LEFT
    6: 6,    # Left Elbow <- ELBOW_LEFT
    7: 7,    # Left Wrist <- WRIST_LEFT
    8: None, # Mid Hip <- synthetic
    9: 22,   # Right Hip <- HIP_RIGHT
    10: 23,  # Right Knee <- KNEE_RIGHT
    11: 24,  # Right Ankle <- ANKLE_RIGHT
    12: 18,  # Left Hip <- HIP_LEFT
    13: 19,  # Left Knee <- KNEE_LEFT
    14: 20,  # Left Ankle <- ANKLE_LEFT
    15: 30,  # Right Eye <- EYE_RIGHT
    16: 28,  # Left Eye <- EYE_LEFT
    17: 31,  # Right Ear <- EAR_RIGHT
    18: 29,  # Left Ear <- EAR_LEFT
    19: None,  # Left Big Toe <- synthetic
    20: None,  # Left Small Toe <- synthetic
    21: None,  # Left Heel <- synthetic (ambiguous)
    22: None,  # Right Big Toe <- synthetic
    23: None,  # Right Small Toe <- synthetic
    24: None,  # Right Heel <- synthetic (ambiguous)
}

# Synthetic reasons keyed by BODY_25 index
_SYNTHETIC_REASONS: Dict[int, str] = {
    8: "midpoint of HIP_LEFT and HIP_RIGHT",
    19: "not available in Kinect skeleton",
    20: "not available in Kinect skeleton",
    21: "ambiguous: Kinect FOOT_LEFT is foot centre, not heel",
    22: "not available in Kinect skeleton",
    23: "not available in Kinect skeleton",
    24: "ambiguous: Kinect FOOT_RIGHT is foot centre, not heel",
}

# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Body25Keypoint:
    """A single BODY_25 keypoint with 2-D image coordinates and confidence."""
    index: int
    name: str
    x: float  # image-space x (pixels)
    y: float  # image-space y (pixels)
    confidence: float  # 0.0 - 1.0
    source: str  # "kinect" or "synthetic"
    source_joint_id: Optional[int] = None
    synthetic_reason: Optional[str] = None


@dataclass(frozen=True)
class Body25Pose:
    """A complete BODY_25 pose with exactly 25 keypoints."""
    keypoints: Tuple[Body25Keypoint, ...]
    frame_id: Optional[int] = None

    def __post_init__(self) -> None:
        if len(self.keypoints) != 25:
            raise ValueError(
                f"BODY_25 pose must have exactly 25 keypoints, "
                f"got {len(self.keypoints)}"
            )


# ---------------------------------------------------------------------------
# Mapper
# ---------------------------------------------------------------------------

# Default pinhole camera parameters for 3D -> 2D projection
_DEFAULT_FX: float = 500.0
_DEFAULT_FY: float = 500.0
_DEFAULT_CX: float = 320.0
_DEFAULT_CY: float = 288.0

# Confidence mapping from Kinect TrackingState
_STATE_CONFIDENCE: Dict[TrackingState, float] = {
    TrackingState.TRACKED: 1.0,
    TrackingState.INFERRED: 0.5,
    TrackingState.NOT_TRACKED: 0.0,
}


class KinectToBody25Mapper:
    """Converts a KinectFrame to a Body25Pose via documented mapping rules."""

    def __init__(
        self,
        fx: float = _DEFAULT_FX,
        fy: float = _DEFAULT_FY,
        cx: float = _DEFAULT_CX,
        cy: float = _DEFAULT_CY,
    ) -> None:
        self.fx = fx
        self.fy = fy
        self.cx = cx
        self.cy = cy

    def project(self, pos: Tuple[float, float, float]) -> Tuple[float, float]:
        """Pinhole projection: 3D metres -> 2D image pixels."""
        x, y, z = pos
        if z <= 0:
            return (self.cx, self.cy)
        px = (x / z) * self.fx + self.cx
        py = (y / z) * self.fy + self.cy
        return (px, py)

    def _joint_confidence(self, joint: Optional[Joint]) -> float:
        if joint is None:
            return 0.0
        return _STATE_CONFIDENCE.get(joint.state, 0.0)

    def map_frame(self, frame: KinectFrame) -> Body25Pose:
        """Map a KinectFrame to a Body25Pose."""
        keypoints: List[Body25Keypoint] = []

        for b25_idx in range(25):
            kinect_id = _BODY25_TO_KINECT[b25_idx]
            name = BODY_25_NAMES[b25_idx]

            if kinect_id is not None:
                # Direct Kinect source
                joint = frame.joints.get(kinect_id)
                conf = self._joint_confidence(joint)
                if joint is not None:
                    px, py = self.project(joint.position)
                else:
                    px, py = self.cx, self.cy
                    conf = 0.0
                keypoints.append(Body25Keypoint(
                    index=b25_idx,
                    name=name,
                    x=round(px, 4),
                    y=round(py, 4),
                    confidence=conf,
                    source="kinect",
                    source_joint_id=kinect_id,
                ))
            else:
                # Synthetic keypoint
                reason = _SYNTHETIC_REASONS.get(b25_idx, "synthetic")
                if b25_idx == 8:
                    # Mid Hip: midpoint of HIP_LEFT (18) and HIP_RIGHT (22)
                    hip_l = frame.joints.get(18)
                    hip_r = frame.joints.get(22)
                    if hip_l is not None and hip_r is not None:
                        mid_pos = (
                            (hip_l.position[0] + hip_r.position[0]) / 2,
                            (hip_l.position[1] + hip_r.position[1]) / 2,
                            (hip_l.position[2] + hip_r.position[2]) / 2,
                        )
                        px, py = self.project(mid_pos)
                        conf = min(
                            self._joint_confidence(hip_l),
                            self._joint_confidence(hip_r),
                        )
                    else:
                        px, py = self.cx, self.cy
                        conf = 0.0
                else:
                    # Toe/heel keypoints: zero confidence, centre position
                    px, py = self.cx, self.cy
                    conf = 0.0

                keypoints.append(Body25Keypoint(
                    index=b25_idx,
                    name=name,
                    x=round(px, 4),
                    y=round(py, 4),
                    confidence=conf,
                    source="synthetic",
                    synthetic_reason=reason,
                ))

        return Body25Pose(
            keypoints=tuple(keypoints),
            frame_id=frame.frame_id,
        )
