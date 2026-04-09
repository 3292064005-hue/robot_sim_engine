from __future__ import annotations

import pytest

pytest.importorskip('PySide6')

from robot_sim.render.scene_3d_widget import Scene3DWidget


def test_scene_widget_exposes_render_runtime_snapshot_offscreen():
    from PySide6.QtWidgets import QApplication

    _app = QApplication.instance() or QApplication([])
    widget = Scene3DWidget()
    snapshot = widget.render_runtime_snapshot()
    assert snapshot['scene_3d'].capability == 'scene_3d'
    assert snapshot['screenshot'].capability == 'screenshot'
    assert snapshot['scene_3d'].level in {'live_3d', 'placeholder_view', 'snapshot_only'}
    assert snapshot['screenshot'].level in {'live_capture', 'snapshot_capture', 'unsupported'}
