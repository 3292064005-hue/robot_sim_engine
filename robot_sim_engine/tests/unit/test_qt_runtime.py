from __future__ import annotations

import importlib
import importlib.util
import sys

import pytest

from robot_sim.infra.qt_runtime import configure_qt_platform_for_pytest
from robot_sim.testing.qt_shims import install_pyside6_test_shims, real_pyside6_available, uninstall_pyside6_test_shims


def test_configure_qt_platform_for_pytest_defaults_to_offscreen() -> None:
    env: dict[str, str] = {}

    selected = configure_qt_platform_for_pytest(env)

    assert selected == 'offscreen'
    assert env['QT_QPA_PLATFORM'] == 'offscreen'


def test_configure_qt_platform_for_pytest_respects_explicit_platform() -> None:
    env = {'QT_QPA_PLATFORM': 'xcb'}

    selected = configure_qt_platform_for_pytest(env)

    assert selected == 'xcb'
    assert env['QT_QPA_PLATFORM'] == 'xcb'


def test_configure_qt_platform_for_pytest_allows_display_opt_out() -> None:
    env = {'ROBOT_SIM_PYTEST_FORCE_GUI_DISPLAY': '1'}

    selected = configure_qt_platform_for_pytest(env)

    assert selected is None
    assert 'QT_QPA_PLATFORM' not in env


@pytest.mark.skipif(real_pyside6_available(), reason='strict missing-Qt path only applies when real PySide6 is absent')
def test_presentation_qt_runtime_consumes_injected_test_pyside6_package() -> None:
    install_pyside6_test_shims()
    sys.modules.pop('robot_sim.presentation.qt_runtime', None)
    module = importlib.import_module('robot_sim.presentation.qt_runtime')
    try:
        assert module.QT_RUNTIME_AVAILABLE is True
        assert module.QWidget.__module__ == 'robot_sim.testing.qt_shims'
        module.require_qt_runtime('MainWindow UI')
    finally:
        sys.modules.pop('robot_sim.presentation.qt_runtime', None)
        install_pyside6_test_shims()
        importlib.import_module('robot_sim.presentation.qt_runtime')


@pytest.mark.skipif(real_pyside6_available(), reason='strict missing-Qt path only applies when real PySide6 is absent')
def test_presentation_qt_runtime_rejects_stable_gui_construction_without_qt(monkeypatch) -> None:
    uninstall_pyside6_test_shims()
    monkeypatch.delenv('QT_QPA_PLATFORM', raising=False)
    sys.modules.pop('robot_sim.presentation.qt_runtime', None)
    module = importlib.import_module('robot_sim.presentation.qt_runtime')
    try:
        assert module.QT_RUNTIME_AVAILABLE is False
        with pytest.raises(RuntimeError, match='PySide6'):
            module.require_qt_runtime('MainWindow UI')
    finally:
        sys.modules.pop('robot_sim.presentation.qt_runtime', None)
        install_pyside6_test_shims()
        importlib.import_module('robot_sim.presentation.qt_runtime')
