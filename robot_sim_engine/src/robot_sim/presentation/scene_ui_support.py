from __future__ import annotations

from collections.abc import Iterable

import numpy as np

from robot_sim.application.services.scene_authority_service import SceneAuthorityService

_SCENE_AUTHORITY_SERVICE = SceneAuthorityService()


def build_default_scene_obstacle_request(runtime_state) -> dict[str, object]:
    """Build the default stable scene-editor request from runtime state.

    Args:
        runtime_state: Session/runtime state carrying target pose, FK result, and planning scene.

    Returns:
        dict[str, object]: Default editor payload suitable for the structured scene editor.

    Raises:
        None: Missing runtime state falls back to bounded defaults.
    """
    target_pose = getattr(runtime_state, 'target_pose', None)
    fk_result = getattr(runtime_state, 'fk_result', None)
    scene = getattr(runtime_state, 'planning_scene', None)
    if target_pose is not None:
        center = np.asarray(getattr(target_pose, 'p', [0.3, 0.0, 0.2]), dtype=float)
    elif fk_result is not None:
        center = np.asarray(getattr(fk_result.ee_pose, 'p', [0.3, 0.0, 0.2]), dtype=float)
    else:
        center = np.asarray([0.3, 0.0, 0.2], dtype=float)
    default_id = 'obstacle'
    if scene is not None:
        default_id = _SCENE_AUTHORITY_SERVICE.next_object_id(scene, default_id)
    return {
        'object_id': default_id,
        'center': tuple(float(v) for v in center.tolist()),
        'size': (0.2, 0.2, 0.2),
        'replace_existing': False,
        'allowed_collision_pairs': tuple(getattr(scene, 'allowed_collision_pairs', ()) or ()),
        'clear_allowed_collision_pairs': False,
        'metadata': {},
    }


def format_vector(values: Iterable[float]) -> str:
    """Return a deterministic 3-vector editor string."""
    return ' '.join(f'{float(value):.3f}' for value in values)


def parse_vector_text(text: str, *, field_name: str) -> tuple[float, float, float]:
    """Parse one editor vector field into a strict xyz tuple.

    Args:
        text: User-entered vector string.
        field_name: Human-readable field identifier used in validation errors.

    Returns:
        tuple[float, float, float]: Parsed xyz tuple.

    Raises:
        ValueError: If the field does not contain exactly three finite numeric values.
    """
    pieces = [piece for piece in str(text).replace(',', ' ').split() if piece]
    if len(pieces) != 3:
        raise ValueError(f'scene obstacle {field_name} must contain exactly three numeric values')
    values = tuple(float(piece) for piece in pieces)
    array = np.asarray(values, dtype=float)
    if not np.isfinite(array).all():
        raise ValueError(f'scene obstacle {field_name} must contain only finite values')
    return float(array[0]), float(array[1]), float(array[2])


def format_allowed_collision_pairs(pairs: Iterable[tuple[str, str]]) -> str:
    """Render ACM pairs into the structured editor text area."""
    return '\n'.join(f'{a}, {b}' for a, b in pairs)


def parse_allowed_collision_pairs_text(text: str) -> tuple[tuple[str, str], ...]:
    """Parse the scene-editor ACM text area into normalized collision pairs.

    Args:
        text: Multiline editor text. Each non-empty line must contain exactly two ids.

    Returns:
        tuple[tuple[str, str], ...]: Normalized collision pairs.

    Raises:
        ValueError: If any non-empty line is malformed.
    """
    pairs: list[tuple[str, str]] = []
    for raw_line in str(text).splitlines():
        line = raw_line.strip()
        if not line:
            continue
        pieces = [piece.strip() for piece in line.replace('->', ',').replace(':', ',').split(',') if piece.strip()]
        if len(pieces) != 2:
            raise ValueError('allowed collision pairs must contain exactly two identifiers per line')
        a, b = pieces
        pairs.append((a, b) if a <= b else (b, a))
    return tuple(dict.fromkeys(pairs))
