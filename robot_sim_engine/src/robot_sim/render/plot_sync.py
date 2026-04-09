from __future__ import annotations

<<<<<<< HEAD
from robot_sim.render.experimental.plot_sync import PlotSync


__all__ = ['PlotSync']
=======

class PlotSync:
    def __init__(self) -> None:
        self._last_x = 0.0

    @property
    def last_x(self) -> float:
        return float(self._last_x)

    def sync(self, plots_manager, plot_keys: list[str], x_value: float) -> None:
        self._last_x = float(x_value)
        for key in plot_keys:
            plots_manager.set_cursor(key, self._last_x)
>>>>>>> 3ed78e647985c6d680c085e4480d898855278db3
