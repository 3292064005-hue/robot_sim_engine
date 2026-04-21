from __future__ import annotations

from pathlib import Path
import tempfile

from robot_sim.app.bootstrap import bootstrap
from robot_sim.presentation.controllers.robot_controller import RobotController
from robot_sim.presentation.state_store import StateStore


_SAMPLE_YAML = """\
id: smoke_robot
name: Smoke Robot
dh_rows:
  - a: 0.25
    alpha: 0.0
    d: 0.0
    theta_offset: 0.0
    joint_type: revolute
    q_min: -3.141592653589793
    q_max: 3.141592653589793
home_q: [0.0]
"""


def run_installed_runtime_smoke() -> dict[str, str]:
    """Exercise installed-wheel robot-library read/write behavior.

    Returns:
        dict[str, str]: Summary of the runtime roots and files touched during the smoke test.

    Raises:
        RuntimeError: If the installed runtime cannot expose a bundled default robot.
        AssertionError: If import/save paths do not land in the writable robot overlay.

    Boundary behavior:
        The smoke test intentionally uses the public bootstrap/container surface plus the
        presentation-level ``RobotController`` to verify the same installed-wheel write path
        used by the stable import/save workflow. Temporary source files are cleaned up by the
        surrounding temporary directory context manager.
    """
    context = bootstrap(startup_mode='headless')
    project_root = context.project_root
    container = context.container
    bootstrap_bundle = container.bootstrap_bundle
    controller = RobotController(
        StateStore(),
        bootstrap_bundle.registries.robot_registry,
        bootstrap_bundle.workflows.fk_uc,
        import_robot_uc=bootstrap_bundle.workflows.import_robot_uc,
        application_workflow=bootstrap_bundle.workflow_facade,
    )

    available_names = bootstrap_bundle.registries.robot_registry.list_names()
    if 'planar_2dof' not in available_names:
        raise RuntimeError('installed runtime smoke requires bundled robot planar_2dof')

    writable_root = Path(bootstrap_bundle.services.runtime_paths.robot_root).resolve()
    bundled_root = Path(bootstrap_bundle.services.runtime_paths.bundled_robot_root).resolve()
    assert writable_root.exists(), 'writable robot root must exist'

    with tempfile.TemporaryDirectory(prefix='robot-smoke-') as tmpdir:
        source_path = Path(tmpdir) / 'smoke_robot.yaml'
        source_path.write_text(_SAMPLE_YAML, encoding='utf-8')
        result = controller.import_robot(str(source_path), importer_id='yaml')
        saved_copy = controller.save_current_robot(name='smoke_saved_robot')

    imported_path = result.persisted_path.resolve()
    saved_copy = Path(saved_copy).resolve()
    assert imported_path.parent == writable_root, 'imported robot must persist into writable overlay'
    assert saved_copy.parent == writable_root, 'saved robot must persist into writable overlay'
    assert bundled_root != writable_root, 'installed runtime should keep bundled robots read-only'

    return {
        'project_root': str(project_root),
        'writable_robot_root': str(writable_root),
        'bundled_robot_root': str(bundled_root),
        'imported_robot_path': str(imported_path),
        'saved_robot_path': str(saved_copy),
    }


def main() -> int:
    summary = run_installed_runtime_smoke()
    for key, value in summary.items():
        print(f'{key}={value}')
    return 0


if __name__ == '__main__':  # pragma: no cover
    raise SystemExit(main())
