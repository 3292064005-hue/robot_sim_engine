from __future__ import annotations
import numpy as np
from robot_sim.model.ik_result import IKResult
from robot_sim.model.trajectory import JointTrajectory


class MetricsService:
    def summarize_ik(self, result: IKResult) -> dict[str, float | int | bool | str]:
        if not result.logs:
            return {
                "success": result.success,
                "iterations": 0,
                "final_pos_err": float("nan"),
                "final_ori_err": float("nan"),
                "final_cond": float("nan"),
                "final_manipulability": float("nan"),
                "final_dq_norm": float("nan"),
                "elapsed_ms": 0.0,
                "message": result.message,
            }
        last = result.logs[-1]
        return {
            "success": result.success,
            "iterations": len(result.logs),
            "final_pos_err": float(last.pos_err_norm),
            "final_ori_err": float(last.ori_err_norm),
            "final_cond": float(last.cond_number),
            "final_manipulability": float(last.manipulability),
            "final_dq_norm": float(last.dq_norm),
            "elapsed_ms": float(last.elapsed_ms),
            "message": result.message,
        }

    def summarize_trajectory(self, trajectory: JointTrajectory) -> dict[str, float | int]:
        return {
            "num_samples": int(trajectory.t.shape[0]),
            "dof": int(trajectory.q.shape[1]),
            "duration": float(trajectory.t[-1] - trajectory.t[0]) if trajectory.t.size else 0.0,
            "max_abs_q": float(np.max(np.abs(trajectory.q))) if trajectory.q.size else 0.0,
            "max_abs_qd": float(np.max(np.abs(trajectory.qd))) if trajectory.qd.size else 0.0,
            "max_abs_qdd": float(np.max(np.abs(trajectory.qdd))) if trajectory.qdd.size else 0.0,
        }

    def summarize_batch(self, results: list[IKResult]) -> dict[str, float]:
        if not results:
            return {"count": 0.0, "success_rate": 0.0}
        success = np.array([1.0 if r.success else 0.0 for r in results], dtype=float)
        pos = np.array([r.logs[-1].pos_err_norm for r in results if r.logs], dtype=float)
        ori = np.array([r.logs[-1].ori_err_norm for r in results if r.logs], dtype=float)
        cond = np.array([r.logs[-1].cond_number for r in results if r.logs], dtype=float)
        return {
            "count": float(len(results)),
            "success_rate": float(success.mean()),
            "mean_final_pos_err": float(pos.mean()) if pos.size else float("nan"),
            "mean_final_ori_err": float(ori.mean()) if ori.size else float("nan"),
            "mean_final_cond": float(cond.mean()) if cond.size else float("nan"),
        }
