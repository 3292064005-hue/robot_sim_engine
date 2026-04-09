from __future__ import annotations

<<<<<<< HEAD
import time

=======
>>>>>>> 3ed78e647985c6d680c085e4480d898855278db3
import numpy as np

from robot_sim.application.adapters import (
    IKRequestAdapterPipeline,
    JointLimitSeedAdapter,
    OrientationRelaxationAdapter,
    TargetRotationNormalizationAdapter,
)
from robot_sim.application.dto import IKRequest
from robot_sim.core.ik.registry import SolverRegistry
from robot_sim.model.ik_result import IKResult


class RunIKUseCase:
    """Execute IK requests with adapter preprocessing and retry handling."""

    def __init__(self, solver_registry: SolverRegistry) -> None:
        """Create the IK use case.

        Args:
            solver_registry: Registry resolving solver implementations by mode.

        Returns:
            None: Initializes solver and adapter dependencies.

        Raises:
            ValueError: If ``solver_registry`` is not provided.
        """
        if solver_registry is None:
            raise ValueError('RunIKUseCase requires an explicit solver registry')
        self._solvers = solver_registry
        self._adapters = IKRequestAdapterPipeline(
            request_adapters=(JointLimitSeedAdapter(), TargetRotationNormalizationAdapter()),
            result_adapters=(OrientationRelaxationAdapter(),),
        )

    @property
    def solver_ids(self) -> list[str]:
        if hasattr(self._solvers, 'ids'):
            return list(self._solvers.ids())
        if isinstance(self._solvers, dict):
            return [key.value if hasattr(key, 'value') else str(key) for key in self._solvers.keys()]
        return []

    def execute(self, req: IKRequest, cancel_flag=None, progress_cb=None, correlation_id: str | None = None) -> IKResult:
        """Execute an IK request with solver retries and adapter post-processing.

        Args:
            req: Immutable IK request.
            cancel_flag: Optional cooperative cancellation callback.
            progress_cb: Optional progress callback forwarded to the solver.
            correlation_id: Optional correlation identifier propagated into diagnostics.

        Returns:
            IKResult: Final solver result with adapter and correlation metadata attached.

        Raises:
<<<<<<< HEAD
            ValueError: If the request shape / masks / numeric inputs are invalid.
            Exception: Propagates solver and adapter failures unchanged.
        """
        self._validate_request(req)
