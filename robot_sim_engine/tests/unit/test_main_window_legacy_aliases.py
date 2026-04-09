from __future__ import annotations

from robot_sim.presentation.main_window import MainWindow


def test_main_window_no_longer_exposes_legacy_private_aliases() -> None:
    for name in ('_load_robot_impl', '_run_ik_impl', '_run_traj_impl', '_save_robot_impl'):
        assert not hasattr(MainWindow, name)
