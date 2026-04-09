from __future__ import annotations

<<<<<<< HEAD
from dataclasses import dataclass
from typing import Iterable, cast

import numpy as np

from robot_sim.core.collision.geometry import AABB, aabb_from_points
from robot_sim.core.collision.self_collision import normalize_link_names, self_collision_pair_specs


def _normalize_pair_iterable(payload: object) -> tuple[tuple[str, str], ...]:
    if not isinstance(payload, (list, tuple, set)):
        return ()
    normalized: list[tuple[str, str]] = []
    for pair in payload:
        if isinstance(pair, (list, tuple)) and len(pair) == 2:
            normalized.append((str(pair[0]), str(pair[1])))
    return tuple(normalized)


@dataclass(frozen=True)
class CapsuleCollisionPayload:
    checked_pairs: tuple[tuple[str, str], ...]
    ignored_pairs: tuple[tuple[str, str], ...]
    self_pairs: tuple[tuple[str, str], ...]
    environment_pairs: tuple[tuple[str, str], ...]
    clearance_metric: float
    candidate_pair_count: int


class CapsuleCollisionBackend:
    """Experimental capsule narrow-phase backend for serial-link collision checks.

    The backend consumes sampled joint-position chains where each link is represented as a
    capsule swept between consecutive points. Self-collision uses exact segment-segment
    clearance, while environment checks evaluate capsule clearance against AABB obstacles
    with conservative segment sampling. The backend stays profile-gated through the runtime
    feature policy even though the implementation is shipped.
    """

    backend_id = 'capsule'
    availability = 'enabled'
    fallback_backend = 'aabb'
    unsupported_reason = ''
    supported_operations: tuple[str, ...] = ('state_collision', 'path_collision', 'min_distance', 'contact_pairs')

    def check_state_collision(
        self,
        joint_positions,
        *,
        obstacles: list[tuple[str, AABB]] | tuple[tuple[str, AABB], ...] = (),
        link_names: list[str] | tuple[str, ...] | None = None,
        link_radii: list[float] | tuple[float, ...] | None = None,
        allowed_collision_matrix=None,
        ignore_adjacent_self_collisions: bool = True,
        self_padding: float = 0.0,
        environment_padding: float = 0.0,
    ) -> dict[str, object]:
        frame = np.asarray(joint_positions, dtype=float)
        if frame.ndim != 2 or frame.shape[0] < 2:
            payload = self._base_payload()
            payload.update({
                'supported': True,
                'self_collision': False,
                'environment_collision': False,
                'checked_pairs': (),
                'ignored_pairs': (),
                'self_pairs': (),
                'environment_pairs': (),
                'candidate_pair_count': 0,
                'clearance_metric': 0.0,
            })
            return payload
        evaluated = self._evaluate_frame(
            frame,
            obstacles=tuple(obstacles),
            link_names=link_names,
            link_radii=link_radii,
            allowed_collision_matrix=allowed_collision_matrix,
            ignore_adjacent_self_collisions=ignore_adjacent_self_collisions,
            self_padding=self_padding,
            environment_padding=environment_padding,
        )
        payload = self._base_payload()
        payload.update({
            'supported': True,
            'self_collision': bool(evaluated.self_pairs),
            'environment_collision': bool(evaluated.environment_pairs),
            'checked_pairs': evaluated.checked_pairs,
            'ignored_pairs': evaluated.ignored_pairs,
            'self_pairs': evaluated.self_pairs,
            'environment_pairs': evaluated.environment_pairs,
            'candidate_pair_count': int(evaluated.candidate_pair_count),
            'clearance_metric': float(evaluated.clearance_metric),
        })
        return payload

    def check_path_collision(self, joint_positions, **kwargs) -> dict[str, object]:
        points = np.asarray(joint_positions, dtype=float)
        if points.ndim != 3:
            return self.check_state_collision(np.zeros((0, 3), dtype=float), **kwargs)
        checked_pairs: set[tuple[str, str]] = set()
        ignored_pairs: set[tuple[str, str]] = set()
        self_pairs: set[tuple[str, str]] = set()
        environment_pairs: set[tuple[str, str]] = set()
        candidate_pair_count = 0
        min_clearance = np.inf
        for frame in points:
            state = self.check_state_collision(frame, **kwargs)
            checked_payload = state.get('checked_pairs', ())
            ignored_payload = state.get('ignored_pairs', ())
            self_payload = state.get('self_pairs', ())
            environment_payload = state.get('environment_pairs', ())
            checked_pairs.update(_normalize_pair_iterable(checked_payload))
            ignored_pairs.update(_normalize_pair_iterable(ignored_payload))
            self_pairs.update(_normalize_pair_iterable(self_payload))
            environment_pairs.update(_normalize_pair_iterable(environment_payload))
            candidate_raw = state.get('candidate_pair_count', 0)
            clearance_raw = state.get('clearance_metric', 0.0)
            candidate_pair_count += int(candidate_raw) if isinstance(candidate_raw, (int, float)) else 0
            min_clearance = min(min_clearance, float(clearance_raw) if isinstance(clearance_raw, (int, float)) else 0.0)
        payload = self._base_payload()
        payload.update({
            'supported': True,
            'path_collision': bool(self_pairs or environment_pairs),
            'self_collision': bool(self_pairs),
            'environment_collision': bool(environment_pairs),
            'checked_pairs': tuple(sorted(checked_pairs)),
            'ignored_pairs': tuple(sorted(ignored_pairs)),
            'self_pairs': tuple(sorted(self_pairs)),
            'environment_pairs': tuple(sorted(environment_pairs)),
            'candidate_pair_count': int(candidate_pair_count),
            'clearance_metric': 0.0 if not np.isfinite(min_clearance) else float(min_clearance),
        })
        return payload

    def min_distance(self, joint_positions, **kwargs) -> float:
        payload = self.check_path_collision(joint_positions, **kwargs)
        clearance_raw = payload.get('clearance_metric', 0.0)
        return float(clearance_raw) if isinstance(clearance_raw, (int, float)) else 0.0

    def contact_pairs(self, joint_positions, **kwargs) -> tuple[tuple[str, str], ...]:
        payload = self.check_path_collision(joint_positions, **kwargs)
        self_payload = payload.get('self_pairs', ())
        environment_payload = payload.get('environment_pairs', ())
        self_pairs = cast(Iterable[tuple[str, str]], self_payload if isinstance(self_payload, (list, tuple, set)) else ())
        environment_pairs = cast(Iterable[tuple[str, str]], environment_payload if isinstance(environment_payload, (list, tuple, set)) else ())
        return tuple(sorted({*self_pairs, *environment_pairs}))

    def _evaluate_frame(
        self,
        frame: np.ndarray,
        *,
        obstacles: tuple[tuple[str, AABB], ...],
        link_names: list[str] | tuple[str, ...] | None,
        link_radii: list[float] | tuple[float, ...] | None,
        allowed_collision_matrix,
        ignore_adjacent_self_collisions: bool,
        self_padding: float,
        environment_padding: float,
    ) -> CapsuleCollisionPayload:
        names = normalize_link_names(frame.shape[0] - 1, list(link_names) if link_names is not None else None)
        radii = self._normalize_link_radii(frame.shape[0] - 1, link_radii)
        segments = tuple((np.asarray(frame[i], dtype=float), np.asarray(frame[i + 1], dtype=float)) for i in range(frame.shape[0] - 1))
        frame_boxes = tuple(
            aabb_from_points(np.vstack((start, end)), padding=float(radii[index] + max(self_padding, environment_padding, 0.0)))
            for index, (start, end) in enumerate(segments)
        )
        checked_pairs: set[tuple[str, str]] = set()
        ignored_pairs: set[tuple[str, str]] = set()
        self_pairs: set[tuple[str, str]] = set()
        environment_pairs: set[tuple[str, str]] = set()
        candidate_pair_count = 0
        clearance_values: list[float] = []

        for i, j, pair in self_collision_pair_specs(names, ignore_adjacent=ignore_adjacent_self_collisions):
            checked_pairs.add(pair)
            if allowed_collision_matrix is not None and allowed_collision_matrix.allows(*pair):
                ignored_pairs.add(pair)
                continue
            if not frame_boxes[i].intersects(frame_boxes[j]):
                clearance = frame_boxes[i].distance(frame_boxes[j]) - (max(self_padding, 0.0) * 2.0)
                clearance_values.append(float(clearance))
                candidate_pair_count += 1
                continue
            clearance = self._segment_segment_distance(*segments[i], *segments[j]) - ((radii[i] + max(self_padding, 0.0)) + (radii[j] + max(self_padding, 0.0)))
            clearance_values.append(float(clearance))
            candidate_pair_count += 1
            if clearance <= 0.0:
                self_pairs.add(pair)

        for index, (start, end) in enumerate(segments):
            link_name = str(names[index])
            link_radius = float(radii[index] + max(environment_padding, 0.0))
            for object_id, obstacle in obstacles:
                pair = (link_name, str(object_id))
                checked_pairs.add(pair)
                if allowed_collision_matrix is not None and allowed_collision_matrix.allows(*pair):
                    ignored_pairs.add(pair)
                    continue
                candidate_pair_count += 1
                inflated = AABB(minimum=np.asarray(obstacle.minimum, dtype=float) - link_radius, maximum=np.asarray(obstacle.maximum, dtype=float) + link_radius)
                if not aabb_from_points(np.vstack((start, end)), padding=0.0).intersects(inflated):
                    clearance = self._sampled_segment_box_distance(start, end, obstacle) - link_radius
                    clearance_values.append(float(clearance))
                    continue
                clearance = self._sampled_segment_box_distance(start, end, obstacle) - link_radius
                clearance_values.append(float(clearance))
                if clearance <= 0.0:
                    environment_pairs.add(pair)

        return CapsuleCollisionPayload(
            checked_pairs=tuple(sorted(checked_pairs)),
            ignored_pairs=tuple(sorted(ignored_pairs)),
            self_pairs=tuple(sorted(self_pairs)),
            environment_pairs=tuple(sorted(environment_pairs)),
            clearance_metric=0.0 if not clearance_values else float(min(clearance_values)),
            candidate_pair_count=int(candidate_pair_count),
        )

    @staticmethod
    def _normalize_link_radii(link_count: int, link_radii) -> tuple[float, ...]:
        if link_count <= 0:
            return ()
        if link_radii is None:
            return tuple(0.03 for _ in range(link_count))
        radii = [max(0.0, float(value)) for value in tuple(link_radii)]
        if not radii:
            return tuple(0.03 for _ in range(link_count))
        if len(radii) < link_count:
            radii.extend([radii[-1]] * (link_count - len(radii)))
        return tuple(radii[:link_count])

    @staticmethod
    def _point_aabb_distance(point: np.ndarray, box: AABB) -> float:
        point = np.asarray(point, dtype=float)
        minimum = np.asarray(box.minimum, dtype=float)
        maximum = np.asarray(box.maximum, dtype=float)
        delta = np.maximum(np.maximum(minimum - point, point - maximum), 0.0)
        return float(np.linalg.norm(delta))

    @classmethod
    def _sampled_segment_box_distance(cls, start: np.ndarray, end: np.ndarray, box: AABB, *, samples: int = 17) -> float:
        start = np.asarray(start, dtype=float)
        end = np.asarray(end, dtype=float)
        direction = end - start
        if np.allclose(direction, 0.0):
            return cls._point_aabb_distance(start, box)
        best = np.inf
        for t in np.linspace(0.0, 1.0, max(int(samples), 2)):
            point = start + float(t) * direction
            best = min(best, cls._point_aabb_distance(point, box))
            if best <= 1.0e-12:
                return 0.0
        return float(best)

    @staticmethod
    def _segment_segment_distance(p1: np.ndarray, q1: np.ndarray, p2: np.ndarray, q2: np.ndarray) -> float:
        u = np.asarray(q1, dtype=float) - np.asarray(p1, dtype=float)
        v = np.asarray(q2, dtype=float) - np.asarray(p2, dtype=float)
        w = np.asarray(p1, dtype=float) - np.asarray(p2, dtype=float)
        a = float(np.dot(u, u))
        b = float(np.dot(u, v))
        c = float(np.dot(v, v))
        d = float(np.dot(u, w))
        e = float(np.dot(v, w))
        denom = a * c - b * b
        small = 1.0e-12
        if a <= small and c <= small:
            return float(np.linalg.norm(np.asarray(p1, dtype=float) - np.asarray(p2, dtype=float)))
        if a <= small:
            s = 0.0
            t = np.clip(e / c if c > small else 0.0, 0.0, 1.0)
        else:
            if c <= small:
                t = 0.0
                s = np.clip(-d / a, 0.0, 1.0)
            else:
                if abs(denom) <= small:
                    s = 0.0
                else:
                    s = np.clip((b * e - c * d) / denom, 0.0, 1.0)
                t = (b * s + e) / c
                if t < 0.0:
                    t = 0.0
                    s = np.clip(-d / a, 0.0, 1.0)
                elif t > 1.0:
                    t = 1.0
                    s = np.clip((b - d) / a, 0.0, 1.0)
        closest_1 = np.asarray(p1, dtype=float) + s * u
        closest_2 = np.asarray(p2, dtype=float) + t * v
        return float(np.linalg.norm(closest_1 - closest_2))

    def _base_payload(self) -> dict[str, object]:
