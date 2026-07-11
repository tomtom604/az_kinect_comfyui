"""Tests for the deterministic PPM pose-map renderer."""

import struct

import pytest

from azure_kinect_comfyui.pose.mapping import (
    Body25Keypoint,
    Body25Pose,
)
from azure_kinect_comfyui.pose.renderer import PoseRenderer


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_full_pose() -> Body25Pose:
    """Create a BODY_25 pose with all keypoints at full confidence."""
    keypoints = tuple(
        Body25Keypoint(
            index=i, name=f"KP{i}",
            x=320.0 + i * 2, y=240.0 + i,
            confidence=1.0, source="kinect",
        )
        for i in range(25)
    )
    return Body25Pose(keypoints=keypoints)


def _parse_ppm(data: bytes):
    """Parse PPM P6 header and return (width, height, pixel_bytes)."""
    # Find the header end (after "255\n")
    header_end = data.index(b"\n255\n") + len(b"\n255\n")
    header = data[:header_end].decode("ascii")
    lines = header.strip().split("\n")
    assert lines[0] == "P6"
    width, height = map(int, lines[1].split())
    pixel_data = data[header_end:]
    assert len(pixel_data) == width * height * 3
    return width, height, pixel_data


# ---------------------------------------------------------------------------
# PoseRenderer basic tests
# ---------------------------------------------------------------------------

class TestPoseRendererBasics:
    def test_default_dimensions(self):
        renderer = PoseRenderer()
        assert renderer.width == 640
        assert renderer.height == 480
        assert renderer.joint_radius == 5
        assert renderer.confidence_threshold == 0.0

    def test_custom_dimensions(self):
        renderer = PoseRenderer(width=320, height=240, joint_radius=3)
        assert renderer.width == 320
        assert renderer.height == 240
        assert renderer.joint_radius == 3

    def test_render_returns_bytes(self):
        renderer = PoseRenderer()
        pose = _make_full_pose()
        result = renderer.render(pose)
        assert isinstance(result, bytes)
        assert len(result) > 0

    def test_ppm_header_valid(self):
        renderer = PoseRenderer(width=100, height=80)
        pose = _make_full_pose()
        result = renderer.render(pose)

        w, h, pixels = _parse_ppm(result)
        assert w == 100
        assert h == 80
        assert len(pixels) == 100 * 80 * 3


# ---------------------------------------------------------------------------
# Determinism
# ---------------------------------------------------------------------------

class TestDeterminism:
    def test_same_input_same_output(self):
        renderer = PoseRenderer()
        pose = _make_full_pose()

        result1 = renderer.render(pose)
        result2 = renderer.render(pose)

        assert result1 == result2

    def test_different_renderers_same_output(self):
        pose = _make_full_pose()
        r1 = PoseRenderer()
        r2 = PoseRenderer()

        assert r1.render(pose) == r2.render(pose)


# ---------------------------------------------------------------------------
# Confidence threshold
# ---------------------------------------------------------------------------

class TestConfidenceThreshold:
    def test_zero_threshold_renders_all(self):
        renderer = PoseRenderer(confidence_threshold=0.0)
        keypoints = tuple(
            Body25Keypoint(
                index=i, name=f"KP{i}",
                x=320.0, y=240.0,
                confidence=0.1, source="kinect",
            )
            for i in range(25)
        )
        pose = Body25Pose(keypoints=keypoints)
        result = renderer.render(pose)
        assert len(result) > 0

    def test_high_threshold_hides_low_confidence(self):
        renderer = PoseRenderer(confidence_threshold=0.9)
        keypoints = tuple(
            Body25Keypoint(
                index=i, name=f"KP{i}",
                x=320.0, y=240.0,
                confidence=0.5, source="kinect",
            )
            for i in range(25)
        )
        pose = Body25Pose(keypoints=keypoints)
        result = renderer.render(pose)

        # With threshold 0.9 and all confidences at 0.5, nothing should render
        # The output should be just the background
        w, h, pixels = _parse_ppm(result)
        # All pixels should be the background colour (30, 30, 30)
        for i in range(0, len(pixels), 3):
            r, g, b = pixels[i], pixels[i+1], pixels[i+2]
            assert r == 30 and g == 30 and b == 30

    def test_mixed_confidence(self):
        renderer = PoseRenderer(confidence_threshold=0.5)
        keypoints = tuple(
            Body25Keypoint(
                index=i, name=f"KP{i}",
                x=320.0, y=240.0,
                confidence=1.0 if i < 10 else 0.3,
                source="kinect",
            )
            for i in range(25)
        )
        pose = Body25Pose(keypoints=keypoints)
        result = renderer.render(pose)

        # Should render first 10 keypoints, skip the rest
        w, h, pixels = _parse_ppm(result)
        # At least some pixels should differ from background
        non_bg = 0
        for i in range(0, len(pixels), 3):
            r, g, b = pixels[i], pixels[i+1], pixels[i+2]
            if r != 30 or g != 30 or b != 30:
                non_bg += 1
        assert non_bg > 0


