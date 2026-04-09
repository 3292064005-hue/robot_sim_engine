from __future__ import annotations

from pathlib import Path
import struct
import zlib

import numpy as np

<<<<<<< HEAD
from robot_sim.domain.errors import CancelledTaskError, ExportRobotError
from robot_sim.model.render_runtime import RenderCapabilityState
from robot_sim.render.backend_protocol import CaptureBackend, CaptureResult
=======
from robot_sim.domain.errors import ExportRobotError
>>>>>>> 3ed78e647985c6d680c085e4480d898855278db3
from robot_sim.render.robot_visual import RobotVisual
from robot_sim.render.target_visual import TargetVisual
from robot_sim.render.trajectory_visual import TrajectoryVisual


<<<<<<< HEAD
class _LivePlotterCaptureBackend:
    """Capture backend backed by a live plotter framebuffer."""

    backend_id = 'live_plotter'

    def runtime_state(self, scene_widget) -> RenderCapabilityState:
        return RenderCapabilityState.available_state(
            'screenshot',
            backend='live_plotter',
            reason='live_plotter_capture',
            message='Scene screenshots are captured from the live plotter backend.',
            level='live_capture',
            provenance={'capture_source': 'live_plotter_framebuffer', 'render_path': 'live_plotter'},
        )

    def capture(self, scene_widget, path: str) -> CaptureResult:
        plotter = getattr(scene_widget, 'plotter', None)
        if plotter is None or not hasattr(plotter, 'screenshot'):
            raise ExportRobotError(
                'scene capture backend is unavailable',
                error_code='unsupported_capture_backend',
                remediation_hint='安装 pyvista/pyvistaqt，或在产生场景数据后再执行截图。',
                metadata={'path': str(path)},
            )
        plotter.screenshot(str(path))
        runtime_state = self.runtime_state(scene_widget)
        return CaptureResult(path=str(path), runtime_state=runtime_state, provenance=dict(runtime_state.provenance))


class _SnapshotCaptureBackend:
    """Capture backend backed by scene snapshot rasterization."""

    backend_id = 'snapshot_renderer'

    def __init__(self, service: 'ScreenshotService') -> None:
        self._service = service

    def runtime_state(self, scene_widget) -> RenderCapabilityState:
        snapshot_fn = getattr(scene_widget, 'scene_snapshot', None)
        snapshot = dict(snapshot_fn() or {}) if callable(snapshot_fn) else {}
        return RenderCapabilityState(
            capability='screenshot',
            status='degraded',
            backend='snapshot_renderer',
            reason='snapshot_renderer_fallback',
            message='Scene screenshots are running through the snapshot fallback renderer.',
            level='snapshot_capture',
            provenance=self._service.snapshot_provenance(snapshot, backend='snapshot_renderer'),
        )

    def capture(self, scene_widget, path: str) -> CaptureResult:
        snapshot_fn = getattr(scene_widget, 'scene_snapshot', None)
        snapshot = dict(snapshot_fn() or {}) if callable(snapshot_fn) else None
        if not snapshot:
            raise ExportRobotError(
                'scene capture backend is unavailable',
                error_code='unsupported_capture_backend',
                remediation_hint='安装 pyvista/pyvistaqt，或在产生场景数据后再执行截图。',
                metadata={'path': str(path)},
            )
        details = self._service.capture_from_snapshot_details(snapshot, path)
        return CaptureResult(
            path=str(details['path']),
            runtime_state=details['runtime_state'],
            provenance=dict(details['provenance']),
        )


class _UnsupportedCaptureBackend:
    """Capture backend used when no runtime screenshot capability is available."""

    backend_id = 'none'

    def runtime_state(self, scene_widget) -> RenderCapabilityState:
        return RenderCapabilityState(
            capability='screenshot',
            status='unsupported',
            backend='none',
            reason='capture_backend_missing',
            error_code='unsupported_capture_backend',
            message='Scene screenshot capture backend is unavailable.',
            level='unsupported',
            provenance={'capture_source': 'unavailable', 'render_path': 'none'},
        )

    def capture(self, scene_widget, path: str) -> CaptureResult:
        raise ExportRobotError(
            'scene capture backend is unavailable',
            error_code='unsupported_capture_backend',
            remediation_hint='安装 pyvista/pyvistaqt，或在产生场景数据后再执行截图。',
            metadata={'path': str(path)},
        )


