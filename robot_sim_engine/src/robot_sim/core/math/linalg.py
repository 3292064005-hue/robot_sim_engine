from __future__ import annotations
import numpy as np
from robot_sim.domain.constants import EPS
from robot_sim.domain.types import FloatArray

def pseudo_inverse_svd(A: FloatArray, rcond: float = 1.0e-12) -> FloatArray:
    U, s, Vt = np.linalg.svd(A, full_matrices=False)
    if s.size == 0:
        return np.zeros((A.shape[1], A.shape[0]), dtype=float)
    cutoff = rcond * float(s[0])
    s_inv = np.array([1.0 / x if x > cutoff else 0.0 for x in s], dtype=float)
    return Vt.T @ np.diag(s_inv) @ U.T

def damped_least_squares(A: FloatArray, damping: float) -> FloatArray:
    m, _ = A.shape
    return A.T @ np.linalg.inv(A @ A.T + (damping ** 2) * np.eye(m, dtype=float))

def safe_condition_number(A: FloatArray) -> float:
    try:
        return float(np.linalg.cond(A))
    except np.linalg.LinAlgError:
        return float("inf")

def clip_norm(v: FloatArray, max_norm: float) -> FloatArray:
    n = float(np.linalg.norm(v))
    if n < EPS or n <= max_norm:
        return v
    return v * (max_norm / n)
