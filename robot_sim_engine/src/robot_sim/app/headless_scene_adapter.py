from __future__ import annotations

from collections.abc import Mapping
from typing import Callable

from robot_sim.application.services.scene_authority_service import SceneAuthorityService, SceneObstacleEdit
from robot_sim.core.collision.scene import PlanningScene

ErrorFactory = Callable[[str], Exception] | type[Exception]

_SCENE_PAYLOAD_KEYS = (
    'planning_scene',
    'scene',
    'scene_snapshot',
    'scene_diff',
    'diff',
    'obstacles',
    'attached_objects',
    'scene_commands',
    'commands',
    'scene_command_history',
    'scene_command_log_tail',
    'allowed_collision_pairs',
    'clear_obstacles',
    'reset_obstacles',
    'clear_allowed_collision_pairs',
)

_CONTROL_SCENE_PAYLOAD_KEYS = frozenset({
    'clear_obstacles',
    'reset_obstacles',
    'clear_allowed_collision_pairs',
})


def _request_scene_value_is_present(key: str, value: object) -> bool:
    """Return whether a top-level headless scene field should trigger scene parsing.

    Args:
        key: Headless request field name.
        value: Raw field value.

    Returns:
        bool: ``True`` when the field is an executable scene payload.

    Raises:
        None: Pure normalization.

    Boundary behavior:
        Explicit ``False`` control flags are treated as absent so requests such as
        ``clear_obstacles: false`` remain legacy no-scene requests. ``True`` control flags still
        trigger deterministic scene handling.
    """
    if value in (None, ''):
        return False
    if isinstance(value, bool):
        return bool(value) if key in _CONTROL_SCENE_PAYLOAD_KEYS else bool(value)
    return True


def request_has_scene_payload(request: Mapping[str, object]) -> bool:
    """Return whether a headless request carries any scene payload.

    Args:
        request: Headless command request mapping.

    Returns:
        bool: ``True`` when the request contains full-scene, diff, command, or shorthand
        obstacle fields.

    Raises:
        None: Pure key inspection.

    Boundary behavior:
        Empty strings and ``None`` values are treated as absent so legacy headless requests keep
        using runtime-default scenes.
    """
    for key in _SCENE_PAYLOAD_KEYS:
        if key in request and _request_scene_value_is_present(key, request.get(key)):
            return True
    return False


def build_scene_payload_from_request(request: Mapping[str, object]) -> dict[str, object] | None:
    """Normalize scene-related headless request fields into one payload mapping.

    Args:
        request: Headless command request mapping.

    Returns:
        dict[str, object] | None: Unified scene payload, or ``None`` for legacy requests.

    Raises:
        None: Shape validation is intentionally deferred to ``build_planning_scene_from_payload``.

    Boundary behavior:
        ``planning_scene``/``scene`` may be either a full snapshot or a patch. Top-level shorthand
        fields are merged after the nested payload so explicit shorthand can refine a reusable
        snapshot without mutating unrelated request fields.
    """
    if not request_has_scene_payload(request):
        return None
    raw = request.get('planning_scene')
    if raw in (None, ''):
        raw = request.get('scene')
    if raw in (None, ''):
        raw = request.get('scene_snapshot')
    if isinstance(raw, Mapping):
        payload: dict[str, object] = {str(key): value for key, value in raw.items()}
    elif raw in (None, ''):
        payload = {}
    else:
        payload = {'obstacles': raw}
    for key in (
        'scene_diff',
        'diff',
        'obstacles',
        'attached_objects',
        'scene_commands',
        'commands',
        'scene_command_history',
        'scene_command_log_tail',
        'allowed_collision_pairs',
        'clear_obstacles',
        'reset_obstacles',
        'clear_allowed_collision_pairs',
    ):
        if key in request and _request_scene_value_is_present(key, request.get(key)):
            payload[key] = request[key]
    return payload


_EXECUTABLE_SCENE_KEYS = frozenset({
    'scene_commands',
    'commands',
    'scene_command_history',
    'scene_command_log_tail',
    'scene_diff',
    'diff',
    'obstacles',
    'attached_objects',
    'allowed_collision_pairs',
    'clear_obstacles',
    'reset_obstacles',
    'clear_allowed_collision_pairs',
})
_DIAGNOSTIC_SNAPSHOT_KEYS = frozenset({
    'obstacle_ids',
    'attached_object_ids',
    'obstacle_count',
    'attached_object_count',
    'revision',
    'collision_backend',
    'geometry_authority',
    'validation_projection',
    'validation_surface',
})


