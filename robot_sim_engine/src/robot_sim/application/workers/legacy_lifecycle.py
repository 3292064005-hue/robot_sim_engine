from __future__ import annotations

from dataclasses import dataclass

from robot_sim.infra.compatibility_usage import record_compatibility_usage
from robot_sim.application.workers.task_events import (
    WorkerCancelledEvent,
    WorkerFailedEvent,
    WorkerFinishedEvent,
    WorkerProgressEvent,
)


@dataclass(frozen=True)
class LegacyWorkerLifecycleAdapter:
    """Compatibility adapter that mirrors structured worker lifecycle events to legacy Qt signals.

    The application uses structured worker events as the canonical lifecycle contract.
    This adapter confines legacy signal payload translation to one place so workers can
    continue exposing the old signal surface without duplicating conversion logic.
    """

    def emit_progress(self, worker, event: WorkerProgressEvent) -> None:
        """Mirror a structured progress event onto the legacy ``progress`` signal.

        Args:
            worker: Worker instance exposing the legacy ``progress`` signal.
            event: Canonical structured progress event.

        Returns:
            None: Emits the translated legacy payload when the signal exists.

        Raises:
            None: Missing legacy signals are ignored for backward-compatible workers.

        Boundary behavior:
            When the structured payload contains only ``{'value': ...}``, the adapter
            unwraps it to preserve the historical callback payload contract.
        """
        signal = getattr(worker, 'progress', None)
        if signal is None:
            return
        record_compatibility_usage('worker legacy lifecycle signals', detail='progress')
        signal.emit(self.coerce_legacy_progress(event))

    def emit_finished(self, worker, event: WorkerFinishedEvent) -> None:
        """Mirror a structured success event onto the legacy ``finished`` signal."""
        signal = getattr(worker, 'finished', None)
        if signal is None:
            return
        record_compatibility_usage('worker legacy lifecycle signals', detail='finished')
        signal.emit(getattr(event, 'payload', event))

    def emit_failed(self, worker, event: WorkerFailedEvent) -> None:
        """Mirror a structured failure event onto the legacy ``failed`` signal."""
        signal = getattr(worker, 'failed', None)
        if signal is None:
            return
        record_compatibility_usage('worker legacy lifecycle signals', detail='failed')
        signal.emit(str(getattr(event, 'message', '')))

    def emit_cancelled(self, worker, _event: WorkerCancelledEvent) -> None:
        """Mirror a structured cancellation event onto the legacy ``cancelled`` signal."""
        signal = getattr(worker, 'cancelled', None)
        if signal is None:
            return
        record_compatibility_usage('worker legacy lifecycle signals', detail='cancelled')
        signal.emit()

    @staticmethod
    def coerce_legacy_progress(event: WorkerProgressEvent | object) -> object:
        """Translate a structured progress event into the legacy callback payload.

        Args:
            event: Structured progress event or fallback payload.

        Returns:
            object: Historically compatible payload passed to ``progress`` handlers.

        Raises:
            None: Unsupported payload shapes simply fall back to the input event.
        """
        payload = getattr(event, 'payload', None)
        if isinstance(payload, dict) and 'value' in payload and len(payload) == 1:
            return payload['value']
        if payload is not None:
            return payload
        return event