class ScreenshotService:
    """Render and persist scene screenshots for Qt and headless export flows."""

=======
class ScreenshotService:
>>>>>>> 3ed78e647985c6d680c085e4480d898855278db3
    def __init__(self) -> None:
        self._robot_visual = RobotVisual()
        self._target_visual = TargetVisual()
        self._trajectory_visual = TrajectoryVisual()
<<<<<<< HEAD
        self._live_backend = _LivePlotterCaptureBackend()
        self._snapshot_backend = _SnapshotCaptureBackend(self)
        self._unsupported_backend = _UnsupportedCaptureBackend()

    def _capture_backends(self) -> tuple[CaptureBackend, ...]:
        """Return capture backends ordered by preference for a scene widget."""
        return (self._live_backend, self._snapshot_backend, self._unsupported_backend)

    def _select_capture_backend(self, scene_widget) -> CaptureBackend:
        """Return the first capture backend supported by the provided scene widget."""
        state_fn = getattr(scene_widget, 'screenshot_runtime_state', None)
        if callable(state_fn):
            state = RenderCapabilityState.from_mapping('screenshot', state_fn())
            for backend in self._capture_backends():
                if backend.backend_id == state.backend:
                    return backend
        plotter = getattr(scene_widget, 'plotter', None)
        if plotter is not None and hasattr(plotter, 'screenshot'):
            return self._live_backend
        snapshot_fn = getattr(scene_widget, 'scene_snapshot', None)
        if callable(snapshot_fn):
            snapshot = dict(snapshot_fn() or {})
            if snapshot:
                return self._snapshot_backend
        return self._unsupported_backend


    def snapshot_sampling_counters(
        self,
        snapshot: dict[str, object],
        *,
        backend: str,
        source: str,
    ) -> tuple[dict[str, object], ...]:
        """Build structured sampling counters for a snapshot-based screenshot render.

        Args:
            snapshot: Serializable scene snapshot captured on the UI thread.
            backend: Backend identifier used for the screenshot render.
            source: Logical telemetry source attached to the counter samples.

        Returns:
            tuple[dict[str, object], ...]: Counter payloads suitable for
                ``StateStore.record_render_sampling_counters``.

        Raises:
            None: Missing snapshot sections are normalized to zero counts.
        """
        robot_points = self._as_points(snapshot.get('robot_points'))
        trajectory_points = self._as_points(snapshot.get('trajectory_points'))
        playback_marker = self._as_point(snapshot.get('playback_marker'))
        target_pose = snapshot.get('target_pose')
        target_point = self._as_point(getattr(target_pose, 'p', None)) if target_pose is not None else None
        overlay_text = str(snapshot.get('overlay_text') or '').strip()
        scene_obstacles = tuple(snapshot.get('scene_obstacles') or ())
        attached_objects = tuple(snapshot.get('attached_objects') or ())
        show_target_axes = bool(snapshot.get('target_axes_visible', True)) and target_point is not None
        robot_count = 0 if robot_points is None else int(len(robot_points))
        trajectory_count = 0 if trajectory_points is None else int(len(trajectory_points))
        playback_count = 1 if playback_marker is not None else 0
        target_count = 1 if target_point is not None else 0
        target_axis_segments = 3 if show_target_axes else 0
        overlay_entity_count = 1 if overlay_text else 0
        obstacle_entities = int(len(scene_obstacles) + len(attached_objects))
        drawable_entities = sum(
            1
            for flag in (
                robot_count > 0,
                trajectory_count > 0,
                playback_count > 0,
                target_count > 0,
                target_axis_segments > 0,
                overlay_entity_count > 0,
                obstacle_entities > 0,
            )
            if flag
        )
        drawable_samples = robot_count + trajectory_count + playback_count + target_count + target_axis_segments * 2 + overlay_entity_count + obstacle_entities * 8
        canvas_pixels = 480 * 640
        common = {'capability': 'screenshot', 'backend': str(backend or ''), 'source': str(source or ''), 'metadata': {'render_path': 'snapshot_renderer'}}
        return (
            {**common, 'counter_name': 'robot_points', 'value': float(robot_count), 'unit': 'points'},
            {**common, 'counter_name': 'trajectory_points', 'value': float(trajectory_count), 'unit': 'points'},
            {**common, 'counter_name': 'target_axis_segments', 'value': float(target_axis_segments), 'unit': 'segments'},
            {**common, 'counter_name': 'overlay_entities', 'value': float(overlay_entity_count), 'unit': 'entities'},
            {**common, 'counter_name': 'scene_obstacles', 'value': float(len(scene_obstacles)), 'unit': 'objects'},
            {**common, 'counter_name': 'attached_objects', 'value': float(len(attached_objects)), 'unit': 'objects'},
            {**common, 'counter_name': 'drawable_entities', 'value': float(drawable_entities), 'unit': 'entities'},
            {**common, 'counter_name': 'drawable_samples', 'value': float(drawable_samples), 'unit': 'samples'},
            {**common, 'counter_name': 'canvas_pixels', 'value': float(canvas_pixels), 'unit': 'pixels'},
        )

    def snapshot_sample_count(self, snapshot: dict[str, object]) -> int:
        """Return an aggregate drawable-sample count for a snapshot render path."""
        counters = self.snapshot_sampling_counters(snapshot, backend='snapshot_renderer', source='screenshot_sample_count')
        for counter in counters:
            if counter.get('counter_name') == 'drawable_samples':
                return int(counter.get('value', 0.0) or 0)
        return 0

    def snapshot_provenance(self, snapshot: dict[str, object], *, backend: str = 'snapshot_renderer') -> dict[str, object]:
        """Build structured provenance for snapshot-based capture paths.

        Args:
            snapshot: Serializable scene snapshot captured on the UI thread.
            backend: Effective backend identifier for the capture.

        Returns:
            dict[str, object]: JSON-safe provenance payload describing where the screenshot comes
                from and what drawable data contributed to it.
        """
        counters = self.snapshot_sampling_counters(snapshot, backend=backend, source='screenshot_provenance')
        drawable_samples = self.snapshot_sample_count(snapshot)
        return {
            'capture_source': 'scene_snapshot',
            'render_path': str(backend or 'snapshot_renderer'),
            'snapshot_title': str(snapshot.get('title') or 'Robot Sim Engine'),
            'drawable_samples': int(drawable_samples),
            'counters': tuple(dict(counter) for counter in counters),
        }

    def runtime_state(self, scene_widget) -> RenderCapabilityState:
        """Return the structured runtime status for screenshot capture on a scene widget."""
        state_fn = getattr(scene_widget, 'screenshot_runtime_state', None)
        if callable(state_fn):
            return RenderCapabilityState.from_mapping('screenshot', state_fn())
        return self._select_capture_backend(scene_widget).runtime_state(scene_widget)

    def capture_details(self, scene_widget, path: str | Path) -> dict[str, object]:
        """Capture a scene widget synchronously and return structured provenance details.

        Args:
            scene_widget: Scene widget exposing either a live plotter or ``scene_snapshot()``.
            path: Destination path for the screenshot.

        Returns:
            dict[str, object]: Saved path plus runtime-state/provenance details.

        Raises:
            ExportRobotError: If no supported capture backend is available.
        """
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        backend = self._select_capture_backend(scene_widget)
        result = backend.capture(scene_widget, str(target))
        self._ensure_non_empty(target)
        return {'path': target, 'runtime_state': result.runtime_state, 'provenance': dict(result.provenance)}

    def capture(self, scene_widget, path: str | Path):
        """Compatibility wrapper returning only the saved screenshot path."""
        details = self.capture_details(scene_widget, path)
        return Path(str(details['path']))

    def capture_from_snapshot_details(
        self,
        snapshot: dict[str, object],
        path: str | Path,
        *,
        progress_cb=None,
        cancel_flag=None,
        correlation_id: str = '',
    ) -> dict[str, object]:
        """Render a screenshot from a scene snapshot and return provenance details."""
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        self._emit_progress(progress_cb, 10.0, 'building raster from scene snapshot', {'path': str(target), 'correlation_id': correlation_id})
        self._ensure_not_cancelled(cancel_flag)
        self._capture_from_snapshot(snapshot, target)
        self._ensure_not_cancelled(cancel_flag)
        self._ensure_non_empty(target)
        runtime_state = RenderCapabilityState(
            capability='screenshot',
            status='degraded',
            backend='snapshot_renderer',
            reason='snapshot_renderer_fallback',
            message='Scene screenshots are running through the snapshot fallback renderer.',
            level='snapshot_capture',
            provenance=self.snapshot_provenance(snapshot, backend='snapshot_renderer'),
        )
        runtime_state.require_level('snapshot_capture')
        self._emit_progress(progress_cb, 100.0, 'scene screenshot completed', {'path': str(target), 'capture_level': runtime_state.level})
        return {'path': target, 'runtime_state': runtime_state, 'provenance': dict(runtime_state.provenance)}

    def capture_from_snapshot(
        self,
        snapshot: dict[str, object],
        path: str | Path,
        *,
        progress_cb=None,
        cancel_flag=None,
        correlation_id: str = '',
    ) -> Path:
        """Compatibility wrapper returning only the saved path for snapshot capture."""
        details = self.capture_from_snapshot_details(
            snapshot,
            path,
            progress_cb=progress_cb,
            cancel_flag=cancel_flag,
            correlation_id=correlation_id,
        )
        return Path(str(details['path']))

    @staticmethod
    def _emit_progress(progress_cb, percent: float, message: str, payload: dict[str, object] | None = None) -> None:
        if callable(progress_cb):
            progress_cb(float(percent), str(message), dict(payload or {}))

    @staticmethod
    def _ensure_not_cancelled(cancel_flag) -> None:
        if callable(cancel_flag) and bool(cancel_flag()):
            raise CancelledTaskError('scene screenshot cancelled')
