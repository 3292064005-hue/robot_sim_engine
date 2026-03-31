from __future__ import annotations

import time

from robot_sim.application.workers.base import BaseWorker, Slot
from robot_sim.application.services.playback_service import PlaybackService
from robot_sim.model.playback_state import PlaybackState
from robot_sim.model.trajectory import JointTrajectory


class PlaybackWorker(BaseWorker):
    def __init__(self, trajectory: JointTrajectory, state: PlaybackState, frame_interval_ms: int = 30) -> None:
        super().__init__()
        self._trajectory = trajectory
        self._state = state
        self._frame_interval_ms = max(int(frame_interval_ms), 5)
        self._service = PlaybackService()

    @Slot()
    def run(self) -> None:
        self.started.emit()
        try:
            state = self._state.play()
            if state.total_frames <= 0:
                self.failed.emit("trajectory has no frames")
                return
            while not self.is_cancel_requested():
                frame = self._service.frame(self._trajectory, state.frame_idx)
                self.progress.emit(frame)
                next_idx = self._service.next_index(state)
                if next_idx is None:
                    self.finished.emit(state.stop())
                    return
                state = state.with_frame(next_idx)
                time.sleep(self._frame_interval_ms / 1000.0 / max(state.speed_multiplier, 0.05))
            self.cancelled.emit()
        except Exception as exc:
            self.failed.emit(str(exc))
