from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Callable, Protocol

import numpy as np

from robot_sim.application.dto import IKRequest
from robot_sim.core.math.so3 import orthonormalize_rotation
from robot_sim.model.ik_result import IKResult
from robot_sim.model.pose import Pose


@dataclass(frozen=True)
class AdaptedIKRequest:
    request: IKRequest
    notes: tuple[str, ...] = ()
    metadata: dict[str, object] = field(default_factory=dict)


class IKRequestAdapter(Protocol):
    adapter_id: str

    def adapt(self, request: IKRequest) -> AdaptedIKRequest: ...


class IKResultAdapter(Protocol):
    adapter_id: str

    def adapt_result(self, request: IKRequest, result: IKResult, *, solve_fn: Callable[[IKRequest], IKResult]) -> IKResult: ...


class JointLimitSeedAdapter:
    adapter_id = 'joint_limit_seed_clamp'

    def adapt(self, request: IKRequest) -> AdaptedIKRequest:
        """Clamp invalid seeds to configured joint limits.

        Args:
            request: Immutable IK request.

        Returns:
            AdaptedIKRequest: Original request when no repair is needed,
                otherwise a repaired request and structured adapter metadata.
        """
        if not bool(getattr(request.config, 'clamp_seed_to_joint_limits', True)):
            return AdaptedIKRequest(request)
        mins = np.array([limit.lower for limit in request.spec.runtime_joint_limits], dtype=float)
        maxs = np.array([limit.upper for limit in request.spec.runtime_joint_limits], dtype=float)
        clamped = np.clip(np.asarray(request.q0, dtype=float), mins, maxs)
        if np.allclose(clamped, np.asarray(request.q0, dtype=float), atol=1.0e-12):
            return AdaptedIKRequest(request)
        repaired = replace(request, q0=clamped)
        return AdaptedIKRequest(
            repaired,
            notes=('initial seed clamped to joint limits',),
            metadata={
                'adapter_id': self.adapter_id,
                'changed': True,
                'original_q0': np.asarray(request.q0, dtype=float).tolist(),
                'clamped_q0': clamped.tolist(),
            },
        )


class TargetRotationNormalizationAdapter:
    adapter_id = 'target_rotation_normalization'

    def adapt(self, request: IKRequest) -> AdaptedIKRequest:
        """Project non-orthonormal target rotations onto ``SO(3)``."""
        if not bool(getattr(request.config, 'normalize_target_rotation', True)):
            return AdaptedIKRequest(request)
        target_R = np.asarray(request.target.R, dtype=float)
        repaired_R = orthonormalize_rotation(target_R)
        residual = float(np.linalg.norm(repaired_R.T @ repaired_R - np.eye(3, dtype=float), ord='fro'))
        delta = float(np.linalg.norm(repaired_R - target_R, ord='fro'))
        if delta <= 1.0e-12:
            return AdaptedIKRequest(request)
        repaired_target = Pose(p=np.asarray(request.target.p, dtype=float).copy(), R=repaired_R, frame=request.target.frame)
        repaired = replace(request, target=repaired_target)
        return AdaptedIKRequest(
            repaired,
            notes=('target rotation projected onto SO(3)',),
            metadata={
                'adapter_id': self.adapter_id,
                'changed': True,
                'orthogonality_residual': residual,
                'projection_delta_fro': delta,
            },
        )


class OrientationRelaxationAdapter:
    adapter_id = 'orientation_relaxation_fallback'

    def adapt_result(self, request: IKRequest, result: IKResult, *, solve_fn: Callable[[IKRequest], IKResult]) -> IKResult:
        """Retry in position-only mode when orientation is the only blocking error."""
        cfg = request.config
        if result.success or request.position_only or not bool(getattr(cfg, 'allow_orientation_relaxation', False)):
            return result
        pos_gate = max(float(cfg.pos_tol) * float(getattr(cfg, 'orientation_relaxation_pos_multiplier', 5.0)), 1.0e-3)
        ori_gate = max(float(cfg.ori_tol) * float(getattr(cfg, 'orientation_relaxation_ori_multiplier', 25.0)), 5.0e-3)
        if not np.isfinite(float(result.final_pos_err)) or not np.isfinite(float(result.final_ori_err)):
            return result
        if float(result.final_pos_err) > pos_gate or float(result.final_ori_err) < ori_gate:
            return result

        relaxed_cfg = replace(cfg, position_only=True, allow_orientation_relaxation=False)
        relaxed_seed = np.asarray(result.best_q if result.best_q is not None else request.q0, dtype=float).copy()
        relaxed_request = replace(
            request,
            q0=relaxed_seed,
            config=relaxed_cfg,
            orientation_mask=(False, False, False),
            allow_approximate_solution=True,
        )
        relaxed = solve_fn(relaxed_request)
        diagnostics = dict(relaxed.diagnostics)
        diagnostics.setdefault('request_adapters', [])
        diagnostics['request_adapters'] = list(diagnostics['request_adapters']) + [
            {
                'adapter_id': self.adapter_id,
                'triggered_from': result.stop_reason,
                'base_pos_err': float(result.final_pos_err),
                'base_ori_err': float(result.final_ori_err),
                'relaxed_position_only': True,
            }
        ]
        message = relaxed.message if relaxed.success else f'{result.message} | orientation relaxed retry failed'
        return IKResult(
            success=relaxed.success,
            q_sol=relaxed.q_sol,
            logs=relaxed.logs,
            message=message,
            final_pos_err=relaxed.final_pos_err,
            final_ori_err=relaxed.final_ori_err,
            final_cond=relaxed.final_cond,
            final_manipulability=relaxed.final_manipulability,
            final_dq_norm=relaxed.final_dq_norm,
            elapsed_ms=relaxed.elapsed_ms,
            effective_mode=relaxed.effective_mode,
            stop_reason='orientation_relaxed_converged' if relaxed.success else result.stop_reason,
            best_q=relaxed.best_q,
            restarts_used=relaxed.restarts_used,
            diagnostics=diagnostics,
            status='succeeded' if relaxed.success else result.status,
            residuals=dict(relaxed.residuals),
            attempt_count=relaxed.attempt_count,
            warnings=tuple(relaxed.warnings),
        )


class IKRequestAdapterPipeline:
    def __init__(self, request_adapters: tuple[IKRequestAdapter, ...] | list[IKRequestAdapter] = (), result_adapters: tuple[IKResultAdapter, ...] | list[IKResultAdapter] = ()) -> None:
        self._request_adapters = tuple(request_adapters)
        self._result_adapters = tuple(result_adapters)

    def prepare(self, request: IKRequest) -> AdaptedIKRequest:
        current = AdaptedIKRequest(request)
        notes: list[str] = []
        metadata: list[dict[str, object]] = []
        for adapter in self._request_adapters:
            adapted = adapter.adapt(current.request)
            current = AdaptedIKRequest(adapted.request)
            notes.extend(adapted.notes)
            if adapted.metadata:
                metadata.append(dict(adapted.metadata))
        return AdaptedIKRequest(current.request, notes=tuple(notes), metadata={'request_adapters': metadata} if metadata else {})

    def finalize(self, request: IKRequest, result: IKResult, *, solve_fn: Callable[[IKRequest], IKResult]) -> IKResult:
        current = result
        for adapter in self._result_adapters:
            current = adapter.adapt_result(request, current, solve_fn=solve_fn)
        return current
