from __future__ import annotations

import pytest

from robot_sim.model.session_state import SessionState
from robot_sim.presentation.state_store import StateStore



def test_render_telemetry_service_rejects_unsupported_capability() -> None:
    store = StateStore(SessionState())

    with pytest.raises(ValueError, match='unsupported render capability'):
        store.patch_render_capability('unknown_capability', {'status': 'ready'})
