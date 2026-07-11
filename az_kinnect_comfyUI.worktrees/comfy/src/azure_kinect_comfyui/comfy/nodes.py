"""Mock-backed ComfyUI custom nodes for Azure Kinect pose/depth bridge.

All nodes operate exclusively on synthetic fixture data.  No hardware access,
no model downloads, and no modifications to an installed ComfyUI directory.

ComfyUI integration contract
============================
The package provides the following ComfyUI-compatible registration
structures through its top-level ``__init__.py``:

- ``NODE_CLASS_MAPPINGS``  -- ``{str: type}`` mapping node identifiers to classes
- ``NODE_DISPLAY_NAME_MAPPINGS`` -- ``{str: str}`` mapping identifiers to UI labels

Node catalogue
==============
AzureKinectMockFrame
    Reads a synthetic KinectFrame from a JSON fixture and emits a placeholder
    IMAGE output (a deterministic 64x64 RGB tensor) plus metadata outputs.

AzureKinectPoseOverlay
    Accepts a fixture path, maps Kinect joints to BODY_25, renders a skeleton
    overlay via the pure-Python PoseRenderer, and returns the result as an
    IMAGE tensor.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Tuple

# ---------------------------------------------------------------------------
# ComfyUI tensor helpers (pure Python, no torch dependency at import time)
# ---------------------------------------------------------------------------

def _make_placeholder_image(
    width: int = 64,
    height: int = 64,
    r: int = 30,
    g: int = 60,
    b: int = 90,
) -> "torch.Tensor":
    """Create a deterministic placeholder IMAGE tensor for ComfyUI.

    ComfyUI expects a ``torch.Tensor`` of shape ``(N, H, W, C)`` with
    float32 RGB values in ``[0, 1]``.  We build the tensor lazily so that
    importing this module does not require ``torch`` to be present on the
    Python path during unit tests.
    """
    import torch  # type: ignore[import-not-found]

    tensor = torch.zeros(1, height, width, 3, dtype=torch.float32)
    tensor[:, :, :, 0] = r / 255.0
    tensor[:, :, :, 1] = g / 255.0
    tensor[:, :, :, 2] = b / 255.0
    return tensor


def _ppm_to_tensor(ppm_bytes: bytes) -> "torch.Tensor":
    """Convert a PPM P6 byte stream to a ComfyUI IMAGE tensor.

    Returns a tensor of shape ``(1, H, W, 3)`` with float32 RGB in ``[0, 1]``.
    """
    import torch  # type: ignore[import-not-found]

    lines = ppm_bytes.split(b"\n")
    # P6 header: "P6", "W H", "255"
    magic = lines[0].strip()
    assert magic == b"P6", f"Expected PPM P6, got {magic!r}"
    dims = lines[1].strip().split()
    width, height = int(dims[0]), int(dims[1])
    max_val = int(lines[2].strip())

    # Pixel data starts after the third newline
    header_end = ppm_bytes.index(b"\n", ppm_bytes.index(b"\n", ppm_bytes.index(b"\n") + 1) + 1) + 1
    pixel_data = ppm_bytes[header_end:]

    expected = width * height * 3
    assert len(pixel_data) == expected, (
        f"PPM pixel data length mismatch: {len(pixel_data)} != {expected}"
    )

    raw = torch.frombuffer(pixel_data, dtype=torch.uint8)
    rgb = raw.view(height, width, 3).to(torch.float32) / max_val
    return rgb.unsqueeze(0)


# ---------------------------------------------------------------------------
# Node: AzureKinectMockFrame
# ---------------------------------------------------------------------------

class AzureKinectMockFrame:
    """Reads a synthetic KinectFrame fixture and emits a placeholder IMAGE.

    Input
    -----
    fixture_path : STRING
        Absolute or relative path to a JSON fixture file compatible with
        ``MockKinectSource``.

    frame_index : INT
        Zero-based index of the frame to read from the fixture.

    Output
    ------
    IMAGE : placeholder RGB tensor (64x64)
    frame_id : INT from the fixture
    tracking_state : STRING ("TRACKED", "INFERRED", "NOT_TRACKED")
    body_id : INT or None
    """

    CATEGORY = "azure_kinect"
    RETURN_TYPES = ("IMAGE", "INT", "STRING", "INT")
    RETURN_NAMES = ("image", "frame_id", "tracking_state", "body_id")
    FUNCTION = "load_frame"

    @classmethod
    def INPUT_TYPES(cls) -> Dict[str, Any]:
        return {
            "required": {
                "fixture_path": ("STRING", {
                    "default": "fixtures/kinect_frames.json",
                    "multiline": False,
                }),
                "frame_index": ("INT", {
                    "default": 0,
                    "min": 0,
                    "max": 999,
                    "step": 1,
                }),
            },
        }

    def load_frame(
        self,
        fixture_path: str,
        frame_index: int,
    ) -> Tuple["torch.Tensor", int, str, int | None]:
        from azure_kinect_comfyui.capture.mock_source import MockKinectSource
        from azure_kinect_comfyui.capture.models import TrackingState

        source = MockKinectSource(fixture_path)
        if frame_index >= source.frame_count:
            raise ValueError(
                f"frame_index {frame_index} out of range "
                f"(fixture has {source.frame_count} frames)"
            )
        for _ in range(frame_index):
            source.next_frame()
        frame = source.next_frame()

        state_name = TrackingState(frame.tracking_state).name
        body_id = frame.body_id if frame.body_id is not None else -1

        image = _make_placeholder_image()
        return (image, frame.frame_id, state_name, body_id)


# ---------------------------------------------------------------------------
# Node: AzureKinectPoseOverlay
# ---------------------------------------------------------------------------

class AzureKinectPoseOverlay:
    """Renders a BODY_25 skeleton overlay from a Kinect fixture.

    Input
    -----
    fixture_path : STRING
        Path to a JSON fixture file.
    frame_index : INT
        Zero-based frame index.
    canvas_width : INT
        Output image width in pixels.
    canvas_height : INT
        Output image height in pixels.

    Output
    ------
    IMAGE : RGB tensor with skeleton overlay rendered from fixture data.
    """

    CATEGORY = "azure_kinect"
    RETURN_TYPES = ("IMAGE",)
    RETURN_NAMES = ("image",)
    FUNCTION = "render_pose"

    @classmethod
    def INPUT_TYPES(cls) -> Dict[str, Any]:
        return {
            "required": {
                "fixture_path": ("STRING", {
                    "default": "fixtures/kinect_frames.json",
                    "multiline": False,
                }),
                "frame_index": ("INT", {
                    "default": 0,
                    "min": 0,
                    "max": 999,
                    "step": 1,
                }),
                "canvas_width": ("INT", {
                    "default": 640,
                    "min": 64,
                    "max": 4096,
                    "step": 1,
                }),
                "canvas_height": ("INT", {
                    "default": 480,
                    "min": 64,
                    "max": 4096,
                    "step": 1,
                }),
            },
        }

    def render_pose(
        self,
        fixture_path: str,
        frame_index: int,
        canvas_width: int,
        canvas_height: int,
    ) -> Tuple["torch.Tensor"]:
        from azure_kinect_comfyui.capture.mock_source import MockKinectSource
        from azure_kinect_comfyui.pose.mapping import KinectToBody25Mapper
        from azure_kinect_comfyui.pose.renderer import PoseRenderer

        source = MockKinectSource(fixture_path)
        if frame_index >= source.frame_count:
            raise ValueError(
                f"frame_index {frame_index} out of range "
                f"(fixture has {source.frame_count} frames)"
            )
        for _ in range(frame_index):
            source.next_frame()
        frame = source.next_frame()

        mapper = KinectToBody25Mapper()
        pose = mapper.map_frame(frame)

        renderer = PoseRenderer(
            width=canvas_width,
            height=canvas_height,
            joint_radius=5,
            confidence_threshold=0.0,
        )
        ppm_bytes = renderer.render(pose)
        image = _ppm_to_tensor(ppm_bytes)
        return (image,)
