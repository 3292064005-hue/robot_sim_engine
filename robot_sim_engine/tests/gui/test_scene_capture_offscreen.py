from __future__ import annotations

import pytest

from robot_sim.testing.qt_shims import real_pyside6_available

if not real_pyside6_available():
    pytest.skip('real PySide6 runtime is unavailable', allow_module_level=True)

from robot_sim.render.scene_3d_widget import Scene3DWidget
from robot_sim.render.screenshot_service import ScreenshotService


def test_scene_widget_snapshot_available_without_plotter(tmp_path):
    from PySide6.QtWidgets import QApplication

    _app = QApplication.instance() or QApplication([])
    widget = Scene3DWidget()
    snap = widget.scene_snapshot()
    assert 'overlay_text' in snap
    service = ScreenshotService()
    path = tmp_path / 'scene_widget_snapshot.png'
    service.capture_from_snapshot(snap, path)
    assert path.exists()
    assert path.stat().st_size > 0
