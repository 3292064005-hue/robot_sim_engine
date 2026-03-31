from __future__ import annotations

from dataclasses import dataclass
import time
import numpy as np

from robot_sim.model.playback_state import PlaybackState
from robot_sim.model.trajectory import JointTrajectory


@dataclass(frozen=True)
class PlaybackFrame:
    frame_idx: int
    t: float
    q: np.ndarray
    qd: np.ndarray
    qdd: np.ndarray
    progress: float
    is_last: bool
    emitted_at_ms: float


class PlaybackService:
    """Pure playback logic independent from Qt.

    This service converts a sampled trajectory into indexed frames, clamps cursor
    movement, and computes the next frame index under looping policies.
    """

    def validate_frame_idx(self, trajectory: JointTrajectory, frame_idx: int) -> int:
        total = int(trajectory.t.shape[0])
        if total <= 0:
            raise ValueError("trajectory has no samples")
        return max(0, min(int(frame_idx), total - 1))

    def build_state(
        self,
        trajectory: JointTrajectory,
        *,
        is_playing: bool = False,
        frame_idx: int = 0,
        speed_multiplier: float = 1.0,
        loop_enabled: bool = False,
    ) -> PlaybackState:
        total = int(trajectory.t.shape[0])
        return PlaybackState(
            is_playing=bool(is_playing),
            frame_idx=self.validate_frame_idx(trajectory, frame_idx) if total else 0,
            total_frames=total,
            speed_multiplier=max(float(speed_multiplier), 0.05),
            loop_enabled=bool(loop_enabled),
        )

    def frame(self, trajectory: JointTrajectory, frame_idx: int) -> PlaybackFrame:
        idx = self.validate_frame_idx(trajectory, frame_idx)
        total = int(trajectory.t.shape[0])
        return PlaybackFrame(
            frame_idx=idx,
            t=float(trajectory.t[idx]),
            q=np.asarray(trajectory.q[idx], dtype=float).copy(),
            qd=np.asarray(trajectory.qd[idx], dtype=float).copy(),
            qdd=np.asarray(trajectory.qdd[idx], dtype=float).copy(),
            progress=0.0 if total <= 1 else float(idx / (total - 1)),
            is_last=idx == total - 1,
            emitted_at_ms=time.perf_counter() * 1000.0,
        )

    def next_index(self, state: PlaybackState) -> int | None:
        if state.total_frames <= 0:
            return None
        if state.frame_idx < state.total_frames - 1:
            return state.frame_idx + 1
        if state.loop_enabled:
            return 0
        return None

    def previous_index(self, state: PlaybackState) -> int | None:
        if state.total_frames <= 0:
            return None
        if state.frame_idx > 0:
            return state.frame_idx - 1
        if state.loop_enabled:
            return state.total_frames - 1
        return None
