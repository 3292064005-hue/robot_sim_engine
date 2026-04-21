from __future__ import annotations

from typing import TYPE_CHECKING

from robot_sim.presentation.scene_ui_support import build_default_scene_obstacle_request
from robot_sim.presentation.state_events import WarningProjectedEvent
from robot_sim.presentation.widgets.scene_editor_dialog import SceneEditorDialog

if TYPE_CHECKING:  # pragma: no cover
    from robot_sim.presentation.view_contracts import MainWindowUIContract


class MainWindowSceneUIMixin:
    """Stable planning-scene projection helpers split out of the main UI shell."""

    def project_scene_fit(self: 'MainWindowUIContract') -> None:
        """Project a scene-fit action into the UI."""
        self.scene_widget.fit_camera()
        self.status_panel.append('3D 视图已适配到当前场景')

    def project_scene_path_cleared(self: 'MainWindowUIContract') -> None:
        """Project a cleared transient scene path into the UI."""
        self.scene_controller.clear_transient_visuals()
        self.scene_widget.clear_trajectory()
        self.status_panel.append('末端轨迹显示已清空')

    def read_scene_obstacle_request(self: 'MainWindowUIContract') -> dict[str, object] | None:
        """Read one stable scene-editor request from the structured dialog flow.

        Returns:
            Optional mapping carrying obstacle geometry, replace policy, and ACM pairs.

        Raises:
            ValueError: If the editor payload is malformed.

        Boundary behavior:
            Cancellation returns ``None`` without mutating runtime state so toolbar actions
            stay side-effect free unless the user explicitly submits a valid scene edit.
        """
        runtime = self._runtime_ops()
        initial = build_default_scene_obstacle_request(runtime.state)
        return SceneEditorDialog.get_request(initial=initial, parent=self)

    def project_scene_obstacles_updated(self: 'MainWindowUIContract', scene) -> None:
        """Project planning-scene mutations into the live UI shell."""
        runtime = self._runtime_ops()
        self.scene_controller.update_planning_scene_projection(scene)
        runtime.state_store.dispatch(WarningProjectedEvent(message=''))
        scene_summary = dict(getattr(runtime.state, 'scene_summary', {}) or {})
        self.status_panel.append(
            '场景已更新：'
            f"authority={scene_summary.get('scene_authority', getattr(scene, 'scene_authority', 'planning_scene'))} "
            f"obstacles={scene_summary.get('obstacle_count', len(getattr(scene, 'obstacles', ())))} "
            f"pairs={scene_summary.get('collision_filter_pair_count', len(getattr(scene, 'allowed_collision_pairs', ()) or ())) } "
            f"revision={scene_summary.get('revision', getattr(scene, 'revision', 0))}"
        )

    def build_scene_capture_request(self: 'MainWindowUIContract', path) -> dict[str, object]:
        """Build a UI-thread-safe scene capture payload for background export.

        Args:
            path: Destination path selected by the scene coordinator.

        Returns:
            dict[str, object]: Snapshot payload containing the target path and scene snapshot.

        Raises:
            AttributeError: If the scene widget does not expose a snapshot contract.
        """
        return {'path': path, 'snapshot': self.scene_widget.scene_snapshot()}

    def project_scene_capture(self: 'MainWindowUIContract', result) -> None:
        """Project a saved scene capture into the status panel."""
        self.status_panel.append(f'场景截图已导出：{result}')