=======
            Exception: Propagates solver and adapter failures unchanged.
        """
>>>>>>> 3ed78e647985c6d680c085e4480d898855278db3
        prepared = self._adapters.prepare(req)
        adapted_req = prepared.request
        result = self._execute_solver(adapted_req, cancel_flag=cancel_flag, progress_cb=progress_cb, correlation_id=correlation_id)
        result = self._adapters.finalize(
            adapted_req,
            result,
            solve_fn=lambda nested_req: self._execute_solver(
                nested_req,
                cancel_flag=cancel_flag,
                progress_cb=progress_cb,
                correlation_id=correlation_id,
            ),
        )
        return self._attach_adapter_metadata(result, prepared, correlation_id=correlation_id)

<<<<<<< HEAD
    def _validate_request(self, req: IKRequest) -> None:
        q0 = np.asarray(req.q0, dtype=float).reshape(-1)
        if q0.shape != (req.spec.dof,):
            raise ValueError(f'IK request q0 shape mismatch: expected {(req.spec.dof,)}, got {q0.shape}')
        if not np.isfinite(q0).all():
            raise ValueError('IK request q0 contains non-finite values')
        if not np.isfinite(np.asarray(req.target.p, dtype=float)).all() or not np.isfinite(np.asarray(req.target.R, dtype=float)).all():
            raise ValueError('IK request target pose contains non-finite values')
        if len(req.position_mask) != 3 or len(req.orientation_mask) != 3:
            raise ValueError('IK request masks must both have length 3')
        if req.timeout_ms is not None and float(req.timeout_ms) < 0.0:
            raise ValueError('IK request timeout_ms must be >= 0')

=======
>>>>>>> 3ed78e647985c6d680c085e4480d898855278db3
    def _execute_solver(self, req: IKRequest, cancel_flag=None, progress_cb=None, correlation_id: str | None = None) -> IKResult:
        solver = self._solvers.get(req.config.mode.value if hasattr(req.config.mode, 'value') else req.config.mode)
        seeds = self._candidate_seeds(req)
        best_result: IKResult | None = None
<<<<<<< HEAD
        deadline = time.perf_counter() + (float(req.timeout_ms) / 1000.0) if req.timeout_ms and float(req.timeout_ms) > 0.0 else None

        def timed_cancelled() -> bool:
            if cancel_flag is not None and cancel_flag():
                return True
            if deadline is not None and time.perf_counter() >= deadline:
                return True
            return False

        for attempt_idx, seed in enumerate(seeds):
            result = solver.solve(req.spec, req.target, seed, req.config, cancel_flag=timed_cancelled, progress_cb=progress_cb, attempt_idx=attempt_idx)
            result = self._decorate_result(result, req, attempt_idx, total_attempts=len(seeds), correlation_id=correlation_id, deadline=deadline)
=======

        for attempt_idx, seed in enumerate(seeds):
            result = solver.solve(req.spec, req.target, seed, req.config, cancel_flag=cancel_flag, progress_cb=progress_cb, attempt_idx=attempt_idx)
            result = self._decorate_result(result, attempt_idx, total_attempts=len(seeds), correlation_id=correlation_id)
>>>>>>> 3ed78e647985c6d680c085e4480d898855278db3
            if result.success or result.message == 'cancelled':
                return result
            if best_result is None or self._result_score(result) < self._result_score(best_result):
                best_result = result

        fallback = best_result if best_result is not None else IKResult(False, np.asarray(req.q0, dtype=float).copy(), tuple(), 'no IK attempts executed')
<<<<<<< HEAD
        return self._decorate_result(fallback, req, int(fallback.restarts_used), total_attempts=len(seeds), correlation_id=correlation_id, deadline=deadline)
=======
        return self._decorate_result(fallback, int(fallback.restarts_used), total_attempts=len(seeds), correlation_id=correlation_id)
>>>>>>> 3ed78e647985c6d680c085e4480d898855278db3

    def _candidate_seeds(self, req: IKRequest) -> list[np.ndarray]:
        seeds: list[np.ndarray] = []
        retry_count = max(int(req.config.retry_count), 0)
<<<<<<< HEAD
        mins = np.array([limit.lower for limit in req.spec.runtime_joint_limits], dtype=float)
        maxs = np.array([limit.upper for limit in req.spec.runtime_joint_limits], dtype=float)
=======
        mins = np.array([row.q_min for row in req.spec.dh_rows], dtype=float)
        maxs = np.array([row.q_max for row in req.spec.dh_rows], dtype=float)
>>>>>>> 3ed78e647985c6d680c085e4480d898855278db3
        mids = np.asarray(req.spec.q_mid(), dtype=float)
        rng = np.random.default_rng(int(req.config.random_seed))
        base_candidates = [
            np.asarray(req.q0, dtype=float),
<<<<<<< HEAD
            np.asarray(req.spec.runtime_model.home_q, dtype=float),
            mids,
            np.clip(0.5 * (np.asarray(req.q0, dtype=float) + np.asarray(req.spec.runtime_model.home_q, dtype=float)), mins, maxs),
=======
            np.asarray(req.spec.home_q, dtype=float),
            mids,
            np.clip(0.5 * (np.asarray(req.q0, dtype=float) + np.asarray(req.spec.home_q, dtype=float)), mins, maxs),
>>>>>>> 3ed78e647985c6d680c085e4480d898855278db3
            np.clip(0.5 * (mids + np.asarray(req.q0, dtype=float)), mins, maxs),
        ]
        random_needed = max(0, retry_count + 1 - len(base_candidates))
        for _ in range(random_needed):
            base_candidates.append(rng.uniform(mins, maxs))

        for candidate in base_candidates[: retry_count + 1]:
            if not any(np.allclose(candidate, existing, atol=1e-9) for existing in seeds):
                seeds.append(np.asarray(candidate, dtype=float).copy())
        if not seeds:
            seeds.append(np.asarray(req.q0, dtype=float).copy())
        return seeds

    def _result_score(self, result: IKResult) -> float:
        pos = result.final_pos_err
        ori = result.final_ori_err
        pos = float(pos) if np.isfinite(pos) else 1.0e12
        ori = float(ori) if np.isfinite(ori) else 1.0e12
        penalty = 0.0 if result.success else 1000.0
        return penalty + pos + ori

<<<<<<< HEAD
    def _decorate_result(self, result: IKResult, req: IKRequest, attempt_idx: int, *, total_attempts: int, correlation_id: str | None = None, deadline: float | None = None) -> IKResult:
=======
    def _decorate_result(self, result: IKResult, attempt_idx: int, *, total_attempts: int, correlation_id: str | None = None) -> IKResult:
>>>>>>> 3ed78e647985c6d680c085e4480d898855278db3
        message = result.message
        if attempt_idx > 0 and message not in {'cancelled', 'converged', 'analytic branch resolved'}:
            message = f"{message} | attempts={attempt_idx + 1}/{total_attempts}"
        diagnostics = dict(result.diagnostics)
        diagnostics.setdefault('attempt_idx', attempt_idx)
        diagnostics.setdefault('total_attempts', total_attempts)
        diagnostics.setdefault('solver_registry_ids', self.solver_ids)
        diagnostics['correlation_id'] = str(correlation_id or diagnostics.get('correlation_id', '') or '')
<<<<<<< HEAD
        diagnostics['target_frame'] = getattr(req.target_frame, 'value', str(req.target_frame))
        diagnostics['position_mask'] = list(bool(v) for v in req.position_mask)
        diagnostics['orientation_mask'] = list(bool(v) for v in req.orientation_mask)
        diagnostics['seed_policy'] = getattr(req.seed_policy, 'value', str(req.seed_policy))
        diagnostics['allow_approximate_solution'] = bool(req.allow_approximate_solution)
        diagnostics['constraint_summary'] = {
            'target_frame': req.constraint_summary.target_frame,
            'position_only': req.constraint_summary.position_only,
            'orientation_weight': req.constraint_summary.orientation_weight,
            'notes': list(req.constraint_summary.notes),
        }
        if deadline is not None:
            diagnostics['timeout_ms'] = float(req.timeout_ms or 0.0)
            if not result.success and result.message == 'cancelled' and result.stop_reason == 'cancelled':
                diagnostics.setdefault('cancelled_by_timeout', True)
        warnings = tuple(str(item) for item in result.warnings)
        if not result.success and req.allow_approximate_solution:
            warnings = warnings + ('approximate solution permitted but not achieved',)
        status = 'succeeded' if result.success else (result.stop_reason or 'failed')
=======
>>>>>>> 3ed78e647985c6d680c085e4480d898855278db3
        return IKResult(
            success=result.success,
            q_sol=result.q_sol,
            logs=result.logs,
            message=message,
            final_pos_err=result.final_pos_err,
            final_ori_err=result.final_ori_err,
            final_cond=result.final_cond,
            final_manipulability=result.final_manipulability,
            final_dq_norm=result.final_dq_norm,
            elapsed_ms=result.elapsed_ms,
            effective_mode=result.effective_mode,
            stop_reason=result.stop_reason,
            best_q=result.best_q,
            restarts_used=attempt_idx,
            diagnostics=diagnostics,
<<<<<<< HEAD
            status=status,
            residuals={'position': float(result.final_pos_err), 'orientation': float(result.final_ori_err)} if np.isfinite(result.final_pos_err) and np.isfinite(result.final_ori_err) else dict(result.residuals),
            attempt_count=max(total_attempts if result.success else attempt_idx + 1, 1),
            warnings=warnings,
=======
>>>>>>> 3ed78e647985c6d680c085e4480d898855278db3
        )

    def _attach_adapter_metadata(self, result: IKResult, prepared, *, correlation_id: str | None = None) -> IKResult:
        diagnostics = dict(result.diagnostics)
        adapter_entries = list((diagnostics.get('request_adapters') or []))
        adapter_entries.extend(list((prepared.metadata or {}).get('request_adapters', [])))
        if adapter_entries:
            diagnostics['request_adapters'] = adapter_entries
        if prepared.notes:
            diagnostics['request_adapter_notes'] = list(prepared.notes)
        diagnostics['correlation_id'] = str(correlation_id or diagnostics.get('correlation_id', '') or '')
        return IKResult(
            success=result.success,
            q_sol=result.q_sol,
            logs=result.logs,
            message=result.message,
            final_pos_err=result.final_pos_err,
            final_ori_err=result.final_ori_err,
            final_cond=result.final_cond,
            final_manipulability=result.final_manipulability,
            final_dq_norm=result.final_dq_norm,
            elapsed_ms=result.elapsed_ms,
            effective_mode=result.effective_mode,
            stop_reason=result.stop_reason,
            best_q=result.best_q,
            restarts_used=result.restarts_used,
            diagnostics=diagnostics,
<<<<<<< HEAD
            status=result.status,
            residuals=dict(result.residuals),
            attempt_count=result.attempt_count,
            warnings=tuple(result.warnings),
=======
>>>>>>> 3ed78e647985c6d680c085e4480d898855278db3
        )
