from __future__ import annotations

from robot_sim.presentation.coordinators._helpers import require_dependency, require_view, run_presented


class RobotCoordinator:
    """Own robot load/save orchestration for the main window."""

    def __init__(self, window, *, robot=None) -> None:
        self.window = window
        self.robot = require_dependency(robot, 'robot_workflow')

    def load_robot(self, name: str | None = None) -> None:
        """Public UI entrypoint for loading a robot into the scene."""
        self.load_robot_task(name=name)

    def import_robot(self) -> None:
        """Public UI entrypoint for importing an external robot into the canonical library."""
        self.import_robot_task()

    def load_robot_task(self, name: str | None = None) -> None:
        """Load a robot and project its initial state into the UI.

        Args:
            name: Optional robot identifier overriding the UI selection.

        Returns:
            None: Projects the loaded robot into the visible UI shell.

        Raises:
            Exception: Propagates robot-load failures through the presentation boundary.
        """
        def action() -> None:
            selected_name = name or require_view(self.window, 'read_selected_robot_name')
            fk = self.robot.load_robot(selected_name)
            require_view(self.window, 'project_robot_loaded', fk)

        run_presented(self.window, action, title='错误')

    def save_current_robot(self) -> None:
        """Save the current robot editor state back to disk."""
        def action() -> None:
            editor_state = require_view(self.window, 'read_robot_editor_state')
            path = self.robot.save_current_robot(
                rows=editor_state['rows'],
                home_q=editor_state['home_q'],
                name=editor_state['name'],
            )
            require_view(self.window, 'project_robot_saved', path)

        run_presented(self.window, action, title='错误')

    def import_robot_task(self) -> None:
        """Import a robot through the view boundary and project the persisted result.

        Returns:
            None: Updates the stable UI through boundary projection methods only.

        Raises:
            Exception: Propagates importer parsing, persistence, and runtime projection
                failures through the shared presentation error boundary.
        """
        def action() -> None:
            request = require_view(self.window, 'read_robot_import_request')
            if request is None:
                return
            source = str(request.get('source', '')).strip()
            if not source:
                return
            raw_importer = request.get('importer_id')
            importer_id = None if raw_importer in (None, '', 'auto') else str(raw_importer)
            result = self.robot.import_robot(source, importer_id=importer_id)
            require_view(self.window, 'project_robot_imported', result)

        run_presented(self.window, action, title='错误')
