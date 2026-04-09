from __future__ import annotations

from robot_sim.application.services.metrics_service import MetricsService
from robot_sim.presentation.state_store import StateStore


class DiagnosticsController:
    def __init__(self, state_store: StateStore, metrics_service: MetricsService) -> None:
        if metrics_service is None:
            raise ValueError('DiagnosticsController requires an explicit metrics service')
        self._state_store = state_store
        self._metrics = metrics_service

    def snapshot(self) -> dict[str, object]:
        state = self._state_store.state
        payload: dict[str, object] = {}
        if state.ik_result is not None:
            payload['ik'] = self._metrics.summarize_ik(state.ik_result)
        if state.trajectory is not None:
            payload['trajectory'] = self._metrics.summarize_trajectory(state.trajectory)
        if state.benchmark_report is not None:
            payload['benchmark'] = self._metrics.summarize_benchmark(state.benchmark_report)
<<<<<<< HEAD
        payload['render_runtime'] = state.render_runtime.as_dict() if hasattr(state.render_runtime, 'as_dict') else dict(state.render_runtime)
        payload['render_telemetry'] = {
            'event_count': len(tuple(getattr(state, 'render_telemetry', ()) or ())),
            'sequence': int(getattr(state, 'render_telemetry_sequence', 0) or 0),
            'events': [event.as_dict() if hasattr(event, 'as_dict') else dict(event) for event in tuple(getattr(state, 'render_telemetry', ()) or ())],
            'operation_span_count': len(tuple(getattr(state, 'render_operation_spans', ()) or ())),
            'operation_sequence': int(getattr(state, 'render_operation_sequence', 0) or 0),
            'operation_spans': [span.as_dict() if hasattr(span, 'as_dict') else dict(span) for span in tuple(getattr(state, 'render_operation_spans', ()) or ())],
            'sampling_counter_count': len(tuple(getattr(state, 'render_sampling_counters', ()) or ())),
            'sampling_sequence': int(getattr(state, 'render_sampling_sequence', 0) or 0),
            'sampling_counters': [counter.as_dict() if hasattr(counter, 'as_dict') else dict(counter) for counter in tuple(getattr(state, 'render_sampling_counters', ()) or ())],
            'backend_count': len(tuple(getattr(state, 'render_backend_performance', ()) or ())),
            'backend_performance': [entry.as_dict() if hasattr(entry, 'as_dict') else dict(entry) for entry in tuple(getattr(state, 'render_backend_performance', ()) or ())],
        }
=======
>>>>>>> 3ed78e647985c6d680c085e4480d898855278db3
        return payload
