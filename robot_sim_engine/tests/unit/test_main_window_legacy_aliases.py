from __future__ import annotations

from robot_sim.presentation.legacy_aliases import MainWindowLegacyAliasMixin


class DummyLegacyWindow(MainWindowLegacyAliasMixin):
    def __init__(self) -> None:
        self.calls: list[str] = []

    def on_load_robot(self) -> None:
        self.calls.append('load')

    def on_run_ik(self) -> None:
        self.calls.append('ik')

    def on_plan(self) -> None:
        self.calls.append('traj')


def test_legacy_main_window_aliases_redirect_to_public_handlers() -> None:
    window = DummyLegacyWindow()
    window._load_robot_impl()
    window._run_ik_impl()
    window._run_traj_impl()
    assert window.calls == ['load', 'ik', 'traj']


def test_unknown_legacy_alias_raises_attribute_error() -> None:
    window = DummyLegacyWindow()
    try:
        getattr(window, '_missing_impl')
    except AttributeError:
        return
    raise AssertionError('expected AttributeError for unknown alias')
