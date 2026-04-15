from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
import traceback
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / 'src'
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from robot_sim.infra.qt_runtime import configure_qt_platform_for_pytest  # noqa: E402
from robot_sim.testing.qt_shims import install_pyside6_test_shims, real_pyside6_available  # noqa: E402


def _run_gui_smoke(*, allow_test_shims: bool = True) -> dict[str, object]:
    """Execute a deterministic GUI smoke path.

    Args:
        allow_test_shims: Whether the repository-local Qt shim may be installed when
            a real ``PySide6`` runtime is unavailable.

    Returns:
        dict[str, object]: Structured smoke evidence including runtime kind, real/shim
            availability classification, Qt platform, and the rendered scene snapshot keys.

    Raises:
        RuntimeError: If the stable GUI construction path cannot be exercised or if a
            real ``PySide6`` runtime is required but unavailable.

    Boundary behavior:
        The verification path prefers a real ``PySide6`` runtime. When unavailable and
        ``allow_test_shims`` is true, the script installs the repository-local Qt test
        shims in-process so offscreen GUI smoke remains executable in constrained CI or
        sandbox environments. The returned payload always distinguishes real-runtime
        success from shim-runtime success so release review cannot confuse the two.
    """
    configure_qt_platform_for_pytest(os.environ)
    real_runtime_available = bool(real_pyside6_available())
    using_test_shims = False
    if not real_runtime_available:
        if not allow_test_shims:
            raise RuntimeError('PySide6 is unavailable and test shims are disabled')
        using_test_shims = bool(install_pyside6_test_shims())

    from PySide6.QtWidgets import QApplication
    from robot_sim.app.bootstrap import get_project_root
    from robot_sim.app.container import build_container
    from robot_sim.presentation.main_window import MainWindow
    from robot_sim.render.scene_3d_widget import Scene3DWidget
    from robot_sim.render.screenshot_service import ScreenshotService

    app = QApplication.instance() or QApplication([])
    root = get_project_root()
    window = MainWindow(root, container=build_container(root))
    try:
        if window.controller is None:
            raise RuntimeError('MainWindow controller is unavailable')
        if window.metrics_service is not window.controller.metrics_service:
            raise RuntimeError('MainWindow metrics service drifted from controller metrics service')
        widget = Scene3DWidget()
        snapshot = widget.scene_snapshot()
        if 'overlay_text' not in snapshot:
            raise RuntimeError('Scene3DWidget snapshot is missing overlay_text')
        service = ScreenshotService()
        with tempfile.TemporaryDirectory() as tmp_dir:
            output_path = Path(tmp_dir) / 'gui_smoke_snapshot.png'
            service.capture_from_snapshot(snapshot, output_path)
            if not output_path.exists() or output_path.stat().st_size <= 0:
                raise RuntimeError('ScreenshotService failed to persist a GUI smoke snapshot')
        runtime_kind = 'test_shim' if using_test_shims else 'real_pyside6'
        return {
            'runtime_kind': runtime_kind,
            'real_runtime_ok': bool(real_runtime_available and not using_test_shims),
            'shim_runtime_ok': bool(using_test_shims),
            'qt_platform': str(os.environ.get('QT_QPA_PLATFORM', '') or ''),
            'snapshot_keys': sorted(str(key) for key in snapshot.keys()),
        }
    finally:
        window.close()
        app.processEvents() if hasattr(app, 'processEvents') else None


def main() -> int:
    parser = argparse.ArgumentParser(
        description='Verify the stable GUI smoke path using real PySide6 when available and a controlled in-process Qt test shim otherwise.'
    )
    parser.add_argument(
        '--no-test-shims',
        action='store_true',
        help='Require a real PySide6 runtime instead of falling back to the repository-local Qt test shims.',
    )
    parser.add_argument('--json-out', type=Path, default=None, help='Optional JSON path used to persist structured GUI smoke evidence.')
    args = parser.parse_args()
    try:
        details = _run_gui_smoke(allow_test_shims=not bool(args.no_test_shims))
    except Exception as exc:  # pragma: no cover - CLI path
        print(f'ERROR: gui smoke failed: {exc}')
        traceback.print_exc()
        return 1
    if args.json_out is not None:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(json.dumps(details, indent=2, sort_keys=True), encoding='utf-8')
    print('gui smoke verified')
    print(f"runtime_kind={details['runtime_kind']}")
    print(f"real_runtime_ok={str(bool(details['real_runtime_ok'])).lower()}")
    print(f"shim_runtime_ok={str(bool(details['shim_runtime_ok'])).lower()}")
    print(f"qt_platform={details['qt_platform']}")
    print('snapshot_keys=' + ','.join(str(item) for item in details['snapshot_keys']))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
