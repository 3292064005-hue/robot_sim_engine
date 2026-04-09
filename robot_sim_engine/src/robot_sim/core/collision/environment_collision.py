from __future__ import annotations

<<<<<<< HEAD
from typing import Iterable, cast

import numpy as np

from robot_sim.core.collision.geometry import AABB, aabb_from_points
from robot_sim.core.collision.self_collision import normalize_link_names


def environment_collision_pairs(joint_positions, obstacles: list[tuple[str, AABB]], *, padding: float = 0.02, link_names: list[str] | None = None) -> list[list[tuple[str, str]]]:
    """Return environment-collision pairs for each trajectory frame."""
    pts = np.asarray(joint_positions, dtype=float)
    if pts.ndim != 3 or pts.shape[1] < 2:
        return [[] for _ in range(int(pts.shape[0]) if pts.ndim >= 1 else 0)]
    names = normalize_link_names(pts.shape[1] - 1, link_names)
    flags: list[list[tuple[str, str]]] = []
    for frame in pts:
        frame_boxes = [aabb_from_points(frame[i:i + 2], padding=padding) for i in range(frame.shape[0] - 1)]
        evaluation = evaluate_environment_collision_pairs(frame_boxes, obstacles=obstacles, link_names=names)
        accepted_pairs = cast(set[tuple[str, str]], evaluation['accepted_pairs'])
        flags.append(sorted(accepted_pairs))
    return flags



def environment_collision_flags(points, obstacles: list[AABB], *, padding: float = 0.02) -> list[bool]:
    """Return legacy environment-collision flags using a single robot AABB."""
=======
import numpy as np

from robot_sim.core.collision.geometry import AABB, aabb_from_points


def environment_collision_pairs(joint_positions, obstacles: list[tuple[str, AABB]], *, padding: float = 0.02, link_names: list[str] | None = None) -> list[list[tuple[str, str]]]:
    pts = np.asarray(joint_positions, dtype=float)
    if pts.ndim != 3 or pts.shape[1] < 2:
        return [[] for _ in range(int(pts.shape[0]) if pts.ndim >= 1 else 0)]
    names = link_names or [f'link_{i}' for i in range(pts.shape[1] - 1)]
    flags: list[list[tuple[str, str]]] = []
    for frame in pts:
        frame_pairs: list[tuple[str, str]] = []
        for i in range(frame.shape[0] - 1):
            arm_box = aabb_from_points(frame[i:i+2], padding=padding)
            for object_id, obstacle in obstacles:
                if arm_box.intersects(obstacle):
                    frame_pairs.append((str(names[i]), str(object_id)))
        flags.append(frame_pairs)
    return flags


def environment_collision_flags(points, obstacles: list[AABB], *, padding: float = 0.02) -> list[bool]:
>>>>>>> 3ed78e647985c6d680c085e4480d898855278db3
    pts = np.asarray(points, dtype=float)
    if pts.ndim != 3:
        return [False] * int(pts.shape[0])
    flags: list[bool] = []
    for frame in pts:
        arm_box = aabb_from_points(frame, padding=padding)
        flags.append(any(arm_box.intersects(ob) for ob in obstacles))
    return flags
<<<<<<< HEAD



def evaluate_environment_collision_pairs(
    frame_boxes: Iterable[AABB],
    *,
    obstacles: list[tuple[str, AABB]],
    link_names: list[str],
    allowed_collision_matrix=None,
) -> dict[str, object]:
    """Evaluate authoritative environment-collision semantics for one frame.

    Args:
        frame_boxes: Per-link AABBs for one frame.
        obstacles: Structured obstacle tuples ``(object_id, AABB)``.
        link_names: Canonical link-name labels.
        allowed_collision_matrix: Optional ACM used to suppress ignored pairs.

    Returns:
        dict[str, object]: Checked/ignored/accepted pair sets, clearance values, and the
        candidate pair count.

    Raises:
        None: Empty inputs simply produce an empty evaluation payload.
    """
    boxes = tuple(frame_boxes)
    ignored_pairs: set[tuple[str, str]] = set()
    checked_pairs: set[tuple[str, str]] = set()
    accepted_pairs: set[tuple[str, str]] = set()
    clearance_values: list[float] = []
    candidate_pair_count = 0
    for index, box_i in enumerate(boxes):
        link_name = str(link_names[index])
        for object_id, obstacle in obstacles:
            pair = (link_name, str(object_id))
            checked_pairs.add(pair)
            if allowed_collision_matrix is not None and allowed_collision_matrix.allows(*pair):
                ignored_pairs.add(pair)
                continue
            candidate_pair_count += 1
            clearance_values.append(box_i.distance(obstacle))
            if box_i.intersects(obstacle):
                accepted_pairs.add(pair)
    return {
        'ignored_pairs': ignored_pairs,
        'checked_pairs': checked_pairs,
        'accepted_pairs': accepted_pairs,
        'clearance_values': tuple(clearance_values),
        'candidate_pair_count': candidate_pair_count,
    }
=======
>>>>>>> 3ed78e647985c6d680c085e4480d898855278db3
