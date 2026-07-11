"""Tests for the Kinect-to-BODY_25 mapping module."""

import pytest

from azure_kinect_comfyui.pose.mapping import (
    BODY_25_NAMES,
    BODY_25_SKELETON,
    BODY_25_SYNTHETIC_INDICES,
    KINECT_OMITTED_JOINTS,
    Body25Keypoint,
    Body25Pose,
    KinectToBody25Mapper,
)
from azure_kinect_comfyui.capture.models import (
    Joint,
    JointId,
    KinectFrame,
    TrackingState,
)


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

class TestConstants:
    def test_body25_names_count(self):
        assert len(BODY_25_NAMES) == 25

    def test_body25_names_first(self):
        assert BODY_25_NAMES[0] == "Nose"
        assert BODY_25_NAMES[1] == "Neck"

    def test_body25_names_last(self):
        assert BODY_25_NAMES[24] == "Right Heel"

    def test_body25_skeleton_count(self):
        assert len(BODY_25_SKELETON) == 24

    def test_body25_skeleton_connections(self):
        # Nose -> Neck
        assert (0, 1) in BODY_25_SKELETON
        # Neck -> Right Shoulder
        assert (1, 2) in BODY_25_SKELETON
        # Mid Hip -> Right Hip
        assert (8, 9) in BODY_25_SKELETON

    def test_skeleton_indices_valid(self):
        for from_idx, to_idx in BODY_25_SKELETON:
            assert 0 <= from_idx < 25
            assert 0 <= to_idx < 25

    def test_synthetic_indices(self):
        assert 8 in BODY_25_SYNTHETIC_INDICES   # Mid Hip
        assert 19 in BODY_25_SYNTHETIC_INDICES  # Left Big Toe
        assert 21 in BODY_25_SYNTHETIC_INDICES  # Left Heel
        assert 24 in BODY_25_SYNTHETIC_INDICES  # Right Heel
        assert len(BODY_25_SYNTHETIC_INDICES) == 7

    def test_omitted_joints(self):
        assert 1 in KINECT_OMITTED_JOINTS   # SPINE_NAVEL
        assert 8 in KINECT_OMITTED_JOINTS   # HAND_LEFT
        assert 26 in KINECT_OMITTED_JOINTS  # HEAD
        assert len(KINECT_OMITTED_JOINTS) == 13


# ---------------------------------------------------------------------------
# Body25Keypoint
# ---------------------------------------------------------------------------

class TestBody25Keypoint:
    def test_kinect_keypoint(self):
        kp = Body25Keypoint(
            index=0, name="Nose", x=320.0, y=200.0,
            confidence=1.0, source="kinect", source_joint_id=27,
        )
        assert kp.index == 0
        assert kp.source == "kinect"
        assert kp.source_joint_id == 27
        assert kp.synthetic_reason is None

    def test_synthetic_keypoint(self):
        kp = Body25Keypoint(
            index=8, name="Mid Hip", x=320.0, y=300.0,
            confidence=0.8, source="synthetic",
            synthetic_reason="midpoint of HIP_LEFT and HIP_RIGHT",
        )
        assert kp.source == "synthetic"
        assert kp.source_joint_id is None
        assert "midpoint" in kp.synthetic_reason

    def test_frozen(self):
        kp = Body25Keypoint(
            index=0, name="Nose", x=0.0, y=0.0,
            confidence=1.0, source="kinect",
        )
        with pytest.raises(AttributeError):
            kp.x = 100.0


# ---------------------------------------------------------------------------
# Body25Pose
# ---------------------------------------------------------------------------

class TestBody25Pose:
    def _make_keypoints(self, count=25):
        return tuple(
            Body25Keypoint(
                index=i, name=f"KP{i}", x=320.0, y=240.0,
                confidence=1.0, source="kinect",
            )
            for i in range(count)
        )

    def test_valid_pose(self):
        pose = Body25Pose(keypoints=self._make_keypoints())
        assert len(pose.keypoints) == 25

    def test_wrong_count_raises(self):
        with pytest.raises(ValueError, match="exactly 25"):
            Body25Pose(keypoints=self._make_keypoints(24))

    def test_frozen(self):
        pose = Body25Pose(keypoints=self._make_keypoints())
        with pytest.raises(AttributeError):
            pose.keypoints = ()


# ---------------------------------------------------------------------------
# KinectToBody25Mapper
# ---------------------------------------------------------------------------

class TestMapperProjection:
    def test_centre_projection(self):
        mapper = KinectToBody25Mapper(fx=500, fy=500, cx=320, cy=288)
        # Point straight ahead at z=2m should project to centre
        px, py = mapper.project((0.0, 0.0, 2.0))
        assert px == pytest.approx(320.0)
        assert py == pytest.approx(288.0)

    def test_zero_z_clamps_to_centre(self):
        mapper = KinectToBody25Mapper()
        px, py = mapper.project((0.0, 0.0, 0.0))
        assert px == 320.0
        assert py == 288.0

    def test_negative_z_clamps_to_centre(self):
        mapper = KinectToBody25Mapper()
        px, py = mapper.project((0.0, 0.0, -1.0))
        assert px == 320.0
        assert py == 288.0


