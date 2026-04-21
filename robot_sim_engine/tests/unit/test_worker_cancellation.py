from __future__ import annotations

from robot_sim.application.workers.export_worker import ExportWorker
from robot_sim.application.workers.screenshot_worker import ScreenshotWorker


def test_export_worker_honors_cancellation_before_start():
    worker = ExportWorker(lambda *, progress_cb=None, cancel_flag=None, correlation_id='': 'done')
    worker.request_cancel()
    worker.run()
    assert worker.state == 'cancelled'


def test_screenshot_worker_honors_cancellation_before_start():
    worker = ScreenshotWorker(lambda *, progress_cb=None, cancel_flag=None, correlation_id='': 'done')
    worker.request_cancel()
    worker.run()
    assert worker.state == 'cancelled'
