"""Tests for ComfyUI node import behavior and registration structures."""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

FIXTURE_PATH = Path(__file__).resolve().parents[2] / "fixtures" / "kinect_frames.json"


@pytest.fixture
def comfy_pkg():
    """Import the comfy package and return it."""
    from azure_kinect_comfyui import comfy
    return comfy


@pytest.fixture
def mock_torch():
    """Provide a mock torch module when real torch is unavailable."""
    if "torch" in sys.modules:
        yield sys.modules["torch"]
        return

    mock_tensor = MagicMock()
    mock_torch = MagicMock()
    mock_torch.zeros.return_value = mock_tensor
    mock_torch.float32 = MagicMock()
    mock_torch.frombuffer.return_value = MagicMock()
    mock_torch.uint8 = MagicMock()
    sys.modules["torch"] = mock_torch
    yield mock_torch
    # Clean up only if we added it
    if "torch" not in sys.modules or sys.modules["torch"] is mock_torch:
        del sys.modules["torch"]


# ---------------------------------------------------------------------------
# Package import and registration
# ---------------------------------------------------------------------------

class TestPackageImport:
    def test_comfy_package_imports(self):
        """The comfy sub-package is importable."""
        from azure_kinect_comfyui import comfy
        assert comfy is not None

    def test_nodes_module_imports(self):
        """The nodes module is importable."""
        from azure_kinect_comfyui.comfy import nodes
        assert nodes is not None

    def test_node_classes_importable(self):
        """Both node classes can be imported directly."""
        from azure_kinect_comfyui.comfy.nodes import (
            AzureKinectMockFrame,
            AzureKinectPoseOverlay,
        )
        assert AzureKinectMockFrame is not None
        assert AzureKinectPoseOverlay is not None


class TestNodeClassMappings:
    def test_mappings_exist(self, comfy_pkg):
        """NODE_CLASS_MAPPINGS is a non-empty dict."""
        assert hasattr(comfy_pkg, "NODE_CLASS_MAPPINGS")
        assert isinstance(comfy_pkg.NODE_CLASS_MAPPINGS, dict)
        assert len(comfy_pkg.NODE_CLASS_MAPPINGS) > 0

    def test_display_name_mappings_exist(self, comfy_pkg):
        """NODE_DISPLAY_NAME_MAPPINGS is a non-empty dict."""
        assert hasattr(comfy_pkg, "NODE_DISPLAY_NAME_MAPPINGS")
        assert isinstance(comfy_pkg.NODE_DISPLAY_NAME_MAPPINGS, dict)
        assert len(comfy_pkg.NODE_DISPLAY_NAME_MAPPINGS) > 0

    def test_mappings_same_keys(self, comfy_pkg):
        """Both mappings have identical keys."""
        class_keys = set(comfy_pkg.NODE_CLASS_MAPPINGS.keys())
        display_keys = set(comfy_pkg.NODE_DISPLAY_NAME_MAPPINGS.keys())
        assert class_keys == display_keys

    def test_mock_frame_registered(self, comfy_pkg):
        """AzureKinectMockFrame is registered."""
        assert "AzureKinectMockFrame" in comfy_pkg.NODE_CLASS_MAPPINGS
        cls = comfy_pkg.NODE_CLASS_MAPPINGS["AzureKinectMockFrame"]
        assert cls.__name__ == "AzureKinectMockFrame"

    def test_pose_overlay_registered(self, comfy_pkg):
        """AzureKinectPoseOverlay is registered."""
        assert "AzureKinectPoseOverlay" in comfy_pkg.NODE_CLASS_MAPPINGS
        cls = comfy_pkg.NODE_CLASS_MAPPINGS["AzureKinectPoseOverlay"]
        assert cls.__name__ == "AzureKinectPoseOverlay"

    def test_display_names_are_strings(self, comfy_pkg):
        """All display name values are non-empty strings."""
        for key, name in comfy_pkg.NODE_DISPLAY_NAME_MAPPINGS.items():
            assert isinstance(name, str)
            assert len(name) > 0


# ---------------------------------------------------------------------------
# Node class structure (ComfyUI contract)
# ---------------------------------------------------------------------------

