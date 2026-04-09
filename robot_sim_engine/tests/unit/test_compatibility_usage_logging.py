from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from robot_sim.app import bootstrap as bootstrap_mod
from robot_sim.infra.compatibility_usage import compatibility_usage_counts, reset_compatibility_usage_counts
from robot_sim.application.services.config_service import ConfigService
from robot_sim.application.workers.base import BaseWorker


def test_clean_bootstrap_uses_attribute_access_without_compatibility_usage(monkeypatch) -> None:
    reset_compatibility_usage_counts()

    class DummyPaths:
        def __init__(self):
            self.project_root = Path('/tmp/fake-project')
            self.logging_config_path = self.project_root / 'runtime' / 'logging.yaml'
            self.config_root = self.project_root / 'runtime'
            self.export_root = self.project_root / 'exports'
            self.resource_root = self.project_root
            self.source_layout_available = False

    monkeypatch.setattr(bootstrap_mod, 'resolve_runtime_paths', lambda: DummyPaths())
    monkeypatch.setattr(bootstrap_mod, 'setup_logging', lambda path: None)
    monkeypatch.setattr(bootstrap_mod, 'build_container', lambda runtime_paths: SimpleNamespace(
        capability_matrix_service=SimpleNamespace(build_matrix=lambda **kwargs: SimpleNamespace(as_dict=lambda: {'solvers': [], 'planners': [], 'importers': []})),
        solver_registry=object(),
        planner_registry=object(),
        importer_registry=object(),
        project_root=runtime_paths.project_root,
        runtime_paths=runtime_paths,
        runtime_context={},
        runtime_feature_policy=SimpleNamespace(as_dict=lambda: {}),
        config_service=SimpleNamespace(describe_resolution=lambda: {'profile': 'default'}),
    ))

    context = bootstrap_mod.bootstrap(startup_mode='headless')

    assert context.project_root == Path('/tmp/fake-project')
    assert context.container.project_root == Path('/tmp/fake-project')
    assert compatibility_usage_counts() == {}


def test_local_override_path_loads_without_legacy_usage(tmp_path: Path) -> None:
    reset_compatibility_usage_counts()
    local_dir = tmp_path / 'local'
    local_dir.mkdir(parents=True)
    (local_dir / 'app.local.yaml').write_text("""window:
  title: Local Title
""", encoding='utf-8')
    service = ConfigService(tmp_path, profile='default', local_override_dir=local_dir)

    config = service.load_app_config()

    assert config['window']['title'] == 'Local Title'
    assert compatibility_usage_counts() == {}


def test_base_worker_exposes_only_structured_terminal_signals() -> None:
    worker = BaseWorker()

    assert hasattr(worker, 'progress_event')
    assert hasattr(worker, 'finished_event')
    assert hasattr(worker, 'failed_event')
    assert hasattr(worker, 'cancelled_event')
    assert not hasattr(worker, 'progress')
    assert not hasattr(worker, 'finished')
    assert not hasattr(worker, 'failed')
    assert not hasattr(worker, 'cancelled')
