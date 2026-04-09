from __future__ import annotations

from collections.abc import Iterable

import numpy as np

SUPPORTED_SCENE_SHAPES = {'box', 'sphere', 'cylinder'}


def coerce_int(value: object) -> int:
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, (int, float, str)):
        return int(value or 0)
    return 0


def normalize_vector(value, *, field_name: str) -> tuple[float, float, float]:
    try:
        array = np.asarray(value, dtype=float).reshape(3)
    except (TypeError, ValueError) as exc:  # pragma: no cover - defensive normalization path
        raise ValueError(f'scene obstacle {field_name} must contain exactly three numeric values') from exc
    if not np.isfinite(array).all():
        raise ValueError(f'scene obstacle {field_name} must contain only finite values')
    x, y, z = array.tolist()
    return float(x), float(y), float(z)


def coerce_positive_scalar(value: object, *, field_name: str) -> float:
    try:
        scalar = float(value)
    except (TypeError, ValueError) as exc:  # pragma: no cover - defensive normalization path
        raise ValueError(f'scene obstacle {field_name} must be numeric') from exc
    if not np.isfinite(scalar) or scalar <= 0.0:
        raise ValueError(f'scene obstacle {field_name} must be finite and strictly positive')
    return scalar


def normalize_shape_size(*, shape: str, size_payload: object, radius_payload: object, height_payload: object) -> tuple[float, float, float]:
    normalized_shape = str(shape or 'box').strip().lower() or 'box'
    if normalized_shape not in SUPPORTED_SCENE_SHAPES:
        raise ValueError(f'unsupported scene obstacle shape: {normalized_shape}')
    if normalized_shape == 'box':
        size = normalize_vector(size_payload, field_name='size')
    elif normalized_shape == 'sphere':
        radius = coerce_positive_scalar(radius_payload, field_name='radius')
        diameter = radius * 2.0
        size = (diameter, diameter, diameter)
    else:
        radius = coerce_positive_scalar(radius_payload, field_name='radius')
        height = coerce_positive_scalar(height_payload, field_name='height')
        diameter = radius * 2.0
        size = (diameter, diameter, height)
    if any(value <= 0.0 for value in size):
        raise ValueError('scene obstacle size must be strictly positive')
    return tuple(float(value) for value in size)


def normalize_collision_pairs(value: object) -> tuple[tuple[str, str], ...]:
    if value in (None, '', ()):
        return ()
    normalized: list[tuple[str, str]] = []
    if not isinstance(value, Iterable):
        raise ValueError('scene allowed collision pairs must be iterable two-item entries')
    for item in value:
        if isinstance(item, str):
            pieces = [piece.strip() for piece in item.replace('->', ',').replace(':', ',').split(',') if piece.strip()]
        else:
            try:
                pieces = [str(piece).strip() for piece in item]
            except TypeError as exc:  # pragma: no cover - defensive normalization path
                raise ValueError('scene allowed collision pairs must be iterable two-item entries') from exc
        if len(pieces) != 2 or not pieces[0] or not pieces[1]:
            raise ValueError('scene allowed collision pairs must contain exactly two non-empty identifiers')
        a, b = pieces
        normalized.append((a, b) if a <= b else (b, a))
    return tuple(dict.fromkeys(normalized))
