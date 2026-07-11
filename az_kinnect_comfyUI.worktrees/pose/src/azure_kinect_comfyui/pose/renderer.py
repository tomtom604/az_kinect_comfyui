"""Deterministic PPM pose-map renderer for BODY_25 keypoints.

Produces a binary PPM (P6) image with coloured skeleton overlay.
Pure Python -- no external dependencies required.
"""

from __future__ import annotations

import struct
from dataclasses import dataclass
from typing import List, Tuple

from azure_kinect_comfyui.pose.mapping import (
    BODY_25_SKELETON,
    Body25Keypoint,
    Body25Pose,
)

# ---------------------------------------------------------------------------
# Colour palette (deterministic, OpenPose-inspired)
# ---------------------------------------------------------------------------

_JOINT_COLOURS: Tuple[Tuple[int, int, int], ...] = (
    (255,   0,   0),  # 0  Nose          - red
    (255,  85,   0),  # 1  Neck          - orange
    (255, 170,   0),  # 2  R Shoulder    - amber
    (255, 255,   0),  # 3  R Elbow       - yellow
    (170, 255,   0),  # 4  R Wrist       - lime
    ( 85, 255,   0),  # 5  L Shoulder    - green
    (  0, 255,   0),  # 6  L Elbow       - green
    (  0, 255,  85),  # 7  L Wrist       - green
    (  0, 255, 170),  # 8  Mid Hip       - teal
    (  0, 255, 255),  # 9  R Hip         - cyan
    (  0, 170, 255),  # 10 R Knee        - sky
    (  0,  85, 255),  # 11 R Ankle       - blue
    ( 85,   0, 255),  # 12 L Hip         - purple
    (170,   0, 255),  # 13 L Knee        - violet
    (255,   0, 255),  # 14 L Ankle       - magenta
    (255,   0, 170),  # 15 R Eye         - pink
    (255,   0,  85),  # 16 L Eye         - rose
    (128,   0,   0),  # 17 R Ear         - maroon
    (  0, 128,   0),  # 18 L Ear         - dark green
    (128, 128,   0),  # 19 L Big Toe     - olive
    (  0, 128, 128),  # 20 L Small Toe   - teal-dark
    (128,   0, 128),  # 21 L Heel        - purple-dark
    ( 64,  64,  64),  # 22 R Big Toe     - grey
    ( 96,  96,  96),  # 23 R Small Toe   - grey-light
    (128, 128, 128),  # 24 R Heel        - grey-mid
)

_SKELETON_COLOUR: Tuple[int, int, int] = (200, 200, 200)

# ---------------------------------------------------------------------------
# Canvas
# ---------------------------------------------------------------------------


@dataclass
class _Canvas:
    width: int
    height: int
    pixels: List[List[Tuple[int, int, int]]]

    @classmethod
    def blank(cls, width: int, height: int,
              bg: Tuple[int, int, int] = (30, 30, 30)) -> "_Canvas":
        return cls(
            width=width,
            height=height,
            pixels=[[bg] * width for _ in range(height)],
        )

    def put_pixel(self, x: int, y: int, colour: Tuple[int, int, int]) -> None:
        if 0 <= x < self.width and 0 <= y < self.height:
            self.pixels[y][x] = colour

    def draw_line(self, x0: int, y0: int, x1: int, y1: int,
                  colour: Tuple[int, int, int]) -> None:
        """Bresenham line algorithm."""
        dx = abs(x1 - x0)
        dy = abs(y1 - y0)
        sx = 1 if x0 < x1 else -1
        sy = 1 if y0 < y1 else -1
        err = dx - dy
        while True:
            self.put_pixel(x0, y0, colour)
            if x0 == x1 and y0 == y1:
                break
            e2 = 2 * err
            if e2 > -dy:
                err -= dy
                x0 += sx
            if e2 < dx:
                err += dx
                y0 += sy

    def draw_circle(self, cx: int, cy: int, radius: int,
                    colour: Tuple[int, int, int]) -> None:
        """Midpoint circle algorithm (filled)."""
        for dy in range(-radius, radius + 1):
            for dx in range(-radius, radius + 1):
                if dx * dx + dy * dy <= radius * radius:
                    self.put_pixel(cx + dx, cy + dy, colour)

    def to_ppm_p6(self) -> bytes:
        """Encode as binary PPM P6."""
        header = f"P6\n{self.width} {self.height}\n255\n".encode("ascii")
        raw = bytearray()
        for row in self.pixels:
            for r, g, b in row:
                raw.extend(struct.pack("BBB", r, g, b))
        return header + bytes(raw)


# ---------------------------------------------------------------------------
# Renderer
# ---------------------------------------------------------------------------

class PoseRenderer:
    """Renders a Body25Pose to a deterministic PPM image."""

    def __init__(
        self,
        width: int = 640,
        height: int = 480,
        joint_radius: int = 5,
        confidence_threshold: float = 0.0,
    ) -> None:
        self.width = width
        self.height = height
        self.joint_radius = joint_radius
        self.confidence_threshold = confidence_threshold

    def render(self, pose: Body25Pose) -> bytes:
        """Render pose to PPM P6 bytes."""
        canvas = _Canvas.blank(self.width, self.height)

        # Draw skeleton lines first (behind joints)
        for from_idx, to_idx in BODY_25_SKELETON:
            if from_idx >= len(pose.keypoints) or to_idx >= len(pose.keypoints):
                continue
            kp_from = pose.keypoints[from_idx]
            kp_to = pose.keypoints[to_idx]
            if (kp_from.confidence < self.confidence_threshold or
                    kp_to.confidence < self.confidence_threshold):
                continue
            x0 = int(round(kp_from.x))
            y0 = int(round(kp_from.y))
            x1 = int(round(kp_to.x))
            y1 = int(round(kp_to.y))
            canvas.draw_line(x0, y0, x1, y1, _SKELETON_COLOUR)

        # Draw joint circles on top
        for kp in pose.keypoints:
            if kp.confidence < self.confidence_threshold:
                continue
            x = int(round(kp.x))
            y = int(round(kp.y))
            colour = _JOINT_COLOURS[kp.index]
            canvas.draw_circle(x, y, self.joint_radius, colour)

        return canvas.to_ppm_p6()