class TestMapperNeutralStanding:
    def test_full_pose_from_neutral(self, neutral_standing_kinect_frame):
        mapper = KinectToBody25Mapper()
        pose = mapper.map_frame(neutral_standing_kinect_frame)

        assert len(pose.keypoints) == 25
        assert pose.frame_id == 1

    def test_nose_mapped_from_kinect(self, neutral_standing_kinect_frame):
        mapper = KinectToBody25Mapper()
        pose = mapper.map_frame(neutral_standing_kinect_frame)

        nose = pose.keypoints[0]
        assert nose.name == "Nose"
        assert nose.source == "kinect"
        assert nose.source_joint_id == 27  # NOSE
        assert nose.confidence == 1.0  # TRACKED

    def test_neck_mapped(self, neutral_standing_kinect_frame):
        mapper = KinectToBody25Mapper()
        pose = mapper.map_frame(neutral_standing_kinect_frame)

        neck = pose.keypoints[1]
        assert neck.name == "Neck"
        assert neck.source == "kinect"
        assert neck.source_joint_id == 3  # NECK

    def test_mid_hip_is_synthetic(self, neutral_standing_kinect_frame):
        mapper = KinectToBody25Mapper()
        pose = mapper.map_frame(neutral_standing_kinect_frame)

        mid_hip = pose.keypoints[8]
        assert mid_hip.name == "Mid Hip"
        assert mid_hip.source == "synthetic"
        assert mid_hip.confidence == 1.0  # Both hips tracked

    def test_toes_have_zero_confidence(self, neutral_standing_kinect_frame):
        mapper = KinectToBody25Mapper()
        pose = mapper.map_frame(neutral_standing_kinect_frame)

        for idx in (19, 20, 22, 23):
            kp = pose.keypoints[idx]
            assert kp.confidence == 0.0
            assert kp.source == "synthetic"

    def test_heel_ambiguous_documented(self, neutral_standing_kinect_frame):
        mapper = KinectToBody25Mapper()
        pose = mapper.map_frame(neutral_standing_kinect_frame)

        left_heel = pose.keypoints[21]
        assert left_heel.source == "synthetic"
        assert "ambiguous" in left_heel.synthetic_reason.lower()

        right_heel = pose.keypoints[24]
        assert right_heel.source == "synthetic"
        assert "ambiguous" in right_heel.synthetic_reason.lower()

    def test_deterministic_output(self, neutral_standing_kinect_frame):
        mapper = KinectToBody25Mapper()
        pose1 = mapper.map_frame(neutral_standing_kinect_frame)
        pose2 = mapper.map_frame(neutral_standing_kinect_frame)

        assert pose1.keypoints == pose2.keypoints


class TestMapperMissingJoints:
    def test_missing_joint_has_zero_confidence(self, missing_joints_kinect_frame):
        mapper = KinectToBody25Mapper()
        pose = mapper.map_frame(missing_joints_kinect_frame)

        # Right Shoulder (B25 idx 2) <- Kinect 12, which is present
        r_shoulder = pose.keypoints[2]
        assert r_shoulder.confidence == 1.0

        # Left Shoulder (B25 idx 5) <- Kinect 5, which is MISSING
        l_shoulder = pose.keypoints[5]
        assert l_shoulder.confidence == 0.0

    def test_inferred_joint_has_half_confidence(self, missing_joints_kinect_frame):
        mapper = KinectToBody25Mapper()
        pose = mapper.map_frame(missing_joints_kinect_frame)

        # Left Elbow (B25 idx 6) <- Kinect 6, state=INFERRED
        l_elbow = pose.keypoints[6]
        assert l_elbow.confidence == pytest.approx(0.5)

    def test_mid_hip_with_missing_hip(self, missing_joints_kinect_frame):
        mapper = KinectToBody25Mapper()
        pose = mapper.map_frame(missing_joints_kinect_frame)

        # Both hips are present in missing_joints fixture, so mid_hip should work
        mid_hip = pose.keypoints[8]
        assert mid_hip.source == "synthetic"
        assert mid_hip.confidence == 1.0


class TestMapperEmptyFrame:
    def test_no_joints_produces_zero_confidence(self):
        frame = KinectFrame(frame_id=99, timestamp_us=0)
        mapper = KinectToBody25Mapper()
        pose = mapper.map_frame(frame)

        assert len(pose.keypoints) == 25
        for kp in pose.keypoints:
            assert kp.confidence == 0.0
