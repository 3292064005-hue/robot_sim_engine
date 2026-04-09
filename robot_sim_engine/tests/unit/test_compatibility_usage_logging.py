from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from robot_sim.app import bootstrap as bootstrap_mod
from robot_sim.infra.compatibility_usage import compatibility_usage_counts, reset_compatibility_usage_counts
from robot_sim.application.services.config_service import ConfigService
from robot_sim.application.workers.base import BaseWorker
from robot_sim.presentation.legacy_aliases import MainWindowLegacyAliasMixin


def test_bootstrap_records_iterable_unpacking_compatibility_usage(monkeypatch) -> None:
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
        config_service=SimpleNamespace(describe_resolution=lambda: {'profile': 'default'}),
    ))

    context = bootstrap_mod.bootstrap(startup_mode='headless')
    root, container = context

    assert root == Path('/tmp/fake-project')
    assert container.project_root == Path('/tmp/fake-project')
    counts = compatibility_usage_counts()
    assert counts['bootstrap iterable unpacking'] == 1


def test_legacy_config_override_records_usage(tmp_path: Path) -> None:
    reset_compatibility_usage_counts()
    (tmp_path / 'app.yaml').write_text("window:\n  title: Legacy Title\n", encoding='utf-8')
    service = ConfigService(tmp_path, profile='default', allow_legacy_local_override=True)

    config = service.load_app_config()

    assert config['window']['title'] == 'Legacy Title'
    counts = compatibility_usage_counts()
    assert counts['legacy config overrides'] == 1


def test_main_window_legacy_alias_records_usage() -> None:
    reset_compatibility_usage_counts()

    class DummyWindow(MainWindowLegacyAliasMixin):
        def on_load_robot(self):
            return 'loaded'

    window = DummyWindow()
    assert window._load_robot_impl() == 'loaded'
    counts = compatibility_usage_counts()
    assert counts['main window private alias shim'] == 1


def test_worker_legacy_signal_adapter_records_usage() -> None:
    reset_compatibility_usage_counts()
    worker = BaseWorker()

    worker.emit_progress(stage='frame', percent=10.0, payload={'value': 1})
    worker.emit_finished({'ok': True})
    worker.emit_failed('boom')
    worker.emit_cancelled()

    counts = compatibility_usage_counts()
    assert counts['worker legacy lifecycle signals'] == 4
