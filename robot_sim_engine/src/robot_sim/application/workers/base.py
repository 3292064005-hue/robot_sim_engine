from __future__ import annotations
try:
    from PySide6.QtCore import QObject, Signal, Slot
except Exception:  # pragma: no cover
    class QObject:  # type: ignore
        pass
    def Slot(*args, **kwargs):  # type: ignore
        def deco(fn):
            return fn
        return deco
    class _DummySignal:
        def __init__(self, *args, **kwargs): ...
        def emit(self, *args, **kwargs): ...
    Signal = _DummySignal  # type: ignore

class BaseWorker(QObject):
    started = Signal()
    progress = Signal(object)
    finished = Signal(object)
    failed = Signal(str)
    cancelled = Signal()

    def __init__(self) -> None:
        super().__init__()
        self._cancel_requested = False

    def request_cancel(self) -> None:
        self._cancel_requested = True

    def is_cancel_requested(self) -> bool:
        return self._cancel_requested
