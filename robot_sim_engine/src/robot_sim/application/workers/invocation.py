from __future__ import annotations

import inspect
from collections.abc import Callable, Mapping
from typing import Any


ProgressCallbackFactory = Callable[[], Callable[..., None]]


def build_structured_progress_callback(*, emit_progress: Callable[..., None], stage: str) -> Callable[..., None]:
    """Build a generic worker progress callback.

    Args:
        emit_progress: Worker progress emitter accepting ``stage``, ``percent``, ``message``, and ``payload``.
        stage: Stable worker stage label.

    Returns:
        Callable[..., None]: Callback compatible with use cases that emit
        ``progress_cb(percent, message='', payload=None)``.

    Raises:
        None: The callback normalizes missing/invalid payloads defensively.
    """

    def _callback(percent: float, message: str = '', payload: Mapping[str, object] | None = None) -> None:
        emit_progress(
            stage=stage,
            percent=float(percent),
            message=str(message),
            payload=dict(payload or {}),
        )

    return _callback



def build_payload_progress_callback(
    *,
    emit_progress: Callable[..., None],
    stage: str,
    default_message: str = '',
) -> Callable[[object], None]:
    """Build a payload-only worker progress callback.

    Args:
        emit_progress: Worker progress emitter accepting ``stage``, ``percent``, ``message``, and ``payload``.
        stage: Stable worker stage label.
        default_message: Fallback user-facing message when the payload does not include one.

    Returns:
        Callable[[object], None]: Callback compatible with use cases that emit
        ``progress_cb(payload)``.

    Raises:
        None: The callback wraps non-mapping payloads into the legacy ``{'value': ...}`` envelope.
    """

    def _callback(payload: object) -> None:
        normalized_payload = payload if isinstance(payload, dict) else {'value': payload}
        percent = 0.0
        message = str(default_message)
        if isinstance(normalized_payload, dict):
            raw_percent = normalized_payload.get('percent', 0.0)
            try:
                percent = float(raw_percent)
            except (TypeError, ValueError):
                percent = 0.0
            raw_message = normalized_payload.get('message', default_message)
            message = str(raw_message)
        emit_progress(
            stage=stage,
            percent=percent,
            message=message,
            payload=dict(normalized_payload),
        )

    return _callback



def call_with_worker_support(
    func: Callable[..., Any],
    *args: object,
    cancel_flag: Callable[[], bool],
    correlation_id: str,
    progress_factory: ProgressCallbackFactory | None = None,
    keyword_overrides: Mapping[str, object] | None = None,
) -> Any:
    """Call a use case while injecting supported worker control arguments.

    Args:
        func: Use-case callable to invoke.
        *args: Positional arguments forwarded to ``func``.
        cancel_flag: Cooperative cancellation probe exposed to the callable when supported.
        correlation_id: Stable correlation identifier propagated when supported.
        progress_factory: Optional callback factory used when the callable accepts ``progress_cb``.
        keyword_overrides: Optional explicit keyword arguments merged after injected control kwargs.

    Returns:
        Any: Result returned by ``func``.

    Raises:
        Exception: Re-raises callable failures unchanged.

    Boundary behavior:
        Signature introspection failures do not block execution; the function is called with the
        original explicit arguments only.
    """
    kwargs: dict[str, object] = dict(keyword_overrides or {})
    try:
        accepted = set(inspect.signature(func).parameters)
    except (TypeError, ValueError):
        accepted = set()
    if 'cancel_flag' in accepted:
        kwargs.setdefault('cancel_flag', cancel_flag)
    if 'progress_cb' in accepted and progress_factory is not None:
        kwargs.setdefault('progress_cb', progress_factory())
    if 'correlation_id' in accepted:
        kwargs.setdefault('correlation_id', str(correlation_id))
    return func(*args, **kwargs)