=======

class CapsuleCollisionBackend:
    """Placeholder capsule backend kept for interface compatibility only."""

    backend_id = 'capsule'
    availability = 'unavailable'
    fallback_backend = 'aabb'

    def _unsupported_payload(self) -> dict[str, object]:
>>>>>>> 3ed78e647985c6d680c085e4480d898855278db3
        return {
            'backend_id': self.backend_id,
            'availability': self.availability,
            'fallback_backend': self.fallback_backend,
<<<<<<< HEAD
            'reason': self.unsupported_reason,
            'supported_operations': self.supported_operations,
        }
=======
            'warning': 'capsule collision backend is not available in V7.1 and must fall back to aabb',
        }

    def check_state_collision(self, *args, **kwargs) -> dict[str, object]:
        payload = self._unsupported_payload()
        payload.update({'supported': False, 'self_collision': False, 'environment_collision': False})
        return payload

    def check_path_collision(self, *args, **kwargs) -> dict[str, object]:
        payload = self._unsupported_payload()
        payload.update({'supported': False, 'path_collision': False})
        return payload

    def min_distance(self, *args, **kwargs) -> float:
        return 0.0

    def contact_pairs(self, *args, **kwargs) -> tuple[tuple[str, str], ...]:
        return ()
>>>>>>> 3ed78e647985c6d680c085e4480d898855278db3
