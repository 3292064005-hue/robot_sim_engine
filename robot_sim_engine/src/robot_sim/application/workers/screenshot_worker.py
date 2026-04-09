from __future__ import annotations

<<<<<<< HEAD
from typing import Any

from robot_sim.application.workers.base import BaseWorker, Slot
from robot_sim.application.workers.invocation import build_structured_progress_callback, call_with_worker_support
=======
import inspect
from typing import Any

from robot_sim.application.workers.base import BaseWorker, Slot
>>>>>>> 3ed78e647985c6d680c085e4480d898855278db3
from robot_sim.domain.errors import CancelledTaskError


class ScreenshotWorker(BaseWorker):
    """Qt worker wrapper for screenshot capture operations."""

    def __init__(self, func, *args, **kwargs):
        """Create a screenshot worker.

        Args:
            func: Callable that performs screenshot capture.
            *args: Positional arguments forwarded to ``func``.
            **kwargs: Keyword arguments forwarded to ``func``.
<<<<<<< HEAD

        Returns:
            None: Stores the capture callable and its arguments.

        Raises:
            None: Construction only stores explicit dependencies.
=======
>>>>>>> 3ed78e647985c6d680c085e4480d898855278db3
        """
        super().__init__(task_kind='screenshot')
        self._func = func
        self._args = args
        self._kwargs = kwargs

    def _invoke_with_control(self) -> Any:
<<<<<<< HEAD
        """Invoke the capture callable while preserving backward compatibility.

        Returns:
            Any: Path or payload returned by the capture callable.

        Raises:
            Exception: Re-raises capture failures unchanged.
        """
        return call_with_worker_support(
            self._func,
            *self._args,
            cancel_flag=self.is_cancel_requested,
            correlation_id=self.correlation_id,
            progress_factory=lambda: build_structured_progress_callback(
                emit_progress=self.emit_progress,
                stage='screenshot',
            ),
            keyword_overrides=self._kwargs,
        )

    @staticmethod
    def _build_cancelled_metadata(exc: CancelledTaskError) -> dict[str, object]:
        """Build structured cancellation metadata for downstream lifecycle consumers.

        Args:
            exc: Cooperative cancellation exception raised by the capture callable.

        Returns:
            dict[str, object]: Flattened structured metadata suitable for
                ``WorkerCancelledEvent.metadata``.

        Raises:
            None: Metadata is normalized defensively.

        Boundary behavior:
            Cancellation telemetry is projected through structured cancellation events
            instead of being tunneled through the success payload path.
        """
        metadata = dict(getattr(exc, 'metadata', {}) or {})
        error_code = str(getattr(exc, 'error_code', '') or '')
        remediation_hint = str(getattr(exc, 'remediation_hint', '') or '')
        if error_code:
            metadata.setdefault('error_code', error_code)
        if remediation_hint:
            metadata.setdefault('remediation_hint', remediation_hint)
        metadata.setdefault('exception_type', exc.__class__.__name__)
        return metadata

    @Slot()
    def run(self):
        """Execute the screenshot callable and emit terminal worker events.

        Returns:
            None: Emits started/progress/finished/cancelled/failed signals.

        Raises:
            None: Execution failures are projected through worker failure events.

        Boundary behavior:
            - Cooperative cancellation is checked before and after the capture callable.
            - ``CancelledTaskError`` is normalized to a structured cancellation event.
            - Terminal failure/cancellation state is never tunneled through ``finished``.
        """
=======
        """Invoke the capture callable while preserving backward compatibility."""
        kwargs = dict(self._kwargs)
        try:
            signature = inspect.signature(self._func)
        except (TypeError, ValueError):
            signature = None
        accepted = set(signature.parameters) if signature is not None else set()
        if 'cancel_flag' in accepted:
            kwargs.setdefault('cancel_flag', self.is_cancel_requested)
        if 'progress_cb' in accepted:
            kwargs.setdefault(
                'progress_cb',
                lambda percent, message='', payload=None: self.emit_progress(
                    stage='screenshot',
                    percent=float(percent),
                    message=str(message),
                    payload=dict(payload or {}),
                ),
            )
        if 'correlation_id' in accepted:
            kwargs.setdefault('correlation_id', self.correlation_id)
        return self._func(*self._args, **kwargs)

    @Slot()
    def run(self):
        """Execute the screenshot callable and emit terminal worker events."""
>>>>>>> 3ed78e647985c6d680c085e4480d898855278db3
        self.emit_started()
        try:
            if self.is_cancelled():
                self.emit_cancelled(stop_reason='cancelled')
                return
<<<<<<< HEAD
            payload = self._invoke_with_control()
            if self.is_cancelled():
                self.emit_cancelled(stop_reason='cancelled')
                return
            self.emit_finished(payload)
        except CancelledTaskError as exc:
            self.emit_cancelled(
                stop_reason='cancelled',
                message=str(exc),
                metadata=self._build_cancelled_metadata(exc),
            )
=======
            path = self._invoke_with_control()
            if self.is_cancelled():
                self.emit_cancelled(stop_reason='cancelled')
                return
            self.emit_finished(path)
        except CancelledTaskError as exc:
            self.emit_cancelled(stop_reason='cancelled', message=str(exc), metadata=exc.to_dict())
>>>>>>> 3ed78e647985c6d680c085e4480d898855278db3
        except Exception as exc:
            self.emit_failed(exc)
