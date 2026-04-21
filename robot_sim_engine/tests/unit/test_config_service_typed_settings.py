from __future__ import annotations

from robot_sim.application.services.config_service import ConfigService


def test_config_service_typed_settings_roundtrip(tmp_path):
    profiles = tmp_path / 'profiles'
    profiles.mkdir(parents=True)
    (profiles / 'default.yaml').write_text(
        """window:
  title: Demo
plots:
  max_points: 42
ik:
  mode: dls
trajectory:
  duration: 2.0
  dt: 0.05
  validation_layers:
    - timing
    - limits
""",
        encoding='utf-8',
    )
    service = ConfigService(tmp_path)

    app_settings = service.load_app_settings()
    solver_settings = service.load_solver_settings()

    assert app_settings.window.title == 'Demo'
    assert app_settings.plots.max_points == 42
    assert solver_settings.trajectory.duration == 2.0
    assert solver_settings.trajectory.validation_layers == ('timing', 'limits')
    assert solver_settings.as_dict()['trajectory']['validation_layers'] == ['timing', 'limits']
    assert solver_settings.as_dict()['ik']['mode'] == 'dls'


def test_config_service_typed_settings_include_render_advice_thresholds(tmp_path):
    profiles = tmp_path / 'profiles'
    profiles.mkdir(parents=True)
    (profiles / 'default.yaml').write_text(
        """window:\n  title: Demo\nrender:\n  advice:\n    high_p95_ms: 41.0\n    high_average_ms: 23.0\n    high_failure_ratio: 0.3\n    high_span_rate_per_sec: 11.0\nik:\n  mode: dls\ntrajectory:\n  duration: 2.0\n  dt: 0.05\n  validation_layers:\n    - timing\n    - limits\n""",
        encoding='utf-8',
    )
    service = ConfigService(tmp_path)
    app_settings = service.load_app_settings()
    assert app_settings.render.advice.high_p95_ms == 41.0
    assert app_settings.render.advice.high_average_ms == 23.0
    assert app_settings.render.advice.high_failure_ratio == 0.3
    assert app_settings.render.advice.high_span_rate_per_sec == 11.0