=======

    def capture(self, scene_widget, path: str | Path):
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        plotter = getattr(scene_widget, 'plotter', None)
        if plotter is not None and hasattr(plotter, 'screenshot'):
            plotter.screenshot(str(target))
            self._ensure_non_empty(target)
            return target

        snapshot_fn = getattr(scene_widget, 'scene_snapshot', None)
        snapshot = snapshot_fn() if callable(snapshot_fn) else None
        if snapshot:
            self._capture_from_snapshot(snapshot, target)
            self._ensure_non_empty(target)
            return target

        raise ExportRobotError(
            'scene capture backend is unavailable',
            error_code='unsupported_capture_backend',
            remediation_hint='安装 pyvista/pyvistaqt，或在产生场景数据后再执行截图。',
            metadata={'path': str(target)},
        )
>>>>>>> 3ed78e647985c6d680c085e4480d898855278db3

    def _capture_from_snapshot(self, snapshot: dict[str, object], target: Path) -> None:
        robot_points = self._as_points(snapshot.get('robot_points'))
        trajectory_points = self._as_points(snapshot.get('trajectory_points'))
        playback_marker = self._as_point(snapshot.get('playback_marker'))
        target_pose = snapshot.get('target_pose')
        target_point = self._as_point(getattr(target_pose, 'p', None)) if target_pose is not None else None
        target_rotation = np.asarray(getattr(target_pose, 'R', np.eye(3)), dtype=float) if target_pose is not None else np.eye(3)
