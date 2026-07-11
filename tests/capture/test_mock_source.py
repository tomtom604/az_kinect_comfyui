"""Tests for MockKinectSource: valid replay, exhaustion, tracking-lost."""

from pathlib import Path

import pytest

from azure_kinect_comfyui.capture.mock_source import MockKinectSource
from azure_kinect_comfyui.capture.models import TrackingState


FIXTURE_PATH = Path(__file__).resolve().parents[2] / "fixtures" / "kinect_frames.json"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

@pytest.fixture
def source():
    """Non-looping source from the canonical fixture."""
    return MockKinectSource(FIXTURE_PATH)


@pytest.fixture
def looping_source():
    """Looping source from the canonical fixture."""
    return MockKinectSource(FIXTURE_PATH, loop=True)


# ---------------------------------------------------------------------------
# Valid frame replay
# ---------------------------------------------------------------------------

class TestValidReplay:
    def test_frame_count(self, source):
        assert source.frame_count == 4

    def test_first_frame(self, source):
        frame = source.next_frame()
        assert frame.frame_id == 1
        assert frame.timestamp_us == 1_000_000
        assert frame.body_id == 42
        assert frame.tracking_state is TrackingState.TRACKED
        assert frame.color is not None
        assert frame.depth is not None
        assert len(frame.joints) == 5

    def test_second_frame(self, source):
        source.next_frame()  # skip frame 1
        frame = source.next_frame()
        assert frame.frame_id == 2
        assert frame.timestamp_us == 1_033_333
        assert frame.tracking_state is TrackingState.TRACKED

    def test_deterministic_replay(self):
        """Two independent sources produce identical sequences."""
        s1 = MockKinectSource(FIXTURE_PATH)
        s2 = MockKinectSource(FIXTURE_PATH)
        for _ in range(s1.frame_count):
            f1 = s1.next_frame()
            f2 = s2.next_frame()
            assert f1.frame_id == f2.frame_id
            assert f1.timestamp_us == f2.timestamp_us
            assert f1.tracking_state == f2.tracking_state
            assert f1.body_id == f2.body_id

    def test_iterator_protocol(self, source):
        frames = list(source)
        assert len(frames) == 4
        assert [f.frame_id for f in frames] == [1, 2, 3, 4]

    def test_peek_does_not_advance(self, source):
        first = source.peek()
        assert first is not None
        assert first.frame_id == 1
        assert source.current_index == 0

    def test_peek_at_end_returns_none(self, source):
        for _ in range(source.frame_count):
            source.next_frame()
        assert source.peek() is None


# ---------------------------------------------------------------------------
# Exhausted replay behavior
# ---------------------------------------------------------------------------

class TestExhaustedReplay:
    def test_exhausted_flag(self, source):
        assert not source.is_exhausted
        for _ in range(source.frame_count):
            source.next_frame()
        assert source.is_exhausted

    def test_next_raises_stop_iteration(self, source):
        for _ in range(source.frame_count):
            source.next_frame()
        with pytest.raises(StopIteration):
            source.next_frame()

    def test_reset_restores_source(self, source):
        for _ in range(source.frame_count):
            source.next_frame()
        assert source.is_exhausted
        source.reset()
        assert not source.is_exhausted
        assert source.current_index == 0
        frame = source.next_frame()
        assert frame.frame_id == 1


# ---------------------------------------------------------------------------
# Tracking-lost behavior
# ---------------------------------------------------------------------------

class TestTrackingLost:
    def test_inferred_tracking_frame(self, source):
        source.next_frame()  # frame 1 (TRACKED)
        source.next_frame()  # frame 2 (TRACKED)
        frame = source.next_frame()  # frame 3 (INFERRED)
        assert frame.frame_id == 3
        assert frame.tracking_state is TrackingState.INFERRED
        # Joints should be in INFERRED state
        for joint in frame.joints.values():
            assert joint.state is TrackingState.INFERRED

    def test_not_tracked_frame(self, source):
        source.next_frame()  # frame 1
        source.next_frame()  # frame 2
        source.next_frame()  # frame 3
        frame = source.next_frame()  # frame 4 (NOT_TRACKED)
        assert frame.frame_id == 4
        assert frame.tracking_state is TrackingState.NOT_TRACKED
        assert frame.body_id is None
        assert frame.color is None
        assert frame.depth is None
        assert frame.joints == {}

    def test_looping_continues_past_lost(self, looping_source):
        """In loop mode, iteration continues past tracking-lost frames."""
        frames = []
        for _ in range(8):
            frames.append(looping_source.next_frame())
        # Should have wrapped around once
        assert len(frames) == 8
        assert frames[0].frame_id == frames[4].frame_id
        assert frames[3].frame_id == frames[7].frame_id


def test_parsed_joint_ids_are_joint_id_enums(source):
    from azure_kinect_comfyui.capture.models import JointId

    frame = source.next_frame()
    assert all(isinstance(joint.joint_id, JointId) for joint in frame.joints.values())
