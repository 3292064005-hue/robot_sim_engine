from __future__ import annotations

from dataclasses import replace
from typing import Any

from robot_sim.model.session_state import SessionState


class StateStore:
    """Minimal mutable state container for the GUI layer.

    The current GUI does not need a full Redux-style store, but centralizing
    state mutations here avoids scattering ad-hoc field writes across widgets.
    """

    def __init__(self, state: SessionState | None = None) -> None:
        self._state = state or SessionState()

    @property
    def state(self) -> SessionState:
        return self._state

    def patch(self, **kwargs: Any) -> SessionState:
        for key, value in kwargs.items():
            setattr(self._state, key, value)
        return self._state