<<<<<<< HEAD
        scene_obstacles = tuple(snapshot.get('scene_obstacles') or ())
        attached_objects = tuple(snapshot.get('attached_objects') or ())
        show_target_axes = bool(snapshot.get('target_axes_visible', True))
        title = str(snapshot.get('title') or 'Robot Sim Engine')
        overlay_text = str(snapshot.get('overlay_text') or '').strip()

        if robot_points is None and trajectory_points is None and playback_marker is None and target_point is None and not overlay_text and not scene_obstacles and not attached_objects:
=======
        show_target_axes = bool(snapshot.get('target_axes_visible', True))
        title = str(snapshot.get('title') or 'Robot Sim Engine')

        if robot_points is None and trajectory_points is None and playback_marker is None and target_point is None:
>>>>>>> 3ed78e647985c6d680c085e4480d898855278db3
            raise ExportRobotError(
                'scene snapshot did not contain any drawable data',
                error_code='render_unavailable',
                remediation_hint='先执行 FK / IK / 轨迹规划，确保场景中存在机械臂、目标位姿或轨迹。',
                metadata={'path': str(target)},
            )

        canvas = np.full((480, 640, 3), 255, dtype=np.uint8)
        all_points = [arr for arr in (robot_points, trajectory_points) if arr is not None]
        if playback_marker is not None:
            all_points.append(playback_marker.reshape(1, 3))
        if target_point is not None:
            all_points.append(target_point.reshape(1, 3))
            if show_target_axes:
                axis_len = 0.12
                axes = np.stack(
                    [
                        target_point,
                        target_point + target_rotation[:, 0] * axis_len,
                        target_point,
                        target_point + target_rotation[:, 1] * axis_len,
                        target_point,
                        target_point + target_rotation[:, 2] * axis_len,
                    ],
                    axis=0,
                )
                all_points.append(axes)
