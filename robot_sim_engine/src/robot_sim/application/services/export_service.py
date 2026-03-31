from __future__ import annotations
from pathlib import Path
import json
import numpy as np

from robot_sim.model.session_state import SessionState


class ExportService:
    def __init__(self, export_dir: str | Path) -> None:
        self.export_dir = Path(export_dir)
        self.export_dir.mkdir(parents=True, exist_ok=True)

    def save_json(self, name: str, payload: dict) -> Path:
        path = self.export_dir / name
        with path.open("w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
        return path

    def save_csv(self, name: str, array: np.ndarray, header: str = "") -> Path:
        path = self.export_dir / name
        np.savetxt(path, array, delimiter=",", header=header, comments="")
        return path

    def save_trajectory(self, name: str, t: np.ndarray, q: np.ndarray, qd: np.ndarray, qdd: np.ndarray) -> Path:
        header_cols = ["t"]
        header_cols += [f"q{i}" for i in range(q.shape[1])]
        header_cols += [f"qd{i}" for i in range(qd.shape[1])]
        header_cols += [f"qdd{i}" for i in range(qdd.shape[1])]
        merged = np.column_stack([t, q, qd, qdd])
        return self.save_csv(name, merged, header=",".join(header_cols))

    def save_metrics(self, name: str, payload: dict) -> Path:
        return self.save_json(name, payload)

    def save_session(self, name: str, state: SessionState) -> Path:
        payload = {
            "robot_name": state.robot_spec.name if state.robot_spec is not None else None,
            "robot_label": state.robot_spec.label if state.robot_spec is not None else None,
            "q_current": None if state.q_current is None else np.asarray(state.q_current, dtype=float).tolist(),
            "target_pose": None if state.target_pose is None else {
                "p": np.asarray(state.target_pose.p, dtype=float).tolist(),
                "R": np.asarray(state.target_pose.R, dtype=float).tolist(),
            },
            "ik": None if state.ik_result is None else {
                "success": state.ik_result.success,
                "message": state.ik_result.message,
                "iterations": len(state.ik_result.logs),
            },
            "trajectory": None if state.trajectory is None else {
                "num_samples": int(state.trajectory.t.shape[0]),
                "dof": int(state.trajectory.q.shape[1]),
            },
            "playback": {
                "frame_idx": int(state.playback.frame_idx),
                "total_frames": int(state.playback.total_frames),
                "speed_multiplier": float(state.playback.speed_multiplier),
                "loop_enabled": bool(state.playback.loop_enabled),
            },
            "last_error": state.last_error,
            "last_warning": state.last_warning,
        }
        return self.save_json(name, payload)