def _require_executable_scene_payload(payload: Mapping[str, object], *, error_factory: ErrorFactory) -> None:
    """Reject non-empty scene payloads that cannot mutate or replay scene truth.

    Args:
        payload: Normalized scene payload mapping.
        error_factory: Exception factory used by the headless API.

    Returns:
        None: The payload contains at least one supported executable scene field.

    Raises:
        Exception: A deterministic error from ``error_factory`` when the payload only contains
        diagnostic/export summary fields or unknown fields.

    Boundary behavior:
        Export summaries that only contain ``obstacle_ids`` are intentionally rejected because
        object identifiers alone cannot reconstruct geometry. Full snapshots must carry
        ``obstacles``/``attached_objects`` records or replayable ``scene_command_history``.
    """
    if not payload:
        _raise(error_factory, 'planning_scene payload must contain replayable scene fields')
    executable_present = any(
        key in payload and _scene_payload_value_is_executable(payload.get(key))
        for key in _EXECUTABLE_SCENE_KEYS
    )
    if executable_present:
        return
    if any(key in payload for key in _DIAGNOSTIC_SNAPSHOT_KEYS):
        _raise(
            error_factory,
            'planning_scene snapshot is not replayable: provide obstacles, attached_objects, scene_commands, or scene_command_history',
        )
    unknown = ', '.join(sorted(str(key) for key in payload))
    _raise(error_factory, f'planning_scene payload contains no supported scene fields: {unknown}')



def _scene_payload_value_is_executable(value: object) -> bool:
    if value in (None, ''):
        return False
    if isinstance(value, Mapping):
        return bool(value)
    if isinstance(value, (list, tuple, set)):
        return bool(value)
    if isinstance(value, bool):
        return bool(value)
    return True


def build_planning_scene_from_payload(
    payload: Mapping[str, object] | None,
    *,
    baseline_scene: PlanningScene | None,
    error_factory: ErrorFactory = ValueError,
    source: str = 'headless_payload',
    planner_id: str = '',
) -> PlanningScene | None:
    """Build a ``PlanningScene`` from a headless full/diff/shorthand payload.

    Args:
        payload: Full scene snapshot, scene diff, replay command list, or obstacle shorthand.
        baseline_scene: Runtime baseline scene used as the immutable replay base.
        error_factory: Exception type/factory used for deterministic request errors.
        source: Source label written into scene command metadata.
        planner_id: Optional planner id used when the scene is cloned for replay.

    Returns:
        PlanningScene | None: Caller scene truth. ``None`` means no explicit scene payload was
        supplied and the application façade should use its runtime-default fallback.

    Raises:
        Exception: An instance from ``error_factory`` if the scene payload is malformed or cannot
        be converted into stable scene-editor commands.

    Boundary behavior:
        The function supports three scene input forms without mutating the baseline scene:
        full snapshots with ``obstacles``/``attached_objects``, diffs with ``scene_commands`` or
        ``scene_diff.commands``, and shorthand top-level obstacle lists. Unsupported mesh or custom
        geometry records fail closed instead of fabricating approximate data.
    """
    if payload in (None, ''):
        return None
    if not isinstance(payload, Mapping):
        _raise(error_factory, 'planning_scene payload must be a mapping, obstacle list, or null')
    service = SceneAuthorityService()
    scene = service.ensure_scene(
        baseline_scene,
        scene_summary={} if baseline_scene is None else baseline_scene.summary(),
        authority=str(source or 'headless_payload'),
        edit_surface='headless_scene_payload',
    )
    payload_dict = {str(key): value for key, value in payload.items()}
    _require_executable_scene_payload(payload_dict, error_factory=error_factory)
    if bool(payload_dict.get('reset_obstacles', False)):
        scene = service.execute_clear_obstacles(scene, source=source).scene
    for command in _iter_scene_commands(payload_dict, error_factory=error_factory):
        try:
            scene = service.apply_scene_command(scene, command, source=source).scene
        except ValueError as exc:
            _raise(error_factory, f'invalid scene command: {exc}')
    diff_payload = payload_dict.get('scene_diff', payload_dict.get('diff'))
    if diff_payload not in (None, '') and not isinstance(diff_payload, Mapping):
        _raise(error_factory, 'scene_diff payload must be a mapping when provided')
    if isinstance(diff_payload, Mapping):
        if bool(diff_payload.get('clear_obstacles', False)):
            scene = service.execute_clear_obstacles(scene, source=source).scene
        for object_id in _iter_strings(diff_payload.get('remove_obstacles', ())):
            scene = scene.remove_obstacle(object_id)
        for command in _iter_sequence(diff_payload.get('commands', ())):
            if not isinstance(command, Mapping):
                _raise(error_factory, 'scene_diff.commands entries must be mappings')
            try:
                scene = service.apply_scene_command(scene, command, source=source).scene
            except ValueError as exc:
                _raise(error_factory, f'invalid scene diff command: {exc}')
        for item in _iter_sequence(diff_payload.get('obstacles', ())):
            edit = _edit_from_obstacle_payload(item, attached=False, error_factory=error_factory)
            scene = service.execute_obstacle_edit(scene, edit, source=source).scene
    if bool(payload_dict.get('clear_obstacles', False)):
        scene = service.execute_clear_obstacles(scene, source=source).scene
    for item in _iter_sequence(payload_dict.get('obstacles', ())):
        edit = _edit_from_obstacle_payload(item, attached=False, error_factory=error_factory)
        scene = service.execute_obstacle_edit(scene, edit, source=source).scene
    for item in _iter_sequence(payload_dict.get('attached_objects', ())):
        edit = _edit_from_obstacle_payload(item, attached=True, error_factory=error_factory)
        scene = service.execute_obstacle_edit(scene, edit, source=source).scene
    pairs = payload_dict.get('allowed_collision_pairs')
    clear_pairs = bool(payload_dict.get('clear_allowed_collision_pairs', False))
    if pairs not in (None, '') or clear_pairs:
        try:
            scene = service.apply_allowed_collision_pairs(
                scene,
                _normalize_allowed_collision_pairs(pairs, error_factory=error_factory),
                clear_existing=clear_pairs,
            )
        except ValueError as exc:
            _raise(error_factory, f'invalid allowed_collision_pairs: {exc}')
    metadata = {
        'scene_source': str(source or 'headless_payload'),
        'planning_scene_source': 'caller_scene',
        'scene_truth_layer': 'session_planning_scene',
        'headless_scene_payload_version': str(payload_dict.get('version', 'v1') or 'v1'),
    }
    if payload_dict.get('revision') not in (None, ''):
        metadata['source_scene_revision'] = int(payload_dict.get('revision') or 0)
    if planner_id:
        metadata['planner_id'] = str(planner_id)
    return scene.with_metadata_patch(**metadata)