<<<<<<< HEAD
        obstacle_corner_ranges: list[tuple[str, int, int]] = []
        for prefix, objects in (('scene_obstacle', scene_obstacles), ('attached_object', attached_objects)):
            for obj in objects:
                corners = self._scene_object_corners(obj)
                if corners is None:
                    continue
                start = sum(len(arr) for arr in all_points) if all_points else 0
                all_points.append(corners)
                end = start + len(corners)
                obstacle_corner_ranges.append((prefix, start, end))
        if all_points:
            stacked = np.vstack(all_points)
            projected = self._project_points(stacked, canvas.shape[1], canvas.shape[0])
            cursor = 0
        else:
            projected = np.empty((0, 2), dtype=int)
            cursor = 0
            self._draw_overlay_placeholder(canvas, overlay_text)
=======
        stacked = np.vstack(all_points)
        projected = self._project_points(stacked, canvas.shape[1], canvas.shape[0])
        cursor = 0
>>>>>>> 3ed78e647985c6d680c085e4480d898855278db3

        if robot_points is not None:
            rp = projected[cursor: cursor + len(robot_points)]
            cursor += len(robot_points)
            self._draw_polyline(canvas, rp, color=(40, 90, 180), thickness=4)
            self._draw_points(canvas, rp, color=(20, 20, 20), radius=4)

        if trajectory_points is not None:
            tp = projected[cursor: cursor + len(trajectory_points)]
            cursor += len(trajectory_points)
            self._draw_polyline(canvas, tp, color=(220, 110, 30), thickness=2)
            self._draw_points(canvas, tp[-1:], color=(220, 110, 30), radius=4)

        if playback_marker is not None:
            pm = projected[cursor]
            cursor += 1
            self._draw_points(canvas, np.asarray([pm]), color=(180, 40, 40), radius=6)

        if target_point is not None:
            tg = projected[cursor]
            cursor += 1
            self._draw_cross(canvas, tg, color=(30, 160, 60), size=8, thickness=2)
            if show_target_axes:
                axis_pts = projected[cursor: cursor + 6]
                cursor += 6
                self._draw_segment(canvas, axis_pts[0], axis_pts[1], color=(230, 70, 70), thickness=2)
                self._draw_segment(canvas, axis_pts[2], axis_pts[3], color=(70, 180, 70), thickness=2)
                self._draw_segment(canvas, axis_pts[4], axis_pts[5], color=(70, 70, 230), thickness=2)

<<<<<<< HEAD
        for prefix, start, end in obstacle_corner_ranges:
            corners = projected[start:end]
            self._draw_aabb_wireframe(canvas, corners, color=(120, 120, 120) if prefix == 'scene_obstacle' else (120, 40, 160))

=======
>>>>>>> 3ed78e647985c6d680c085e4480d898855278db3
        self._draw_title_bar(canvas, title)
        self._write_png(target, canvas)

    @staticmethod
    def _as_points(value: object) -> np.ndarray | None:
        if value is None:
            return None
        arr = np.asarray(value, dtype=float)
        if arr.ndim != 2 or arr.shape[1] != 3 or arr.size == 0:
            return None
        return arr

    @staticmethod
    def _as_point(value: object) -> np.ndarray | None:
        if value is None:
            return None
        arr = np.asarray(value, dtype=float).reshape(-1)
        if arr.shape != (3,):
            return None
        return arr

    @staticmethod
    def _project_points(points: np.ndarray, width: int, height: int) -> np.ndarray:
        xy = np.column_stack([points[:, 0], -points[:, 2] - 0.35 * points[:, 1]])
        lo = xy.min(axis=0)
        hi = xy.max(axis=0)
        span = np.maximum(hi - lo, 1e-6)
        scale = min((width * 0.75) / span[0], (height * 0.68) / span[1])
        center = (lo + hi) * 0.5
        canvas_center = np.asarray([width * 0.5, height * 0.56], dtype=float)
        projected = (xy - center) * scale + canvas_center
        return np.rint(projected).astype(int)

    @staticmethod
