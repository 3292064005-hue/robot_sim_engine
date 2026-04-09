from __future__ import annotations

from typing import Iterable

import numpy as np

from robot_sim.core.collision.aabb import broad_phase_intersections
from robot_sim.core.collision.geometry import AABB, aabb_from_points


def normalize_link_names(link_count: int, link_names: list[str] | None = None) -> list[str]:
    """Return canonical link names for a link-chain collision evaluation."""
    if link_names is not None:
        return [str(name) for name in link_names]
    return [f'link_{index}' for index in range(max(int(link_count), 0))]



def self_collision_pair_specs(
    link_names: list[str],
    *,
    ignore_adjacent: bool = True,
) -> tuple[tuple[int, int, tuple[str, str]], ...]:
    """Return canonical self-collision pair descriptors for a link chain.

    Args:
        link_names: Canonical link-name labels.
        ignore_adjacent: Whether adjacent links are excluded from self checks.

    Returns:
        tuple[tuple[int, int, tuple[str, str]], ...]: Pair descriptors including link indices
        plus the normalized pair label.

    Raises:
        None: Empty link chains simply produce an empty pair set.
    """
    pairs: list[tuple[int, int, tuple[str, str]]] = []
    for i in range(len(link_names)):
        for j in range(i + 1, len(link_names)):
            if ignore_adjacent and abs(i - j) <= 1:
                continue
            pairs.append((i, j, (str(link_names[i]), str(link_names[j]))))
    return tuple(pairs)



def self_collision_pair_hits(
    joint_positions,
    *,
    link_padding: float = 0.03,
    ignore_adjacent: bool = True,
    link_names: list[str] | None = None,
) -> tuple[frozenset[tuple[str, str]], ...]:
    """Return canonical per-frame self-collision hit pairs.

    Args:
        joint_positions: Per-frame joint positions.
        link_padding: AABB padding applied to each link segment.
        ignore_adjacent: Whether adjacent links are excluded from the hit set.
        link_names: Optional canonical link names.

    Returns:
        tuple[frozenset[tuple[str, str]], ...]: Per-frame hit-pair sets.

    Raises:
        None: Invalid shapes are normalized into empty per-frame results.
    """
    joint_positions = np.asarray(joint_positions, dtype=float)
    if joint_positions.ndim != 3 or joint_positions.shape[1] < 2:
        return tuple(frozenset() for _ in range(int(joint_positions.shape[0]) if joint_positions.ndim >= 1 else 0))
    names = normalize_link_names(joint_positions.shape[1] - 1, link_names)
    all_pairs: list[frozenset[tuple[str, str]]] = []
    for frame in joint_positions:
        aabbs = [aabb_from_points(frame[i:i + 2], padding=link_padding) for i in range(frame.shape[0] - 1)]
        pairs_idx = broad_phase_intersections(aabbs)
        if ignore_adjacent:
            pairs_idx = [(i, j) for i, j in pairs_idx if abs(i - j) > 1]
        frame_pairs = frozenset((str(names[i]), str(names[j])) for i, j in pairs_idx)
        all_pairs.append(frame_pairs)
    return tuple(all_pairs)



def self_collision_pairs(joint_positions, *, link_padding: float = 0.03, ignore_adjacent: bool = True, link_names: list[str] | None = None) -> list[list[tuple[str, str]]]:
    """Return self-collision pairs for each trajectory frame."""
    return [sorted(frame_pairs) for frame_pairs in self_collision_pair_hits(joint_positions, link_padding=link_padding, ignore_adjacent=ignore_adjacent, link_names=link_names)]



def self_collision_flags(joint_positions, *, link_padding: float = 0.03, ignore_adjacent: bool = True) -> list[bool]:
    """Return self-collision flags for each trajectory frame."""
    return [bool(pairs) for pairs in self_collision_pair_hits(joint_positions, link_padding=link_padding, ignore_adjacent=ignore_adjacent)]



def evaluate_self_collision_pairs(
    frame_boxes: Iterable[AABB],
    *,
    pair_specs: tuple[tuple[int, int, tuple[str, str]], ...],
    seen_pairs: frozenset[tuple[str, str]],
    allowed_collision_matrix=None,
) -> dict[str, object]:
    """Evaluate authoritative self-collision pair semantics for one frame.

    Args:
        frame_boxes: Per-link AABBs for one frame.
        pair_specs: Canonical pair descriptors from :func:`self_collision_pair_specs`.
        seen_pairs: Broad-phase hit pairs for the frame.
        allowed_collision_matrix: Optional ACM used to suppress ignored pairs.

    Returns:
        dict[str, object]: Checked/ignored/accepted pair sets, clearance values, and the
        candidate pair count.

    Raises:
        None: Empty pair specs simply produce an empty evaluation payload.
    """
    boxes = tuple(frame_boxes)
    ignored_pairs: set[tuple[str, str]] = set()
    checked_pairs: set[tuple[str, str]] = set()
    accepted_pairs: set[tuple[str, str]] = set()
    clearance_values: list[float] = []
    candidate_pair_count = 0
    for i, j, pair in pair_specs:
        checked_pairs.add(pair)
        if allowed_collision_matrix is not None and allowed_collision_matrix.allows(*pair):
            ignored_pairs.add(pair)
            continue
        candidate_pair_count += 1
        clearance_values.append(boxes[i].distance(boxes[j]))
        if pair in seen_pairs:
            accepted_pairs.add(pair)
    return {
        'ignored_pairs': ignored_pairs,
        'checked_pairs': checked_pairs,
        'accepted_pairs': accepted_pairs,
        'clearance_values': tuple(clearance_values),
        'candidate_pair_count': candidate_pair_count,
    }