def build_planning_scene_from_request(
    request: Mapping[str, object],
    *,
    baseline_scene: PlanningScene | None,
    error_factory: ErrorFactory = ValueError,
    source: str = 'headless_payload',
    planner_id: str = '',
) -> PlanningScene | None:
    """Build the optional caller scene for one headless command request.

    Args:
        request: Headless command payload.
        baseline_scene: Runtime baseline scene used when replaying full/diff scene payloads.
        error_factory: Exception type/factory used for validation failures.
        source: Source label for scene command metadata.
        planner_id: Optional planner id for diagnostics.

    Returns:
        PlanningScene | None: Explicit caller scene, or ``None`` for legacy no-scene requests.

    Raises:
        Exception: An instance from ``error_factory`` for malformed scene payloads.
    """
    payload = build_scene_payload_from_request(request)
    return build_planning_scene_from_payload(
        payload,
        baseline_scene=baseline_scene,
        error_factory=error_factory,
        source=source,
        planner_id=planner_id,
    )


def _iter_sequence(value: object) -> tuple[object, ...]:
    if value in (None, ''):
        return ()
    if isinstance(value, Mapping):
        return (value,)
    if isinstance(value, (list, tuple)):
        return tuple(value)
    return (value,)


def _iter_scene_commands(payload: Mapping[str, object], *, error_factory: ErrorFactory) -> tuple[Mapping[str, object], ...]:
    commands = (
        payload.get('scene_commands')
        or payload.get('commands')
        or payload.get('scene_command_history')
        or payload.get('scene_command_log_tail')
        or ()
    )
    normalized: list[Mapping[str, object]] = []
    for item in _iter_sequence(commands):
        if not isinstance(item, Mapping):
            _raise(error_factory, 'scene command entries must be mappings')
        normalized.append(item)
    return tuple(normalized)


def _iter_strings(value: object) -> tuple[str, ...]:
    return tuple(str(item) for item in _iter_sequence(value) if str(item or '').strip())


def _normalize_allowed_collision_pairs(value: object, *, error_factory: ErrorFactory) -> tuple[tuple[str, str], ...]:
    if value in (None, ''):
        return ()
    normalized: list[tuple[str, str]] = []
    for pair in _iter_sequence(value):
        if isinstance(pair, str):
            parts = [part.strip() for part in pair.replace('->', ',').replace(':', ',').split(',') if part.strip()]
        else:
            try:
                parts = [str(part).strip() for part in pair]  # type: ignore[operator]
            except TypeError:
                _raise(error_factory, 'allowed_collision_pairs entries must be two-item iterables or strings')
        if len(parts) != 2 or not parts[0] or not parts[1]:
            _raise(error_factory, 'allowed_collision_pairs entries must contain exactly two non-empty identifiers')
        a, b = parts
        normalized.append((a, b) if a <= b else (b, a))
    return tuple(dict.fromkeys(normalized))


