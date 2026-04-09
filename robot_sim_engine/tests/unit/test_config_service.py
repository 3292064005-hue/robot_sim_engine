from __future__ import annotations

from robot_sim.application.services.config_service import ConfigService


<<<<<<< HEAD
def test_config_service_loads_defaults_and_merges_local_overrides(tmp_path):
    local_dir = tmp_path / 'local'
    local_dir.mkdir(parents=True)
    (local_dir / 'app.local.yaml').write_text(
        """window:
  title: Custom Title
  width: 1234
plots:
  max_points: 42
""",
        encoding='utf-8',
    )
    (local_dir / 'solver.local.yaml').write_text(
        """ik:
  mode: pinv
  retry_count: 3
trajectory:
  dt: 0.05
  validation_layers:
    - timing
    - limits
""",
        encoding='utf-8',
    )
    service = ConfigService(tmp_path, local_override_dir=local_dir)
=======
def test_config_service_loads_defaults_and_merges_overrides(tmp_path):
    (tmp_path / 'app.yaml').write_text(
        'window:\n  title: Custom Title\n  width: 1234\nplots:\n  max_points: 42\n',
        encoding='utf-8',
    )
    (tmp_path / 'solver.yaml').write_text(
        'ik:\n  mode: pinv\n  retry_count: 3\ntrajectory:\n  dt: 0.05\n',
        encoding='utf-8',
    )
    service = ConfigService(tmp_path)
>>>>>>> 3ed78e647985c6d680c085e4480d898855278db3
    app_cfg = service.load_app_config()
    solver_cfg = service.load_solver_config()
    assert app_cfg['window']['title'] == 'Custom Title'
    assert app_cfg['window']['height'] == 980
    assert app_cfg['plots']['max_points'] == 42
    assert solver_cfg['ik']['mode'] == 'pinv'
    assert solver_cfg['ik']['retry_count'] == 3
    assert solver_cfg['ik']['reachability_precheck'] is True
    assert solver_cfg['trajectory']['duration'] == 3.0
    assert solver_cfg['trajectory']['dt'] == 0.05
<<<<<<< HEAD
    assert solver_cfg['trajectory']['validation_layers'] == ['timing', 'limits']


def test_config_service_ignores_retired_repository_level_overrides(tmp_path):
    (tmp_path / 'app.yaml').write_text(
        """window:
  title: Legacy Title
""",
        encoding='utf-8',
    )
    (tmp_path / 'solver.yaml').write_text(
        """trajectory:
  dt: 0.08
""",
        encoding='utf-8',
    )
    service = ConfigService(tmp_path, allow_legacy_local_override=True)
    app_cfg = service.load_app_config()
    solver_cfg = service.load_solver_config()
    assert app_cfg['window']['title'] == 'Robot Sim Engine'
    assert solver_cfg['trajectory']['dt'] == 0.02


def test_config_service_resolution_summary_does_not_duplicate_default_profile(tmp_path):
    service = ConfigService(tmp_path)
    resolution = service.describe_resolution()
    assert resolution['active_profile'] == 'default'
    assert tuple(resolution['resolution_order']).count('profiles/default.yaml') == 1
=======
>>>>>>> 3ed78e647985c6d680c085e4480d898855278db3
