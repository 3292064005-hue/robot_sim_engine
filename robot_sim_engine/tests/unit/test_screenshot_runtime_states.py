from __future__ import annotations

from robot_sim.render.screenshot_service import ScreenshotService


class _DummyPlotter:
    def screenshot(self, path: str) -> None:
        raise AssertionError('not used during runtime_state test')


class _LiveScene:
    plotter = _DummyPlotter()


class _SnapshotScene:
    plotter = None

    def scene_snapshot(self):
        return {'overlay_text': 'snapshot'}


class _UnsupportedScene:
    plotter = None


def test_screenshot_runtime_state_reports_live_plotter_backend():
    state = ScreenshotService().runtime_state(_LiveScene())
    assert state.status == 'available'
    assert state.backend == 'live_plotter'
    assert state.level == 'live_capture'
    assert state.provenance['capture_source'] == 'live_plotter_framebuffer'


def test_screenshot_runtime_state_reports_snapshot_fallback():
    state = ScreenshotService().runtime_state(_SnapshotScene())
    assert state.status == 'degraded'
    assert state.backend == 'snapshot_renderer'
    assert state.level == 'snapshot_capture'
    assert state.provenance['capture_source'] == 'scene_snapshot'


def test_screenshot_runtime_state_reports_unsupported_backend():
    state = ScreenshotService().runtime_state(_UnsupportedScene())
    assert state.status == 'unsupported'
    assert state.error_code == 'unsupported_capture_backend'
    assert state.level == 'unsupported'
    assert state.provenance['render_path'] == 'none'
