from __future__ import annotations

import numpy as np

from robot_sim.domain.errors import RenderBackendUnavailableError, RenderInitializationError, RenderOperationError
from robot_sim.model.render_runtime import RenderCapabilityState
from robot_sim.render.actor_manager import ActorManager
from robot_sim.render.robot_visual import RobotVisual
from robot_sim.render.screenshot_service import ScreenshotService
from robot_sim.render.target_visual import TargetVisual
from robot_sim.render.trajectory_visual import TrajectoryVisual

from robot_sim.presentation.qt_runtime import QApplication, QLabel, QVBoxLayout, QWidget, require_qt_runtime


class Scene3DWidget(QWidget):  # pragma: no cover - GUI shell
    def __init__(self, parent=None):
        require_qt_runtime('Scene3DWidget')
        super().__init__(parent)
        self.plotter = None
        self.actor_manager = ActorManager()
        self.screenshot_service = ScreenshotService()
        self.robot_visual = RobotVisual()
        self.target_visual = TargetVisual()
        self.trajectory_visual = TrajectoryVisual()
        self._robot_points: np.ndarray | None = None
        self._trajectory_points: np.ndarray | None = None
        self._playback_marker: np.ndarray | None = None
        self._target_pose = None
        self._target_axes_visible = True
        self._trajectory_visible = True
        self._scene_title = 'Robot Sim Engine'
        self._robot_geometry = None
        self._scene_obstacles: list[object] = []
        self._attached_objects: list[object] = []
        self._overlay_text = self._scene_title
        self._robot_actor_names: set[str] = set()
        self._scene_actor_names: set[str] = set()
        self._scene_runtime = RenderCapabilityState(
            capability='scene_3d',
            status='degraded',
            backend='pyvistaqt',
            reason='scene_backend_pending',
            error_code='',
            message='3D scene backend has not been initialized yet.',
            level='placeholder_view',
            provenance={'render_path': 'placeholder_shell', 'provider': 'scene_3d_widget'},
        )
        self._screenshot_runtime = RenderCapabilityState(
            capability='screenshot',
            status='degraded',
            backend='snapshot_renderer',
            reason='snapshot_renderer_active',
            message='Scene screenshots will use the snapshot rasterizer until a live plotter is available.',
            level='snapshot_capture',
            provenance={'capture_source': 'scene_snapshot', 'render_path': 'snapshot_renderer', 'provider': 'scene_3d_widget'},
        )
        self._initialize_plotter_shell()

    def _initialize_plotter_shell(self) -> None:
        layout = QVBoxLayout(self)
        qt_platform = self._qt_platform_name()
        if qt_platform in {'offscreen', 'minimal'}:
            self._scene_runtime = RenderCapabilityState(
                capability='scene_3d',
                status='degraded',
                backend='pyvistaqt',
                reason='qt_platform_snapshot_only',
                message=(
                    'The Qt platform is running without a live window surface; '
                    'the scene uses snapshot-only rendering.'
                ),
                level='snapshot_only',
                metadata={'qt_platform': qt_platform},
                provenance={'render_path': 'snapshot_only', 'provider': 'scene_3d_widget', 'qt_platform': qt_platform},
            )
            self._screenshot_runtime = RenderCapabilityState(
                capability='screenshot',
                status='degraded',
                backend='snapshot_renderer',
                reason='snapshot_renderer_active',
                message='Scene screenshots are running through the snapshot fallback renderer.',
                level='snapshot_capture',
                metadata={'qt_platform': qt_platform},
                provenance={
                    'capture_source': 'scene_snapshot',
                    'render_path': 'snapshot_renderer',
                    'provider': 'scene_3d_widget',
                },
            )
            self._install_placeholder(
                layout,
                RenderInitializationError(
                    '3D backend is disabled for the current Qt platform',
                    metadata={'qt_platform': qt_platform},
                ),
            )
            return
        try:
            from pyvistaqt import QtInteractor
        except ImportError as exc:
            self._scene_runtime = RenderCapabilityState(
                capability='scene_3d',
                status='unsupported',
                backend='pyvistaqt',
                reason='backend_dependency_missing',
                error_code=RenderBackendUnavailableError.default_error_code,
                message='3D backend dependency is unavailable; the scene remains on a placeholder view.',
                level='placeholder_view',
                metadata={'exception_type': exc.__class__.__name__},
                provenance={'render_path': 'placeholder_view', 'provider': 'scene_3d_widget', 'exception_type': exc.__class__.__name__},
            )
            self._install_placeholder(
                layout,
                RenderBackendUnavailableError(
                    '3D backend is unavailable',
                    metadata={'exception_type': exc.__class__.__name__},
                ),
            )
            return
        try:
            self.plotter = QtInteractor(self)
            layout.addWidget(self.plotter.interactor)
            self.plotter.set_background('white')
            self.plotter.add_axes()
            self._set_plotter_overlay_text(self._overlay_text)
            self._scene_runtime = RenderCapabilityState.available_state(
                'scene_3d',
                backend='pyvistaqt',
                reason='live_plotter_active',
                message='3D scene backend is active.',
                level='live_3d',
                provenance={'render_path': 'live_plotter', 'provider': 'pyvistaqt'},
            )
            self._screenshot_runtime = RenderCapabilityState.available_state(
                'screenshot',
                backend='live_plotter',
                reason='live_plotter_capture',
                message='Scene screenshots are captured from the live plotter backend.',
                level='live_capture',
                provenance={'capture_source': 'live_plotter_framebuffer', 'render_path': 'live_plotter', 'provider': 'pyvistaqt'},
            )
        except (AttributeError, RuntimeError, TypeError, ValueError, OSError) as exc:
            self.plotter = None
            self._scene_runtime = RenderCapabilityState(capability='scene_3d', status='degraded', backend='pyvistaqt', reason='backend_initialization_failed', error_code=RenderInitializationError.default_error_code, message='3D backend initialization failed; the scene remains on a placeholder view.', level='placeholder_view', metadata={'exception_type': exc.__class__.__name__, 'message': str(exc)}, provenance={'render_path': 'placeholder_view', 'provider': 'scene_3d_widget', 'exception_type': exc.__class__.__name__})
            self._screenshot_runtime = RenderCapabilityState(capability='screenshot', status='degraded', backend='snapshot_renderer', reason='snapshot_renderer_fallback', message='Scene screenshots are running through the snapshot fallback renderer.', level='snapshot_capture', metadata={'exception_type': exc.__class__.__name__}, provenance={'capture_source': 'scene_snapshot', 'render_path': 'snapshot_renderer', 'provider': 'scene_3d_widget', 'exception_type': exc.__class__.__name__})
            self._install_placeholder(
                layout,
                RenderInitializationError(
                    '3D backend initialization failed',
                    metadata={'exception_type': exc.__class__.__name__, 'message': str(exc)},
                ),
            )

    @staticmethod
    def _qt_platform_name() -> str:
        app = QApplication.instance()
        if app is not None and hasattr(app, 'platformName'):
            return str(app.platformName() or '').strip().lower()
        return ''

    @staticmethod
    def _install_placeholder(layout, exc: RenderBackendUnavailableError | RenderInitializationError) -> None:
        label = QLabel(
            '3D 视图依赖未安装或初始化失败，当前为占位视图。\n'
            '请在项目目录执行: pip install -e .[gui]\n'
            f'详细信息: {exc.__class__.__name__}: {exc}'
        )
        label.setWordWrap(True)
        layout.addWidget(label)

    def _set_plotter_overlay_text(self, text: str) -> None:
        if self.plotter is None:
            return
        self.actor_manager.remove(self.plotter, 'scene_overlay')
        try:
            actor = self.plotter.add_text(text, font_size=10, name='scene_overlay')
        except TypeError:
            actor = self.plotter.add_text(text, font_size=10)
        except (AttributeError, RuntimeError, ValueError) as exc:
            raise RenderOperationError(
                'failed to update scene overlay text',
                metadata={'exception_type': exc.__class__.__name__, 'message': str(exc)},
            ) from exc
        self.actor_manager.set('scene_overlay', actor)

    def _update_mesh(self, name: str, mesh, **kwargs) -> None:
        if self.plotter is None:
            return
        actor = self.actor_manager.get(name)
        if actor is None:
            actor = self.plotter.add_mesh(mesh, **kwargs)
            self.actor_manager.set(name, actor)
        else:
            mapper = actor.GetMapper()
            if mapper is not None:
                mapper.SetInputData(mesh)

    def _remove_mesh(self, name: str) -> None:
        self.actor_manager.remove(self.plotter, name)

    def _render(self) -> None:
        if self.plotter is None:
            return
        self.plotter.reset_camera_clipping_range()
        self.plotter.render()

    def set_robot_geometry(self, robot_geometry) -> None:
        """Store runtime geometry and refresh the live robot projection when possible.

        Args:
            robot_geometry: Runtime visual geometry bundle or ``None``.

        Returns:
            None: Updates in-memory geometry and refreshes live actors when supported.

        Raises:
            None: Geometry updates degrade silently to skeleton-only rendering when the
                live plotter backend is unavailable.
        """
        self._robot_geometry = robot_geometry
        if self._robot_points is not None:
            self._render_robot()

    def set_scene_obstacles(self, obstacles) -> None:
        """Store planning-scene obstacles and refresh the live scene overlay."""
        self._scene_obstacles = list(obstacles or [])
        self._render_scene_objects()

    def set_attached_objects(self, attached_objects) -> None:
        """Store attached collision objects and refresh the live scene overlay."""
        self._attached_objects = list(attached_objects or [])
        self._render_scene_objects()

    def set_overlay_text(self, text: str) -> None:
        self._overlay_text = str(text)
        self._set_plotter_overlay_text(self._overlay_text)
        self._render()

    def set_robot_lines(self, points: np.ndarray) -> None:
        """Project FK skeleton points and, when available, runtime geometry meshes.

        Args:
            points: FK joint positions with shape ``(N, 3)``.

        Returns:
            None: Updates cached points and the live plotter scene.

        Raises:
            None: Rendering degrades silently when the live plotter backend is unavailable.
        """
        pts = np.asarray(points, dtype=float)
        self._robot_points = pts.copy()
        self._render_robot()


    def _render_robot(self) -> None:
        if self._robot_points is None or self.plotter is None or len(self._robot_points) < 2:
            return
        payload = self.robot_visual.build(self._robot_points, robot_geometry=self._robot_geometry)
        active_names = set(payload)
        for stale_name in tuple(self._robot_actor_names - active_names):
            self._remove_mesh(stale_name)
        for name, (mesh, kwargs) in payload.items():
            self._update_mesh(name, mesh, **kwargs)
        self._robot_actor_names = active_names
        self._render()

    def _render_scene_objects(self) -> None:
        if self.plotter is None:
            return
        import pyvista as pv

        payload: dict[str, object] = {}
        for prefix, objects in (('scene_obstacle', self._scene_obstacles), ('scene_attached', self._attached_objects)):
            for idx, obj in enumerate(objects):
                geometry = getattr(obj, 'geometry', None)
                metadata = dict(getattr(obj, 'metadata', {}) or {})
                if geometry is None:
                    continue
                try:
                    minimum = np.asarray(getattr(geometry, 'minimum', None), dtype=float)
                    maximum = np.asarray(getattr(geometry, 'maximum', None), dtype=float)
                except (TypeError, ValueError):
                    continue
                if minimum.shape != (3,) or maximum.shape != (3,):
                    continue
                lengths = np.maximum(maximum - minimum, 1.0e-6)
                center = (minimum + maximum) * 0.5
                shape = str(metadata.get('shape', 'box') or 'box').strip().lower()
                if shape == 'sphere':
                    payload[f'{prefix}_{idx}'] = pv.Sphere(radius=float(max(lengths) * 0.5), center=center)
                elif shape == 'cylinder':
                    payload[f'{prefix}_{idx}'] = pv.Cylinder(
                        center=center,
                        direction=(0.0, 0.0, 1.0),
                        radius=float(max(lengths[0], lengths[1]) * 0.5),
                        height=float(lengths[2]),
                    )
                else:
                    payload[f'{prefix}_{idx}'] = pv.Cube(
                        center=center,
                        x_length=float(lengths[0]),
                        y_length=float(lengths[1]),
                        z_length=float(lengths[2]),
                    )
        active_names = set(payload)
        for stale_name in tuple(self._scene_actor_names - active_names):
            self._remove_mesh(stale_name)
        for name, mesh in payload.items():
            self._update_mesh(name, mesh, style='wireframe', opacity=0.55)
        self._scene_actor_names = active_names
        self._render()

    def set_target_pose(self, pose) -> None:
        self._target_pose = pose
        if self.plotter is None:
            return
        payload = self.target_visual.build(pose, show_axes=self._target_axes_visible)
        for name, (mesh, kwargs) in payload.items():
            self._update_mesh(name, mesh, **kwargs)
        if not self._target_axes_visible:
            for axis_name in ('x', 'y', 'z'):
                self._remove_mesh(f'target_axis_{axis_name}')
        self._render()

    def set_trajectory(self, points: np.ndarray) -> None:
        if points is None:
            self.clear_trajectory()
            return
        pts = np.asarray(points, dtype=float)
        self._trajectory_points = pts.copy()
        if self.plotter is None or len(pts) < 2 or not self._trajectory_visible:
            return
        for name, (mesh, kwargs) in self.trajectory_visual.build(pts).items():
            self._update_mesh(name, mesh, **kwargs)
        self._render()

    def clear_trajectory(self) -> None:
        self._trajectory_points = None
        self._remove_mesh('trajectory')
        self._render()

    def set_playback_marker(self, point: np.ndarray) -> None:
        point_arr = np.asarray(point, dtype=float).reshape(3)
        self._playback_marker = point_arr.copy()
        if self.plotter is None:
            return
        import pyvista as pv

        marker = pv.PolyData(np.asarray([point_arr], dtype=float))
        self._update_mesh('playback_marker', marker, point_size=15, render_points_as_spheres=True)
        self._render()

    def fit_camera(self) -> None:
        if self.plotter is None:
            return
        self.plotter.reset_camera()
        self._render()

    def set_target_axes_visible(self, visible: bool) -> None:
        self._target_axes_visible = bool(visible)
        if self._target_pose is None:
            return
        if not self._target_axes_visible:
            for axis_name in ('x', 'y', 'z'):
                self._remove_mesh(f'target_axis_{axis_name}')
            self._render()
            return
        self.set_target_pose(self._target_pose)

    def set_trajectory_visible(self, visible: bool) -> None:
        self._trajectory_visible = bool(visible)
        if not visible:
            self._remove_mesh('trajectory')
            self._render()
            return
        if self._trajectory_points is not None:
            self.set_trajectory(self._trajectory_points)

    def scene_snapshot(self) -> dict[str, object]:
        return {
            'title': self._scene_title,
            'overlay_text': self._overlay_text,
            'robot_points': None if self._robot_points is None else self._robot_points.copy(),
            'trajectory_points': None if self._trajectory_points is None else self._trajectory_points.copy(),
            'playback_marker': None if self._playback_marker is None else self._playback_marker.copy(),
            'target_pose': self._target_pose,
            'target_axes_visible': bool(self._target_axes_visible),
            'trajectory_visible': bool(self._trajectory_visible),
            'robot_geometry': self._robot_geometry,
            'scene_obstacles': list(self._scene_obstacles),
            'attached_objects': list(self._attached_objects),
        }

    def scene_runtime_state(self) -> RenderCapabilityState:
        """Return the structured runtime status for the 3D scene surface."""
        return self._scene_runtime

    def screenshot_runtime_state(self) -> RenderCapabilityState:
        """Return the structured runtime status for scene screenshot capture."""
        return self._screenshot_runtime

    def render_runtime_snapshot(self) -> dict[str, RenderCapabilityState]:
        """Return the aggregate render runtime status exposed by the scene widget shell."""
        return {'scene_3d': self.scene_runtime_state(), 'screenshot': self.screenshot_runtime_state()}

    def capture_screenshot(self, path):
        return self.screenshot_service.capture(self, path)
