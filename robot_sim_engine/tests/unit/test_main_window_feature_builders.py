from __future__ import annotations

from test_main_window_mixins import DummyWindow


def test_main_window_exposes_feature_builder_bundle() -> None:
    window = DummyWindow()
    builders = window._feature_builders()

    assert 'layout' in builders
    assert 'signals' in builders
    assert builders['layout'].left_builder is not None
    assert builders['layout'].center_builder is not None
    assert builders['layout'].right_builder is not None