def _edit_from_obstacle_payload(item: object, *, attached: bool, error_factory: ErrorFactory) -> SceneObstacleEdit:
    if not isinstance(item, Mapping):
        _raise(error_factory, 'scene obstacle entries must be mappings')
    payload = {str(key): value for key, value in item.items()}
    normalized: dict[str, object] = dict(payload)
    normalized.setdefault('object_id', payload.get('object_id', payload.get('id', payload.get('name', 'obstacle'))))
    normalized.setdefault('replace_existing', True)
    normalized.setdefault('attached', bool(attached or payload.get('attached', False) or payload.get('attach_link')))
    if normalized.get('shape') in (None, '') and payload.get('kind') not in (None, ''):
        normalized['shape'] = str(payload.get('kind') or '').strip().lower()
    if normalized.get('center') in (None, ''):
        center = _center_from_obstacle_payload(payload)
        if center not in (None, ''):
            normalized['center'] = center
    if normalized.get('size') in (None, '') and payload.get('dimensions') not in (None, ''):
        normalized['size'] = payload.get('dimensions')
    if normalized.get('height') in (None, '') and payload.get('length') not in (None, ''):
        normalized['height'] = payload.get('length')
    if normalized.get('center') in (None, '') or _shape_size_missing(normalized):
        geometry_payload = _geometry_payload_from_obstacle(payload, error_factory=error_factory)
        normalized.update(geometry_payload)
    try:
        return SceneObstacleEdit.from_mapping(normalized)
    except (TypeError, ValueError) as exc:
        _raise(error_factory, f'invalid scene obstacle {normalized.get("object_id", "")}: {exc}')


def _center_from_obstacle_payload(payload: Mapping[str, object]) -> object:
    center = payload.get('center')
    if center not in (None, ''):
        return center
    position = payload.get('position')
    if position not in (None, ''):
        return position
    pose = payload.get('pose')
    if isinstance(pose, Mapping):
        nested_position = pose.get('position', pose.get('p', pose.get('xyz')))
        if nested_position not in (None, ''):
            return nested_position
    return None


def _shape_size_missing(payload: Mapping[str, object]) -> bool:
    shape = str(payload.get('shape', payload.get('kind', 'box')) or 'box').strip().lower()
    if shape == 'box':
        return payload.get('size') in (None, '')
    if shape == 'sphere':
        return payload.get('radius') in (None, '')
    if shape == 'cylinder':
        return payload.get('radius') in (None, '') or payload.get('height') in (None, '')
    return False


def _geometry_payload_from_obstacle(payload: Mapping[str, object], *, error_factory: ErrorFactory) -> dict[str, object]:
    for key in ('declaration_geometry', 'render_geometry'):
        geometry = payload.get(key)
        if isinstance(geometry, Mapping):
            extracted = _primitive_geometry_payload(geometry)
            if extracted:
                return extracted
    for key in ('validation_query_geometry', 'validation_geometry'):
        geometry = payload.get(key)
        if isinstance(geometry, Mapping):
            extracted = _aabb_geometry_payload(geometry)
            if extracted:
                return extracted
    _raise(error_factory, 'scene obstacle is missing center/size or supported geometry payload')


def _primitive_geometry_payload(geometry: Mapping[str, object]) -> dict[str, object]:
    kind = str(geometry.get('shape', geometry.get('kind', 'box')) or 'box').strip().lower()
    center = _center_from_obstacle_payload(geometry)
    if center in (None, ''):
        return {}
    size = geometry.get('size', geometry.get('dimensions'))
    if size not in (None, ''):
        return {'shape': kind, 'center': center, 'size': size}
    if kind == 'sphere' and geometry.get('radius') not in (None, ''):
        return {'shape': 'sphere', 'center': center, 'radius': float(geometry.get('radius') or 0.0)}
    height = geometry.get('height', geometry.get('length'))
    if kind == 'cylinder' and geometry.get('radius') not in (None, '') and height not in (None, ''):
        return {'shape': 'cylinder', 'center': center, 'radius': float(geometry.get('radius') or 0.0), 'height': float(height or 0.0)}
    return {}


def _aabb_geometry_payload(geometry: Mapping[str, object]) -> dict[str, object]:
    minimum = geometry.get('minimum')
    maximum = geometry.get('maximum')
    if minimum in (None, '') or maximum in (None, ''):
        return {}
    try:
        min_values = [float(value) for value in minimum]  # type: ignore[arg-type]
        max_values = [float(value) for value in maximum]  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return {}
    if len(min_values) != 3 or len(max_values) != 3:
        return {}
    center = [(lo + hi) * 0.5 for lo, hi in zip(min_values, max_values)]
    size = [hi - lo for lo, hi in zip(min_values, max_values)]
    return {'shape': 'box', 'center': center, 'size': size}


def _raise(error_factory: ErrorFactory, message: str) -> None:
    raise error_factory(message)
