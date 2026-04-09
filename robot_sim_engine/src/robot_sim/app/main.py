from __future__ import annotations

import logging
import sys

from robot_sim.app.bootstrap import bootstrap

_LOG = logging.getLogger(__name__)
_EXIT_CODE_MISSING_GUI = 1
_EXIT_CODE_RUNTIME_RESOURCE = 2
_EXIT_CODE_STARTUP_FAILURE = 3


def _startup_failure_exit(exc: Exception) -> tuple[int, str]:
    """Map a startup failure to a stable process exit code and user message.

    Args:
        exc: Startup exception raised before the event loop enters steady state.

    Returns:
        tuple[int, str]: Stable ``(exit_code, user_message)`` pair.

    Raises:
        None: The helper only classifies already-raised exceptions.

    Boundary behavior:
        The mapping is intentionally coarse so bootstrap/configuration failures, GUI
        dependency failures, and unknown startup faults each retain a deterministic
        process exit surface for scripts and smoke tests.
    """
    message = str(exc)
    if isinstance(exc, ModuleNotFoundError) and 'PySide6' in message:
        return _EXIT_CODE_MISSING_GUI, 'PySide6 未安装。先安装 GUI 依赖后再运行界面。'
    if isinstance(exc, ImportError) and 'PySide6' in message:
        return _EXIT_CODE_MISSING_GUI, 'PySide6 未安装。先安装 GUI 依赖后再运行界面。'
    if isinstance(exc, FileNotFoundError):
        return _EXIT_CODE_RUNTIME_RESOURCE, f'运行时资源缺失，启动失败：{exc}'
    return _EXIT_CODE_STARTUP_FAILURE, f'应用启动失败：{exc}'


def _log_startup_failure(exc: Exception) -> None:
    """Log a startup failure through the process-entry defensive boundary.

    Args:
        exc: Startup exception raised by bootstrap, imports, or window construction.

    Returns:
        None: Emits a defensive exception log entry when logging is available.

    Raises:
        None: Logging failures are suppressed by the logging framework itself.
    """
    _LOG.exception('application startup failed', exc_info=exc)


def main() -> int:
    """Launch the Qt application shell.

    Returns:
        int: Process exit code.

    Raises:
        None: Startup errors are handled and converted into exit codes.
    """
    try:
        context = bootstrap(startup_mode='gui')
        from PySide6.QtWidgets import QApplication
        from robot_sim.presentation.main_window import MainWindow

        app = QApplication(sys.argv)
        window = MainWindow(context.project_root, container=context.container)
        window.show()
        return int(app.exec())
    except Exception as exc:
        _log_startup_failure(exc)
        exit_code, user_message = _startup_failure_exit(exc)
        print(user_message)
        if user_message != str(exc):
            print(exc)
        return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
