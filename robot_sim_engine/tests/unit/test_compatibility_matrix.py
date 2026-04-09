from robot_sim.app.compatibility_matrix import COMPATIBILITY_MATRIX


def test_compatibility_matrix_tracks_expected_surfaces() -> None:
    surfaces = {entry.surface for entry in COMPATIBILITY_MATRIX}
    assert 'bootstrap iterable unpacking' in surfaces
    assert 'legacy config overrides' in surfaces
    assert 'main window private alias shim' in surfaces
    assert 'worker legacy lifecycle signals' in surfaces
