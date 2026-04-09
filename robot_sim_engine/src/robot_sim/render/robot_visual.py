from __future__ import annotations

from dataclasses import dataclass
<<<<<<< HEAD
from pathlib import Path
=======
>>>>>>> 3ed78e647985c6d680c085e4480d898855278db3

import numpy as np


@dataclass(frozen=True)
class RobotVisualConfig:
    line_width: float = 5.0
    joint_point_size: float = 12.0
    use_tube: bool = False
    tube_radius: float = 0.018


class RobotVisual:
<<<<<<< HEAD
    """Build live robot render payloads from FK points plus optional runtime geometry.

    The stable V7 scene still projects FK skeleton points, but when runtime geometry is
    available the live plotter should also receive deterministic per-link visual meshes
    instead of ignoring the imported geometry bundle entirely.
    """

    def __init__(self, config: RobotVisualConfig | None = None) -> None:
        self.config = config or RobotVisualConfig()
        self._cache_key: tuple[bytes, bytes | None] | None = None
        self._cached_payload: dict[str, tuple[object, dict[str, object]]] | None = None

    def describe_renderables(self, points, robot_geometry=None) -> tuple[dict[str, object], ...]:
        """Describe deterministic link renderables without importing GUI/render backends.

        Args:
            points: FK joint positions with shape ``(N, 3)``.
            robot_geometry: Optional ``RobotGeometry`` bundle describing link primitives.

        Returns:
            tuple[dict[str, object], ...]: Stable render descriptors used by the live
                PyVista backend and unit tests.

        Raises:
            ValueError: If the point array is malformed.

        Boundary behavior:
            If geometry metadata is missing or mismatched with the FK chain length, the
            returned descriptors fall back to one capsule-like segment per visible link.
        """
        pts = np.asarray(points, dtype=float)
        if pts.ndim != 2 or pts.shape[0] < 2 or pts.shape[1] != 3:
            raise ValueError('robot visual requires an (N, 3) point array with N >= 2')
        descriptors: list[dict[str, object]] = []
        segments = [(pts[i], pts[i + 1]) for i in range(len(pts) - 1)]
        geometry_links = tuple(getattr(robot_geometry, 'links', ()) or ())
        if not geometry_links:
            geometry_links = tuple(None for _ in segments)
        for idx, (p0, p1) in enumerate(segments):
            link = geometry_links[idx] if idx < len(geometry_links) else None
            descriptors.extend(self._describe_link(idx, p0, p1, link))
        return tuple(descriptors)

    def _describe_link(self, idx: int, p0: np.ndarray, p1: np.ndarray, link) -> tuple[dict[str, object], ...]:
        axis_vec = np.asarray(p1, dtype=float) - np.asarray(p0, dtype=float)
        length = float(np.linalg.norm(axis_vec))
        if length <= 1.0e-9:
            direction = np.array([0.0, 0.0, 1.0], dtype=float)
        else:
            direction = axis_vec / length
        center = (np.asarray(p0, dtype=float) + np.asarray(p1, dtype=float)) * 0.5
        radius = float(getattr(link, 'radius', 0.03) if link is not None else 0.03)
        metadata = dict(getattr(link, 'metadata', {}) or {}) if link is not None else {}
        primitives = tuple(getattr(link, 'visual_primitives', ()) or ()) if link is not None else ()
        if not primitives:
            primitives = tuple(getattr(link, 'collision_primitives', ()) or ()) if link is not None else ()
        if not primitives:
            primitives = (
                {
                    'kind': 'capsule',
                    'params': {'radius': radius, 'length': length},
                    'local_transform': None,
                },
            )
        normalized: list[dict[str, object]] = []
        for primitive_idx, primitive in enumerate(primitives):
            kind = str(getattr(primitive, 'kind', primitive.get('kind', 'capsule')) if isinstance(primitive, dict) else primitive.kind).strip().lower() or 'capsule'
            params = dict(getattr(primitive, 'params', primitive.get('params', {})) if isinstance(primitive, dict) else primitive.params)
            local_transform = getattr(primitive, 'local_transform', primitive.get('local_transform')) if isinstance(primitive, dict) else primitive.local_transform
            normalized.append(
                {
                    'actor_name': f'robot_geom_{idx}_{primitive_idx}',
                    'link_index': idx,
                    'link_name': str(getattr(link, 'name', f'link_{idx}') if link is not None else f'link_{idx}'),
                    'kind': kind,
                    'center': center.copy(),
                    'direction': direction.copy(),
                    'length': length,
                    'radius': radius,
                    'params': params,
                    'local_transform': None if local_transform is None else np.asarray(local_transform, dtype=float),
                    'metadata': metadata,
                    'segment_start': np.asarray(p0, dtype=float).copy(),
                    'segment_end': np.asarray(p1, dtype=float).copy(),
                }
            )
        return tuple(normalized)

    def build(self, points, robot_geometry=None) -> dict[str, tuple[object, dict[str, object]]]:
        import pyvista as pv

        pts = np.asarray(points, dtype=float)
        geometry_key = None
        if robot_geometry is not None:
            geometry_key = repr(robot_geometry).encode('utf-8', errors='ignore')
        cache_key = (pts.tobytes(), geometry_key)
