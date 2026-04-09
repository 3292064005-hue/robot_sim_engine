from robot_sim.app.compatibility_matrix import COMPATIBILITY_MATRIX


def test_compatibility_matrix_is_empty_after_retiring_runtime_shims() -> None:
    assert COMPATIBILITY_MATRIX == ()
