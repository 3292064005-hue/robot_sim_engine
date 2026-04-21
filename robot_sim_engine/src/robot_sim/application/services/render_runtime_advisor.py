from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from robot_sim.model.render_runtime import RenderRuntimeState
from robot_sim.model.render_telemetry import RenderBackendPerformanceTelemetry, normalize_render_backend_performance


@dataclass(frozen=True)
class RenderAdviceThresholds:
    """Thresholds used to project render telemetry into actionable runtime advice.

    Attributes:
        high_p95_ms: Latency percentile beyond which the backend should be considered slow.
        high_average_ms: Average duration threshold used for sustained regressions.
        high_failure_ratio: Failure ratio beyond which fallback guidance becomes urgent.
        high_span_rate_per_sec: Span rate above which throttling guidance is projected.
    """

    high_p95_ms: float = 33.0
    high_average_ms: float = 20.0
    high_failure_ratio: float = 0.20
    high_span_rate_per_sec: float = 24.0


class RenderRuntimeAdvisor:
    """Project render telemetry into deterministic runtime-strategy advice.

    The advisor is suggestion-only. It does not auto-switch backends. Instead it translates
    backend performance snapshots and current runtime status into explicit actions that UI,
    diagnostics, export, and future policy engines can consume.
    """

    def __init__(self, thresholds: RenderAdviceThresholds | None = None) -> None:
        self._thresholds = thresholds or RenderAdviceThresholds()

    def build_advice(
        self,
        render_runtime: RenderRuntimeState | dict[str, object],
        backend_performance: Iterable[RenderBackendPerformanceTelemetry | dict[str, object]],
    ) -> dict[str, object]:
        """Build structured render-runtime advice from runtime state and telemetry.

        Args:
            render_runtime: Current typed render-runtime state or mapping payload.
            backend_performance: Backend-specific performance telemetry snapshots.

        Returns:
            dict[str, object]: Structured advice summary keyed for diagnostics/export/UI.

        Raises:
            None: Unknown backends or sparse telemetry degrade to advisory no-op output.
        """
        runtime = RenderRuntimeState.from_mapping(render_runtime)
        perf_rows = tuple(normalize_render_backend_performance(tuple(backend_performance or ())))
        perf_map = {(row.capability, row.backend): row for row in perf_rows}
        recommendations: list[dict[str, object]] = []
        for capability_state in (runtime.scene_3d, runtime.plots, runtime.screenshot):
            perf = perf_map.get((capability_state.capability, capability_state.backend))
            recommendation = self._recommend_for_capability(capability_state, perf)
            if recommendation is not None:
                recommendations.append(recommendation)
        severity = 'nominal'
        if any(item['severity'] == 'critical' for item in recommendations):
            severity = 'critical'
        elif recommendations:
            severity = 'warning'
        return {
            'severity': severity,
            'recommendation_count': len(recommendations),
            'recommendations': recommendations,
            'thresholds': {
                'high_p95_ms': float(self._thresholds.high_p95_ms),
                'high_average_ms': float(self._thresholds.high_average_ms),
                'high_failure_ratio': float(self._thresholds.high_failure_ratio),
                'high_span_rate_per_sec': float(self._thresholds.high_span_rate_per_sec),
            },
        }

    def _recommend_for_capability(self, capability_state, perf: RenderBackendPerformanceTelemetry | None) -> dict[str, object] | None:
        thresholds = self._thresholds
        failure_ratio = 0.0
        if perf is not None and perf.total_spans > 0:
            failure_ratio = float(perf.failed_spans) / float(perf.total_spans)
        p95_ms = 0.0 if perf is None else float(perf.duration_percentiles_ms.get('p95', perf.average_duration_ms))
        average_ms = 0.0 if perf is None else float(perf.average_duration_ms)
        span_rate = 0.0 if perf is None else float(perf.rolling_span_rate_per_sec)

        severity = 'warning'
        action = ''
        rationale = ''
        if capability_state.status == 'unsupported':
            severity = 'critical'
            action = 'keep_capability_disabled'
            rationale = 'capability is unsupported in the current runtime and should remain disabled until dependencies are restored'
        elif capability_state.status == 'degraded' and failure_ratio >= thresholds.high_failure_ratio:
            severity = 'critical'
            action = 'switch_to_fallback_backend'
            rationale = 'degraded backend is failing frequently; operators should switch to the declared fallback backend before continuing'
        elif capability_state.status == 'degraded':
            action = 'prefer_degraded_fallback'
            rationale = 'capability is already degraded; downstream workflows should prefer the advertised fallback path'
        elif p95_ms >= thresholds.high_p95_ms or average_ms >= thresholds.high_average_ms:
            action = 'reduce_sampling_rate'
            rationale = 'backend latency is above the stable target and should be mitigated through lower sampling or lighter render work'
        elif span_rate >= thresholds.high_span_rate_per_sec and average_ms > 0.0:
            action = 'throttle_render_updates'
            rationale = 'backend update rate is high relative to observed span cost and should be throttled before the runtime degrades'
        else:
            return None

        return {
            'capability': capability_state.capability,
            'backend': capability_state.backend,
            'status': capability_state.status,
            'severity': severity,
            'action': action,
            'reason': capability_state.reason,
            'error_code': capability_state.error_code,
            'message': capability_state.message,
            'rationale': rationale,
            'metrics': {
                'p95_ms': float(p95_ms),
                'average_ms': float(average_ms),
                'failure_ratio': float(round(failure_ratio, 4)),
                'rolling_span_rate_per_sec': float(span_rate),
            },
        }


__all__ = ['RenderAdviceThresholds', 'RenderRuntimeAdvisor']
