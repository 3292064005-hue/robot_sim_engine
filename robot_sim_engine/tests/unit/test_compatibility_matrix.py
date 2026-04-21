from __future__ import annotations

from robot_sim.app.compatibility_matrix import COMPATIBILITY_MATRIX


def test_compatibility_matrix_is_empty_for_clean_mainline() -> None:
    assert COMPATIBILITY_MATRIX == ()