<<<<<<< HEAD
    def _draw_overlay_placeholder(canvas: np.ndarray, overlay_text: str) -> None:
        """Draw a deterministic placeholder when only overlay text is available."""
        hash_value = zlib.crc32(overlay_text.encode('utf-8')) if overlay_text else 0
        accent = np.array([
            60 + (hash_value & 0x1F),
            110 + ((hash_value >> 5) & 0x1F),
            160 + ((hash_value >> 10) & 0x1F),
        ], dtype=np.uint8)
        canvas[120:360, 140:500, :] = np.array([248, 250, 252], dtype=np.uint8)
        canvas[140:340, 160:480, :] = np.array([255, 255, 255], dtype=np.uint8)
        canvas[156:164, 176:464, :] = accent
        canvas[196:204, 188:452, :] = np.array([95, 104, 120], dtype=np.uint8)
        canvas[228:236, 188:396, :] = np.array([165, 174, 188], dtype=np.uint8)
        canvas[270:310, 292:348, :] = accent


    @staticmethod
    def _scene_object_corners(obj) -> np.ndarray | None:
        geometry = getattr(obj, 'geometry', None)
        try:
            minimum = np.asarray(getattr(geometry, 'minimum', None), dtype=float)
            maximum = np.asarray(getattr(geometry, 'maximum', None), dtype=float)
        except (TypeError, ValueError):
            return None
        if minimum.shape != (3,) or maximum.shape != (3,):
            return None
        mn = minimum
        mx = maximum
        return np.asarray(
            [
                [mn[0], mn[1], mn[2]],
                [mx[0], mn[1], mn[2]],
                [mx[0], mx[1], mn[2]],
                [mn[0], mx[1], mn[2]],
                [mn[0], mn[1], mx[2]],
                [mx[0], mn[1], mx[2]],
                [mx[0], mx[1], mx[2]],
                [mn[0], mx[1], mx[2]],
            ],
            dtype=float,
        )

    @staticmethod
    def _draw_aabb_wireframe(canvas: np.ndarray, points: np.ndarray, *, color: tuple[int, int, int]) -> None:
        if np.asarray(points).shape != (8, 2):
            return
        edges = (
            (0, 1), (1, 2), (2, 3), (3, 0),
            (4, 5), (5, 6), (6, 7), (7, 4),
            (0, 4), (1, 5), (2, 6), (3, 7),
        )
        for i, j in edges:
            ScreenshotService._draw_segment(canvas, points[i], points[j], color=color, thickness=1)

    @staticmethod
