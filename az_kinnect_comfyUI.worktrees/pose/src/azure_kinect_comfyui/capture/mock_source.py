"""Deterministic mock/replay frame source for KinectFrame data.

Reads synthetic fixture files and replays frames in order.  No Azure Kinect
SDK or hardware access is performed.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Iterator, List, Optional

from azure_kinect_comfyui.capture.models import (
    JointId,
    Calibration,
    Joint,
    KinectFrame,
    TrackingState,
)


class MockKinectSource:
    """Replays KinectFrame objects from a JSON fixture file.

    Parameters
    ----------
    fixture_path : Path or str
        Path to a JSON fixture produced by ``fixtures/kinect_frames.json``
        or an equivalent synthetic dataset.
    loop : bool, optional
        If ``True``, replay restarts from the first frame after the last one
        is consumed.  Default is ``False`` (exhaustion raises ``StopIteration``).
    """

    def __init__(self, fixture_path: Path | str, *, loop: bool = False) -> None:
        self._fixture_path = Path(fixture_path)
        self._loop = loop
        self._frames: List[KinectFrame] = []
        self._index: int = 0
        self._load()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @property
    def frame_count(self) -> int:
        """Total number of frames available in the fixture."""
        return len(self._frames)

    @property
    def current_index(self) -> int:
        """Index of the next frame that will be returned."""
        return self._index

    @property
    def is_exhausted(self) -> bool:
        """True when all frames have been consumed (non-looping mode)."""
        return not self._loop and self._index >= self.frame_count

    def next_frame(self) -> KinectFrame:
        """Return the next frame, advancing the internal cursor.

        Raises
        ------
        StopIteration
            When the fixture is exhausted and ``loop`` is ``False``.
        """
        if self._index >= self.frame_count:
            if self._loop:
                self._index = 0
            else:
                raise StopIteration(
                    f"MockKinectSource exhausted after {self.frame_count} frames"
                )
        frame = self._frames[self._index]
        self._index += 1
        return frame

    def peek(self) -> Optional[KinectFrame]:
        """Return the next frame without advancing the cursor."""
        if self._index >= self.frame_count:
            return None
        return self._frames[self._index]

    def reset(self) -> None:
        """Reset the replay cursor to the beginning."""
        self._index = 0

    def __iter__(self) -> Iterator[KinectFrame]:
        """Allow ``for frame in source:`` iteration."""
        return self

    def __next__(self) -> KinectFrame:
        return self.next_frame()

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _load(self) -> None:
        data = json.loads(self._fixture_path.read_text(encoding="utf-8"))
        self._frames = [self._parse_frame(raw) for raw in data["frames"]]
        self._index = 0

    @staticmethod
    def _parse_frame(raw: dict) -> KinectFrame:
        cal_raw = raw.get("calibration", {})
        calibration = Calibration(
            color_width=cal_raw.get("color_width", 1920),
            color_height=cal_raw.get("color_height", 1080),
            depth_width=cal_raw.get("depth_width", 640),
            depth_height=cal_raw.get("depth_height", 576),
            color_focal_length=tuple(cal_raw.get("color_focal_length", [0.0, 0.0])),
            depth_focal_length=tuple(cal_raw.get("depth_focal_length", [0.0, 0.0])),
            depth_mode=cal_raw.get("depth_mode", "NFOV_UNBINNED"),
            color_format=cal_raw.get("color_format", "BGRA32"),
        )

        joints: dict[int, Joint] = {}
        for key, jraw in raw.get("joints", {}).items():
            jid = int(key)
            joints[jid] = Joint(
                joint_id=JointId(jid),
                position=tuple(jraw["position"]),
                state=TrackingState(jraw.get("state", 0)),
            )

        return KinectFrame(
            frame_id=raw["frame_id"],
            timestamp_us=raw["timestamp_us"],
            color=raw.get("color"),
            depth=raw.get("depth"),
            joints=joints,
            tracking_state=TrackingState(raw.get("tracking_state", 0)),
            calibration=calibration,
            body_id=raw.get("body_id"),
        )