class TestAzureKinectMockFrameStructure:
    @pytest.fixture
    def node_cls(self):
        from azure_kinect_comfyui.comfy.nodes import AzureKinectMockFrame
        return AzureKinectMockFrame

    def test_category(self, node_cls):
        assert node_cls.CATEGORY == "azure_kinect"

    def test_return_types(self, node_cls):
        assert isinstance(node_cls.RETURN_TYPES, tuple)
        assert len(node_cls.RETURN_TYPES) == 4
        assert node_cls.RETURN_TYPES[0] == "IMAGE"

    def test_return_names(self, node_cls):
        assert isinstance(node_cls.RETURN_NAMES, tuple)
        assert len(node_cls.RETURN_NAMES) == 4

    def test_function(self, node_cls):
        assert node_cls.FUNCTION == "load_frame"

    def test_input_types(self, node_cls):
        input_types = node_cls.INPUT_TYPES()
        assert "required" in input_types
        assert "fixture_path" in input_types["required"]
        assert "frame_index" in input_types["required"]

    def test_has_load_frame_method(self, node_cls):
        assert hasattr(node_cls, "load_frame")
        assert callable(getattr(node_cls, "load_frame"))


class TestAzureKinectPoseOverlayStructure:
    @pytest.fixture
    def node_cls(self):
        from azure_kinect_comfyui.comfy.nodes import AzureKinectPoseOverlay
        return AzureKinectPoseOverlay

    def test_category(self, node_cls):
        assert node_cls.CATEGORY == "azure_kinect"

    def test_return_types(self, node_cls):
        assert isinstance(node_cls.RETURN_TYPES, tuple)
        assert node_cls.RETURN_TYPES == ("IMAGE",)

    def test_return_names(self, node_cls):
        assert isinstance(node_cls.RETURN_NAMES, tuple)
        assert node_cls.RETURN_NAMES == ("image",)

    def test_function(self, node_cls):
        assert node_cls.FUNCTION == "render_pose"

    def test_input_types(self, node_cls):
        input_types = node_cls.INPUT_TYPES()
        assert "required" in input_types
        assert "fixture_path" in input_types["required"]
        assert "frame_index" in input_types["required"]
        assert "canvas_width" in input_types["required"]
        assert "canvas_height" in input_types["required"]

    def test_has_render_pose_method(self, node_cls):
        assert hasattr(node_cls, "render_pose")
        assert callable(getattr(node_cls, "render_pose"))


# ---------------------------------------------------------------------------
# Mock-backed execution (with mocked torch)
# ---------------------------------------------------------------------------

class TestMockFrameExecution:
    """Validate that AzureKinectMockFrame reads fixture data correctly."""

    @pytest.fixture
    def node(self):
        from azure_kinect_comfyui.comfy.nodes import AzureKinectMockFrame
        return AzureKinectMockFrame()

    def test_load_frame_first(self, node, mock_torch):
        """Loading frame 0 returns correct metadata."""
        image, frame_id, tracking_state, body_id = node.load_frame(
            fixture_path=str(FIXTURE_PATH),
            frame_index=0,
        )
        assert frame_id == 1
        assert tracking_state == "TRACKED"
        assert body_id == 42

    def test_load_frame_second(self, node, mock_torch):
        """Loading frame 1 returns correct metadata."""
        image, frame_id, tracking_state, body_id = node.load_frame(
            fixture_path=str(FIXTURE_PATH),
            frame_index=1,
        )
        assert frame_id == 2
        assert tracking_state == "TRACKED"

    def test_load_frame_tracking_lost(self, node, mock_torch):
        """Loading frame 3 (NOT_TRACKED) returns correct state."""
        image, frame_id, tracking_state, body_id = node.load_frame(
            fixture_path=str(FIXTURE_PATH),
            frame_index=3,
        )
        assert frame_id == 4
        assert tracking_state == "NOT_TRACKED"
        assert body_id == -1  # None mapped to -1

    def test_load_frame_out_of_range(self, node, mock_torch):
        """Requesting a frame beyond fixture length raises ValueError."""
        with pytest.raises(ValueError, match="out of range"):
            node.load_frame(
                fixture_path=str(FIXTURE_PATH),
                frame_index=99,
            )


class TestPoseOverlayExecution:
    """Validate that AzureKinectPoseOverlay renders from fixture data."""

    @pytest.fixture
    def node(self):
        from azure_kinect_comfyui.comfy.nodes import AzureKinectPoseOverlay
        return AzureKinectPoseOverlay()

    def test_render_pose_first_frame(self, node, mock_torch):
        """Rendering frame 0 produces an IMAGE tensor."""
        (image,) = node.render_pose(
            fixture_path=str(FIXTURE_PATH),
            frame_index=0,
            canvas_width=640,
            canvas_height=480,
        )
        # With mock torch, we just verify the call was made
        assert mock_torch.zeros.called or mock_torch.frombuffer.called

    def test_render_pose_out_of_range(self, node, mock_torch):
        """Requesting a frame beyond fixture length raises ValueError."""
        with pytest.raises(ValueError, match="out of range"):
            node.render_pose(
                fixture_path=str(FIXTURE_PATH),
                frame_index=99,
                canvas_width=640,
                canvas_height=480,
            )