=======
>>>>>>> 3ed78e647985c6d680c085e4480d898855278db3
    def _draw_title_bar(canvas: np.ndarray, title: str) -> None:
        canvas[:32, :, :] = np.array([245, 247, 250], dtype=np.uint8)
        hash_value = zlib.crc32(title.encode('utf-8'))
        accent = np.array([
            40 + (hash_value & 0x3F),
            90 + ((hash_value >> 6) & 0x3F),
            150 + ((hash_value >> 12) & 0x3F),
        ], dtype=np.uint8)
        canvas[8:24, 12:28, :] = accent
        canvas[12:20, 34:300, :] = np.array([70, 78, 92], dtype=np.uint8)
        title_width = min(240, max(60, len(title) * 6))
        canvas[14:18, 40:40 + title_width, :] = np.array([255, 255, 255], dtype=np.uint8)

    @classmethod
    def _draw_polyline(cls, canvas: np.ndarray, points: np.ndarray, *, color: tuple[int, int, int], thickness: int) -> None:
        if len(points) < 2:
            return
        for start, end in zip(points[:-1], points[1:]):
            cls._draw_segment(canvas, start, end, color=color, thickness=thickness)

    @classmethod
    def _draw_cross(cls, canvas: np.ndarray, point: np.ndarray, *, color: tuple[int, int, int], size: int, thickness: int) -> None:
        cls._draw_segment(canvas, point + np.array([-size, 0]), point + np.array([size, 0]), color=color, thickness=thickness)
        cls._draw_segment(canvas, point + np.array([0, -size]), point + np.array([0, size]), color=color, thickness=thickness)

    @staticmethod
    def _draw_points(canvas: np.ndarray, points: np.ndarray, *, color: tuple[int, int, int], radius: int) -> None:
        for px, py in points:
            y0 = max(py - radius, 0)
            y1 = min(py + radius + 1, canvas.shape[0])
            x0 = max(px - radius, 0)
            x1 = min(px + radius + 1, canvas.shape[1])
            if y0 >= y1 or x0 >= x1:
                continue
            yy, xx = np.ogrid[y0:y1, x0:x1]
            mask = (xx - px) ** 2 + (yy - py) ** 2 <= radius ** 2
            canvas[y0:y1, x0:x1][mask] = np.asarray(color, dtype=np.uint8)

    @staticmethod
    def _draw_segment(canvas: np.ndarray, start: np.ndarray, end: np.ndarray, *, color: tuple[int, int, int], thickness: int) -> None:
        start = np.asarray(start, dtype=int)
        end = np.asarray(end, dtype=int)
        delta = end - start
        steps = int(max(abs(delta[0]), abs(delta[1]), 1))
        xs = np.rint(np.linspace(start[0], end[0], steps + 1)).astype(int)
        ys = np.rint(np.linspace(start[1], end[1], steps + 1)).astype(int)
        half = max(thickness // 2, 0)
        color_arr = np.asarray(color, dtype=np.uint8)
        for x, y in zip(xs, ys):
            y0 = max(y - half, 0)
            y1 = min(y + half + 1, canvas.shape[0])
            x0 = max(x - half, 0)
            x1 = min(x + half + 1, canvas.shape[1])
            if y0 < y1 and x0 < x1:
                canvas[y0:y1, x0:x1] = color_arr

    @staticmethod
    def _write_png(path: Path, canvas: np.ndarray) -> None:
        if canvas.dtype != np.uint8 or canvas.ndim != 3 or canvas.shape[2] != 3:
            raise ExportRobotError(
                'invalid screenshot raster payload',
                error_code='invalid_screenshot_raster',
                remediation_hint='检查截图渲染阶段是否产生了 HxWx3 uint8 图像。',
                metadata={'shape': tuple(canvas.shape)},
            )
        height, width, _ = canvas.shape
        raw = b''.join(b'\x00' + canvas[row].tobytes() for row in range(height))
        compressed = zlib.compress(raw, level=9)
        ihdr = struct.pack('!IIBBBBB', width, height, 8, 2, 0, 0, 0)

        def chunk(tag: bytes, data: bytes) -> bytes:
            return struct.pack('!I', len(data)) + tag + data + struct.pack('!I', zlib.crc32(tag + data) & 0xFFFFFFFF)

<<<<<<< HEAD
        with path.open('wb') as handle:
            handle.write(b'\x89PNG\r\n\x1a\n')
            handle.write(chunk(b'IHDR', ihdr))
            handle.write(chunk(b'IDAT', compressed))
            handle.write(chunk(b'IEND', b''))
=======
        png = b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', ihdr) + chunk(b'IDAT', compressed) + chunk(b'IEND', b'')
        path.write_bytes(png)
>>>>>>> 3ed78e647985c6d680c085e4480d898855278db3

    @staticmethod
    def _ensure_non_empty(path: Path) -> None:
        if not path.exists() or path.stat().st_size <= 0:
            raise ExportRobotError(
<<<<<<< HEAD
                'screenshot file is empty',
                error_code='empty_screenshot_output',
                remediation_hint='确认截图目标路径可写，且场景中存在可导出的渲染内容。',
                metadata={'path': str(path)},
=======
                f'empty screenshot artifact was produced: {path}',
                error_code='empty_screenshot_artifact',
                remediation_hint='检查渲染后端是否可用，并确认场景中存在可绘制对象。',
>>>>>>> 3ed78e647985c6d680c085e4480d898855278db3
            )
