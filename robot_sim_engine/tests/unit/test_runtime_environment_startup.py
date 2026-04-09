from __future__ import annotations

from pathlib import Path

import pytest

from robot_sim.app import bootstrap as bootstrap_mod
from robot_sim.app.runtime_environment import StartupEnvironmentStatus, evaluate_startup_environment


class DummyRuntimePaths:
    def __init__(self, config_root: Path) -> None:
        self.config_root = config_root


class DummyReport:
    def __init__(self, errors: tuple[str, ...] = ()) -> None:
        self.errors = errors
        self.warnings = ()
        self.ok = not errors


class DummyContainer:
    def __init__(self, root: Path, runtime_paths) -> None:
        self.runtime_context: dict[str, object] = {}
        self.capability_matrix_service = type(
            'M', (), {'build_matrix': lambda self, **kwargs: type('A', (), {'as_dict': lambda self: {'solvers': [], 'planners': [], 'importers': []}})()}
        )()
        self.solver_registry = object()
        self.planner_registry = object()
        self.importer_registry = object()
        self.project_root = root
        self.runtime_paths = runtime_paths
        self.config_service = type('Cfg', (), {'describe_resolution': lambda self: {'profile': 'default'}})()
        self.runtime_feature_policy = type('P', (), {'as_dict': lambda self: {}})()


def test_evaluate_startup_environment_is_strict_by_default_for_gui_and_release(tmp_path: Path) -> None:
    (tmp_path / 'release_environment.yaml').write_text(
        """
release_environment:
  gui:
    platform_system: Linux
    os_id: ubuntu
    os_version_id: 22.04
    python_major: 3
    python_minor: 10
    pyside_min_version: 6.5
  release:
    platform_system: Linux
    os_id: ubuntu
    os_version_id: 22.04
    python_major: 3
    python_minor: 10
    requires_build: true
""".strip()
        + "\n",
        encoding='utf-8',
    )
    runtime_paths = DummyRuntimePaths(tmp_path)
    assert evaluate_startup_environment(runtime_paths, mode='gui').strict is True
    assert evaluate_startup_environment(runtime_paths, mode='release').strict is True
    assert evaluate_startup_environment(runtime_paths, mode='headless').strict is False


def test_bootstrap_rejects_bad_gui_environment_by_default(monkeypatch):
    root = Path('/tmp/fake-project')

    class DummyPaths:
        def __init__(self, root_path):
            self.project_root = root_path
            self.logging_config_path = root_path / 'runtime' / 'logging.yaml'
            self.config_root = root_path / 'runtime'
            self.export_root = root_path / 'exports'
            self.resource_root = root_path
            self.source_layout_available = False

    monkeypatch.setattr(bootstrap_mod, 'resolve_runtime_paths', lambda: DummyPaths(root))
    monkeypatch.setattr(bootstrap_mod, 'setup_logging', lambda path: None)
    monkeypatch.setattr(
        bootstrap_mod,
        'evaluate_startup_environment',
        lambda runtime_paths, mode='gui': StartupEnvironmentStatus(mode=mode, report=DummyReport(('gui missing',)), strict=True),
    )

    with pytest.raises(RuntimeError, match='GUI startup environment contract failed'):
        bootstrap_mod.bootstrap()


def test_bootstrap_allows_explicit_headless_startup(monkeypatch):
    root = Path('/tmp/fake-project')

    class DummyPaths:
        def __init__(self, root_path):
            self.project_root = root_path
            self.logging_config_path = root_path / 'runtime' / 'logging.yaml'
            self.config_root = root_path / 'runtime'
            self.export_root = root_path / 'exports'
            self.resource_root = root_path
            self.source_layout_available = False

    monkeypatch.setattr(bootstrap_mod, 'resolve_runtime_paths', lambda: DummyPaths(root))
    monkeypatch.setattr(bootstrap_mod, 'setup_logging', lambda path: None)
    monkeypatch.setattr(
        bootstrap_mod,
        'evaluate_startup_environment',
        lambda runtime_paths, mode='headless': StartupEnvironmentStatus(mode=mode, report=DummyReport(('gui missing',)), strict=False),
    )
    monkeypatch.setattr(bootstrap_mod, 'build_container', lambda runtime_paths: DummyContainer(root, runtime_paths))

    context = bootstrap_mod.bootstrap(startup_mode='headless')
    assert context.project_root == root
    assert context.container.runtime_context['startup_mode'] == 'headless'


def test_bootstrap_allows_explicit_release_startup(monkeypatch):
    root = Path('/tmp/fake-project')

    class DummyPaths:
        def __init__(self, root_path):
            self.project_root = root_path
            self.logging_config_path = root_path / 'runtime' / 'logging.yaml'
            self.config_root = root_path / 'runtime'
            self.export_root = root_path / 'exports'
            self.resource_root = root_path
            self.source_layout_available = False

    monkeypatch.setattr(bootstrap_mod, 'resolve_runtime_paths', lambda: DummyPaths(root))
    monkeypatch.setattr(bootstrap_mod, 'setup_logging', lambda path: None)
    monkeypatch.setattr(
        bootstrap_mod,
        'evaluate_startup_environment',
        lambda runtime_paths, mode='release': StartupEnvironmentStatus(mode=mode, report=DummyReport(()), strict=True),
    )
    monkeypatch.setattr(bootstrap_mod, 'build_container', lambda runtime_paths: DummyContainer(root, runtime_paths))

    context = bootstrap_mod.bootstrap(startup_mode='release')
    assert context.project_root == root
    assert context.container.runtime_context['startup_mode'] == 'release'
    assert context.container.runtime_context['startup_environment']['ok'] is True
