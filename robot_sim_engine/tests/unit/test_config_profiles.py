from __future__ import annotations

import yaml

from robot_sim.application.services.config_service import ConfigService


def test_config_service_merges_default_and_named_profiles(tmp_path):
    profiles = tmp_path / 'profiles'
    profiles.mkdir(parents=True)
    (profiles / 'default.yaml').write_text(yaml.safe_dump({
        'window': {'width': 1111},
        'ik': {'retry_count': 2},
    }), encoding='utf-8')
    (profiles / 'ci.yaml').write_text(yaml.safe_dump({
        'window': {'title': 'CI Title'},
        'trajectory': {'dt': 0.05, 'validation_layers': ['timing', 'limits']},
    }), encoding='utf-8')
    service = ConfigService(tmp_path, profile='ci')

    app_cfg = service.load_app_config()
    solver_cfg = service.load_solver_config()

    assert app_cfg['window']['width'] == 1111
    assert app_cfg['window']['title'] == 'CI Title'
    assert solver_cfg['ik']['retry_count'] == 2
    assert solver_cfg['trajectory']['dt'] == 0.05
    assert solver_cfg['trajectory']['validation_layers'] == ['timing', 'limits']


def test_config_service_local_files_override_profiles_from_local_directory(tmp_path):
    profiles = tmp_path / 'profiles'
    profiles.mkdir(parents=True)
    local_dir = tmp_path / 'local'
    local_dir.mkdir(parents=True)
    (profiles / 'default.yaml').write_text(yaml.safe_dump({
        'window': {'height': 900},
        'trajectory': {'duration': 4.0},
    }), encoding='utf-8')
    (profiles / 'gui.yaml').write_text(yaml.safe_dump({
        'window': {'title': 'GUI'},
        'plots': {'max_points': 6000},
    }), encoding='utf-8')
    (local_dir / 'app.local.yaml').write_text(yaml.safe_dump({
        'window': {'title': 'LOCAL GUI'},
    }), encoding='utf-8')
    (local_dir / 'solver.local.yaml').write_text(yaml.safe_dump({
        'trajectory': {'duration': 5.0},
    }), encoding='utf-8')
    service = ConfigService(tmp_path, profile='gui', local_override_dir=local_dir)

    app_cfg = service.load_app_config()
    solver_cfg = service.load_solver_config()

    assert app_cfg['window']['title'] == 'LOCAL GUI'
    assert app_cfg['window']['height'] == 900
    assert app_cfg['plots']['max_points'] == 6000
    assert solver_cfg['trajectory']['duration'] == 5.0


def test_shipped_repository_profiles_remain_observably_different(project_root):
    observed = {}
    for profile in ('default', 'dev', 'ci', 'research'):
        service = ConfigService(project_root / 'configs', profile=profile)
        app_cfg = service.load_app_config()
        solver_cfg = service.load_solver_config()
        observed[profile] = (
            app_cfg['window']['title'],
            app_cfg['plots']['max_points'],
            solver_cfg['ik']['retry_count'],
            solver_cfg['trajectory']['dt'],
        )

    assert observed['default'] == ('Robot Sim Engine', 5000, 1, 0.02)
    assert observed['dev'] == ('Robot Sim Engine [dev]', 7000, 2, 0.02)
    assert observed['ci'] == ('Robot Sim Engine [ci]', 2500, 1, 0.05)
    assert observed['research'] == ('Robot Sim Engine [research]', 8000, 3, 0.01)


def test_config_service_reports_available_profiles(tmp_path):
    profiles = tmp_path / 'profiles'
    profiles.mkdir(parents=True)
    (profiles / 'default.yaml').write_text('{}', encoding='utf-8')
    (profiles / 'release.yaml').write_text('{}', encoding='utf-8')
    service = ConfigService(tmp_path)
    assert service.available_profiles() == ('default', 'release')
