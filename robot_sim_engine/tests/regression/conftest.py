from __future__ import annotations

from robot_sim.testing.qt_shims import install_pyside6_test_shims, real_pyside6_available

if not real_pyside6_available():
    install_pyside6_test_shims()