=======
    def __init__(self, config: RobotVisualConfig | None = None) -> None:
        self.config = config or RobotVisualConfig()
        self._cache_key: bytes | None = None
        self._cached_payload: dict[str, tuple[object, dict[str, object]]] | None = None

    def build(self, points) -> dict[str, tuple[object, dict[str, object]]]:
        import pyvista as pv

        pts = np.asarray(points, dtype=float)
        if pts.ndim != 2 or pts.shape[0] < 2 or pts.shape[1] != 3:
            raise ValueError('robot visual requires an (N, 3) point array with N >= 2')
        cache_key = pts.tobytes()
>>>>>>> 3ed78e647985c6d680c085e4480d898855278db3
        if self._cache_key == cache_key and self._cached_payload is not None:
            return self._cached_payload
        line_mesh = pv.lines_from_points(pts)
        if self.config.use_tube:
            line_mesh = line_mesh.tube(radius=float(self.config.tube_radius))
        joints_mesh = pv.PolyData(pts)
<<<<<<< HEAD
        payload: dict[str, tuple[object, dict[str, object]]] = {
=======
        payload = {
>>>>>>> 3ed78e647985c6d680c085e4480d898855278db3
            'robot_lines': (line_mesh, {'line_width': float(self.config.line_width)}),
            'robot_joints': (
                joints_mesh,
                {
                    'point_size': float(self.config.joint_point_size),
                    'render_points_as_spheres': True,
                },
            ),
        }
<<<<<<< HEAD
        for descriptor in self.describe_renderables(pts, robot_geometry=robot_geometry):
            mesh = self._build_mesh_for_descriptor(descriptor, pv)
            payload[str(descriptor['actor_name'])] = (mesh, {'opacity': 0.35, 'smooth_shading': True})
        self._cache_key = cache_key
        self._cached_payload = payload
        return payload

    def _build_mesh_for_descriptor(self, descriptor: dict[str, object], pv):
        kind = str(descriptor.get('kind', 'capsule')).strip().lower() or 'capsule'
        params = dict(descriptor.get('params') or {})
        center = np.asarray(descriptor['center'], dtype=float)
        direction = np.asarray(descriptor['direction'], dtype=float)
        length = max(float(descriptor.get('length', 0.0) or 0.0), 1.0e-6)
        radius = max(float(descriptor.get('radius', 0.03) or 0.03), 1.0e-4)
        if kind == 'sphere':
            sphere_radius = self._param_float(params, 'radius', radius)
            return pv.Sphere(radius=sphere_radius, center=center)
        if kind == 'cylinder':
            cyl_radius = self._param_float(params, 'radius', radius)
            cyl_length = self._param_float(params, 'length', length)
            return pv.Cylinder(center=center, direction=direction, radius=cyl_radius, height=max(cyl_length, 1.0e-6))
        if kind == 'box':
            sx, sy, sz = self._param_vec(params, 'size', (radius * 2.0, radius * 2.0, length))
            cube = pv.Cube(center=(0.0, 0.0, 0.0), x_length=float(sx), y_length=float(sy), z_length=float(sz))
            return cube.transform(self._segment_transform(direction, center), inplace=False)
        if kind == 'mesh':
            mesh = self._load_mesh_primitive(params, pv, center=center, direction=direction, length=length, radius=radius)
            if mesh is not None:
                return mesh
        return self._build_capsule_mesh(pv, center=center, direction=direction, length=length, radius=radius)

    def _load_mesh_primitive(self, params: dict[str, object], pv, *, center: np.ndarray, direction: np.ndarray, length: float, radius: float):
        filename = str(params.get('resolved_filename') or params.get('filename') or '').strip()
        if filename:
            candidate = Path(filename)
            if candidate.exists():
                try:
                    mesh = pv.read(str(candidate))
                    scale = self._param_vec(params, 'scale', (1.0, 1.0, 1.0))
                    if tuple(scale) != (1.0, 1.0, 1.0):
                        mesh = mesh.scale(scale, inplace=False)
                    return mesh.transform(self._segment_transform(direction, center), inplace=False)
                except (FileNotFoundError, OSError, ValueError, RuntimeError, TypeError, AttributeError):
                    pass
        return None

    @staticmethod
    def _build_capsule_mesh(pv, *, center: np.ndarray, direction: np.ndarray, length: float, radius: float):
        cylinder_height = max(length - 2.0 * radius, 1.0e-6)
        cylinder = pv.Cylinder(center=center, direction=direction, radius=radius, height=cylinder_height)
        half = direction * (cylinder_height * 0.5)
        sphere_a = pv.Sphere(radius=radius, center=center - half)
        sphere_b = pv.Sphere(radius=radius, center=center + half)
        return cylinder.merge(sphere_a).merge(sphere_b)

    @staticmethod
    def _segment_transform(direction: np.ndarray, center: np.ndarray) -> np.ndarray:
        z_axis = np.asarray(direction, dtype=float)
        if float(np.linalg.norm(z_axis)) <= 1.0e-9:
            z_axis = np.array([0.0, 0.0, 1.0], dtype=float)
        else:
            z_axis = z_axis / float(np.linalg.norm(z_axis))
        helper = np.array([0.0, 1.0, 0.0], dtype=float)
        if abs(float(np.dot(helper, z_axis))) > 0.95:
            helper = np.array([1.0, 0.0, 0.0], dtype=float)
        x_axis = np.cross(helper, z_axis)
        if float(np.linalg.norm(x_axis)) <= 1.0e-9:
            x_axis = np.array([1.0, 0.0, 0.0], dtype=float)
        else:
            x_axis = x_axis / float(np.linalg.norm(x_axis))
        y_axis = np.cross(z_axis, x_axis)
        y_axis = y_axis / max(float(np.linalg.norm(y_axis)), 1.0e-9)
        transform = np.eye(4, dtype=float)
        transform[:3, 0] = x_axis
        transform[:3, 1] = y_axis
        transform[:3, 2] = z_axis
        transform[:3, 3] = np.asarray(center, dtype=float)
        return transform

    @staticmethod
    def _param_float(params: dict[str, object], key: str, default: float) -> float:
        raw = params.get(key, default)
        if isinstance(raw, str):
            raw = raw.strip().split()[0] if raw.strip() else default
        try:
            value = float(raw)
        except (TypeError, ValueError):
            value = float(default)
        return value

    @staticmethod
    def _param_vec(params: dict[str, object], key: str, default: tuple[float, float, float]) -> tuple[float, float, float]:
        raw = params.get(key)
        if raw is None:
            return tuple(float(v) for v in default)
        if isinstance(raw, str):
            parts = [part for part in raw.replace(',', ' ').split() if part]
        else:
            parts = list(raw) if isinstance(raw, (list, tuple)) else [raw]
        values: list[float] = []
        for idx, fallback in enumerate(default):
            try:
                values.append(float(parts[idx]))
            except (IndexError, TypeError, ValueError):
                values.append(float(fallback))
        return tuple(values[:3])
=======
        self._cache_key = cache_key
        self._cached_payload = payload
        return payload
>>>>>>> 3ed78e647985c6d680c085e4480d898855278db3
