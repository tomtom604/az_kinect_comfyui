"""Tests for the KinectFrame data model."""

import pytest

from azure_kinect_comfyui.capture.models import (
    Calibration,
    Joint,
    JointId,
    KinectFrame,
    TrackingState,
)


# ---------------------------------------------------------------------------
# TrackingState
# ---------------------------------------------------------------------------

class TestTrackingState:
    def test_enum_values(self):
        assert TrackingState.NOT_TRACKED == 0
        assert TrackingState.INFERRED == 1
        assert TrackingState.TRACKED == 2

    def test_from_int(self):
        assert TrackingState(0) is TrackingState.NOT_TRACKED
        assert TrackingState(1) is TrackingState.INFERRED
        assert TrackingState(2) is TrackingState.TRACKED


# ---------------------------------------------------------------------------
# JointId
# ---------------------------------------------------------------------------

class TestJointId:
    def test_count(self):
        assert JointId.COUNT == 32

    def test_key_joints(self):
        assert JointId.HEAD == 26
        assert JointId.PELVIS == 0
        assert JointId.HAND_LEFT == 8
        assert JointId.HAND_RIGHT == 15


# ---------------------------------------------------------------------------
# Joint
# ---------------------------------------------------------------------------

class TestJoint:
    def test_default_state(self):
        j = Joint(joint_id=JointId.HEAD, position=(0.0, 1.7, 2.0))
        assert j.state is TrackingState.NOT_TRACKED

    def test_tracked_joint(self):
        j = Joint(
            joint_id=JointId.HEAD,
            position=(0.0, 1.7, 2.0),
            state=TrackingState.TRACKED,
        )
        assert j.state is TrackingState.TRACKED
        assert j.position == (0.0, 1.7, 2.0)

    def test_frozen(self):
        j = Joint(joint_id=JointId.PELVIS, position=(0.0, 0.9, 2.0))
        with pytest.raises(AttributeError):
            j.position = (1.0, 1.0, 1.0)


# ---------------------------------------------------------------------------
# Calibration
# ---------------------------------------------------------------------------

class TestCalibration:
    def test_defaults(self):
        c = Calibration()
        assert c.color_width == 1920
        assert c.color_height == 1080
        assert c.depth_width == 640
        assert c.depth_height == 576
        assert c.depth_mode == "NFOV_UNBINNED"
        assert c.color_format == "BGRA32"

    def test_custom(self):
        c = Calibration(
            color_width=1280,
            color_height=720,
            depth_mode="WFOV_2X2BINNED",
        )
        assert c.color_width == 1280
        assert c.depth_mode == "WFOV_2X2BINNED"

    def test_frozen(self):
        c = Calibration()
        with pytest.raises(AttributeError):
            c.color_width = 640


# ---------------------------------------------------------------------------
# KinectFrame
# ---------------------------------------------------------------------------

class TestKinectFrame:
    def test_minimal_frame(self):
        f = KinectFrame(frame_id=1, timestamp_us=1000)
        assert f.frame_id == 1
        assert f.timestamp_us == 1000
        assert f.color is None
        assert f.depth is None
        assert f.joints == {}
        assert f.tracking_state is TrackingState.NOT_TRACKED
        assert f.body_id is None

    def test_full_frame(self):
        joints = {
            JointId.HEAD.value: Joint(
                joint_id=JointId.HEAD,
                position=(0.0, 1.7, 2.0),
                state=TrackingState.TRACKED,
            ),
        }
        cal = Calibration(color_width=1280, color_height=720)
        f = KinectFrame(
            frame_id=10,
            timestamp_us=5000,
            color=[[[100, 120, 140, 255]]],
            depth=[[1500]],
            joints=joints,
            tracking_state=TrackingState.TRACKED,
            calibration=cal,
            body_id=7,
        )
        assert f.frame_id == 10
        assert f.body_id == 7
        assert f.tracking_state is TrackingState.TRACKED
        assert len(f.joints) == 1
        assert f.color[0][0] == [100, 120, 140, 255]
        assert f.depth[0][0] == 1500

    def test_frozen(self):
        f = KinectFrame(frame_id=1, timestamp_us=0)
        with pytest.raises(AttributeError):
            f.frame_id = 2


class TestFullKinectJointSet:
    def test_face_joint_ids_complete_the_32_joint_contract(self):
        assert JointId.NOSE == 27
        assert JointId.EYE_LEFT == 28
        assert JointId.EAR_LEFT == 29
        assert JointId.EYE_RIGHT == 30
        assert JointId.EAR_RIGHT == 31
        assert JointId.COUNT == 32
