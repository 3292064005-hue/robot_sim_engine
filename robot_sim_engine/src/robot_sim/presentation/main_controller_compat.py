from __future__ import annotations

from collections.abc import Callable
import inspect
from typing import Any

from robot_sim.application.export_artifacts import DEFAULT_EXPORT_ARTIFACTS

_COMPATIBILITY_METHOD_BINDINGS: dict[str, tuple[str, str]] = {
    'robot_names': ('robot_workflow', 'robot_names'),
    'robot_entries': ('robot_workflow', 'robot_entries'),
    'importer_entries': ('robot_workflow', 'importer_entries'),
    'available_specs': ('robot_workflow', 'available_specs'),
    'solver_defaults': ('motion_workflow', 'solver_defaults'),
    'trajectory_defaults': ('motion_workflow', 'trajectory_defaults'),
    'import_robot': ('robot_workflow', 'import_robot'),
    'load_robot': ('robot_workflow', 'load_robot'),
    'build_robot_from_editor': ('robot_workflow', 'build_robot_from_editor'),
    'save_current_robot': ('robot_workflow', 'save_current_robot'),
    'run_fk': ('robot_workflow', 'run_fk'),
    'sample_ee_positions': ('robot_workflow', 'sample_ee_positions'),
    'build_target_pose': ('motion_workflow', 'build_target_pose'),
    'build_ik_request': ('motion_workflow', 'build_ik_request'),
    'apply_ik_result': ('motion_workflow', 'apply_ik_result'),
    'run_ik': ('motion_workflow', 'run_ik'),
    'build_benchmark_config': ('motion_workflow', 'build_benchmark_config'),
    'run_benchmark': ('motion_workflow', 'run_benchmark'),
    'trajectory_goal_or_raise': ('motion_workflow', 'trajectory_goal_or_raise'),
    'build_trajectory_request': ('motion_workflow', 'build_trajectory_request'),
    'plan_trajectory': ('motion_workflow', 'plan_trajectory'),
    'apply_trajectory': ('motion_workflow', 'apply_trajectory'),
    'current_playback_frame': ('motion_workflow', 'current_playback_frame'),
    'set_playback_frame': ('motion_workflow', 'set_playback_frame'),
    'next_playback_frame': ('motion_workflow', 'next_playback_frame'),
    'set_playback_options': ('motion_workflow', 'set_playback_options'),
    'export_trajectory_bundle': ('export_workflow', 'export_trajectory_bundle'),
    'export_trajectory': ('export_workflow', 'export_trajectory'),
    'export_trajectory_metrics': ('export_workflow', 'export_trajectory_metrics'),
    'export_benchmark': ('export_workflow', 'export_benchmark'),
    'export_benchmark_cases_csv': ('export_workflow', 'export_benchmark_cases_csv'),
    'export_session': ('export_workflow', 'export_session'),
    'export_package': ('export_workflow', 'export_package'),
}

_COMPATIBILITY_DEFAULTS: dict[str, dict[str, object]] = {
    'export_trajectory_bundle': {'name': DEFAULT_EXPORT_ARTIFACTS.trajectory_bundle_name},
    'export_trajectory': {'name': DEFAULT_EXPORT_ARTIFACTS.trajectory_bundle_name},
    'export_trajectory_metrics': {
        'name': DEFAULT_EXPORT_ARTIFACTS.trajectory_metrics_name,
        'metrics': None,
    },
    'export_benchmark': {'name': DEFAULT_EXPORT_ARTIFACTS.benchmark_report_name},
    'export_benchmark_cases_csv': {'name': DEFAULT_EXPORT_ARTIFACTS.benchmark_cases_name},
    'export_session': {'name': DEFAULT_EXPORT_ARTIFACTS.session_name, 'telemetry_detail': 'full'},
    'export_package': {'name': DEFAULT_EXPORT_ARTIFACTS.package_name, 'telemetry_detail': 'minimal'},
}


def compatibility_method_names() -> tuple[str, ...]:
    """Return the stable compatibility method names still exposed by MainController."""
    return tuple(_COMPATIBILITY_METHOD_BINDINGS)


def build_compatibility_method(controller: Any, name: str) -> Callable[..., Any]:
    """Build a bound compatibility method that delegates to the canonical workflow surface.

    Args:
        controller: ``MainController`` instance exposing canonical workflow collaborators.
        name: Historical compatibility method name.

    Returns:
        Callable[..., Any]: Bound method proxy that delegates to the configured workflow.

    Raises:
        AttributeError: If ``name`` is not a supported compatibility method.
    """
    if name not in _COMPATIBILITY_METHOD_BINDINGS:
        raise AttributeError(name)
    workflow_attr, method_name = _COMPATIBILITY_METHOD_BINDINGS[name]
    target = getattr(getattr(controller, workflow_attr), method_name)
    defaults = dict(_COMPATIBILITY_DEFAULTS.get(name, {}))

    signature = inspect.signature(target)

    def _method(*args, **kwargs):
        bound = signature.bind_partial(*args, **kwargs)
        payload = dict(kwargs)
        for key, value in defaults.items():
            if key not in bound.arguments:
                payload[key] = value
        return target(*args, **payload)

    _method.__name__ = name
    _method.__qualname__ = f'{controller.__class__.__name__}.{name}'
    _method.__doc__ = (
        f'Compatibility delegate for ``{name}`` that forwards to '
        f'``{workflow_attr}.{method_name}`` on the canonical workflow surface.'
    )
    return _method
