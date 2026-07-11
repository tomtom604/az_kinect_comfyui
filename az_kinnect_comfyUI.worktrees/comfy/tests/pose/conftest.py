from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
FIXTURES = ROOT / "fixtures" / "skeletons"

sys.path.insert(0, str(SRC))

from azure_kinect_comfyui.capture.models import Joint, JointId, KinectFrame, TrackingState


def _frame_from_fixture(filename: str, frame_id: int) -> KinectFrame:
    raw = json.loads((FIXTURES / filename).read_text(encoding="utf-8"))
    joints = {
        int(joint_id): Joint(
            joint_id=JointId(int(joint_id)),
            position=tuple(joint["position"]),
            state=TrackingState(joint["state"]),
        )
        for joint_id, joint in raw["joints_3d"].items()
    }
    return KinectFrame(
        frame_id=frame_id,
        timestamp_us=frame_id * 33_333,
        joints=joints,
        tracking_state=TrackingState.TRACKED,
    )


@pytest.fixture
def neutral_standing_kinect_frame() -> KinectFrame:
    return _frame_from_fixture("neutral_standing.json", frame_id=1)


@pytest.fixture
def missing_joints_kinect_frame() -> KinectFrame:
    return _frame_from_fixture("missing_joints.json", frame_id=2)
