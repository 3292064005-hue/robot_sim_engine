from __future__ import annotations

import pytest

from robot_sim.testing.qt_shims import real_pyside6_available

if not real_pyside6_available():
    pytest.skip('real PySide6 runtime is unavailable', allow_module_level=True)

from robot_sim.app.bootstrap import get_project_root
from robot_sim.app.container import build_container
from robot_sim.presentation.main_window import MainWindow


def test_main_window_constructs():
    from PySide6.QtWidgets import QApplication
    _app = QApplication.instance() or QApplication([])
    root = get_project_root()
    w = MainWindow(root, container=build_container(root))
    assert w.controller is not None
    assert w.metrics_service is w.controller.metrics_service
    w.close()