# ---------------------------------------------------------------------------
# Neutral standing fixture integration
# ---------------------------------------------------------------------------

class TestNeutralStandingRender:
    def test_render_from_mapper(self, neutral_standing_kinect_frame):
        from azure_kinect_comfyui.pose.mapping import KinectToBody25Mapper

        mapper = KinectToBody25Mapper()
        pose = mapper.map_frame(neutral_standing_kinect_frame)

        renderer = PoseRenderer()
        result = renderer.render(pose)

        w, h, pixels = _parse_ppm(result)
        assert w == 640
        assert h == 480
        # Should have non-background pixels (tracked joints)
        non_bg = 0
        for i in range(0, len(pixels), 3):
            r, g, b = pixels[i], pixels[i+1], pixels[i+2]
            if r != 30 or g != 30 or b != 30:
                non_bg += 1
        assert non_bg > 0

    def test_render_with_threshold(self, neutral_standing_kinect_frame):
        from azure_kinect_comfyui.pose.mapping import KinectToBody25Mapper

        mapper = KinectToBody25Mapper()
        pose = mapper.map_frame(neutral_standing_kinect_frame)

        # High threshold: only fully tracked joints render
        renderer = PoseRenderer(confidence_threshold=1.0)
        result = renderer.render(pose)

        w, h, pixels = _parse_ppm(result)
        # Synthetic keypoints (toes/heels) have 0 confidence, should not render
        # But tracked body joints should render
        non_bg = 0
        for i in range(0, len(pixels), 3):
            r, g, b = pixels[i], pixels[i+1], pixels[i+2]
            if r != 30 or g != 30 or b != 30:
                non_bg += 1
        assert non_bg > 0


# ---------------------------------------------------------------------------
# Missing joints render
# ---------------------------------------------------------------------------

class TestMissingJointsRender:
    def test_render_with_missing_joints(self, missing_joints_kinect_frame):
        from azure_kinect_comfyui.pose.mapping import KinectToBody25Mapper

        mapper = KinectToBody25Mapper()
        pose = mapper.map_frame(missing_joints_kinect_frame)

        renderer = PoseRenderer()
        result = renderer.render(pose)

        w, h, pixels = _parse_ppm(result)
        assert w == 640
        assert h == 480

    def test_high_threshold_reduces_rendered_joints(self, missing_joints_kinect_frame):
        from azure_kinect_comfyui.pose.mapping import KinectToBody25Mapper

        mapper = KinectToBody25Mapper()
        pose = mapper.map_frame(missing_joints_kinect_frame)

        # With threshold 1.0, only fully tracked joints render
        renderer_high = PoseRenderer(confidence_threshold=1.0)
        result_high = renderer_high.render(pose)

        # With threshold 0.0, all joints render (including low-confidence)
        renderer_low = PoseRenderer(confidence_threshold=0.0)
        result_low = renderer_low.render(pose)

        # The high-threshold render should have fewer or equal non-bg pixels
        _, _, pixels_high = _parse_ppm(result_high)
        _, _, pixels_low = _parse_ppm(result_low)

        non_bg_high = sum(
            1 for i in range(0, len(pixels_high), 3)
            if pixels_high[i] != 30 or pixels_high[i+1] != 30 or pixels_high[i+2] != 30
        )
        non_bg_low = sum(
            1 for i in range(0, len(pixels_low), 3)
            if pixels_low[i] != 30 or pixels_low[i+1] != 30 or pixels_low[i+2] != 30
        )

        assert non_bg_high <= non_bg_low
