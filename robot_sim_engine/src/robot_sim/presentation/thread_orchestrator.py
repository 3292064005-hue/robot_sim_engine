from __future__ import annotations

try:
    from PySide6.QtCore import QObject, QThread
except Exception:  # pragma: no cover
    QObject = object  # type: ignore
    QThread = object  # type: ignore


class ThreadOrchestrator(QObject):  # pragma: no cover - GUI shell
    def __init__(self, parent=None):
        super().__init__(parent)
        self._thread = None
        self._worker = None

    @property
    def worker(self):
        return self._worker

    def is_running(self) -> bool:
        return self._thread is not None

    def start(self, worker, on_progress=None, on_finished=None, on_failed=None, on_cancelled=None, on_started=None) -> None:
        self.stop(wait=False)
        thread = QThread()
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        if on_started is not None:
            worker.started.connect(on_started)
        if on_progress is not None:
            worker.progress.connect(on_progress)
        if on_finished is not None:
            worker.finished.connect(on_finished)
        if on_failed is not None:
            worker.failed.connect(on_failed)
        if on_cancelled is not None:
            worker.cancelled.connect(on_cancelled)
        worker.finished.connect(thread.quit)
        worker.failed.connect(thread.quit)
        worker.cancelled.connect(thread.quit)
        thread.finished.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)
        self._thread = thread
        self._worker = worker
        thread.finished.connect(self._cleanup)
        thread.start()

    def cancel(self) -> None:
        if self._worker is not None:
            self._worker.request_cancel()

    def stop(self, wait: bool = True) -> None:
        if self._thread is None:
            return
        if self._worker is not None:
            self._worker.request_cancel()
        self._thread.quit()
        if wait:
            self._thread.wait()
        self._cleanup()

    def _cleanup(self) -> None:
        self._thread = None
        self._worker = None
