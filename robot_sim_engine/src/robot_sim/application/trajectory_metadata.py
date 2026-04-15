from __future__ import annotations

from robot_sim.application.planner_capabilities import planner_descriptor_for_id
from robot_sim.domain.enums import PlannerFamily

_CANONICAL_CACHE_STATUSES = {'none', 'partial', 'ready', 'recomputed'}


def infer_planner_family(planner_id: str, goal_source: str = '') -> str:
    planner_key = str(planner_id or '').strip().lower()
    goal_key = str(goal_source or '').strip().lower()
    if planner_key == 'waypoint_graph' or goal_key == 'waypoint_graph':
        return PlannerFamily.WAYPOINT_GRAPH.value
    if 'cartesian' in planner_key or goal_key in {'cartesian_pose', 'cartesian'}:
        return PlannerFamily.CARTESIAN.value
    return PlannerFamily.JOINT.value


def normalize_cache_status(cache_status: object, *, has_complete_fk: bool = False, has_partial_fk: bool = False) -> str:
    value = str(cache_status or '').strip().lower()
    if has_complete_fk:
        return 'recomputed' if value == 'recomputed' else 'ready'
    if has_partial_fk:
        return 'partial'
    if value in _CANONICAL_CACHE_STATUSES:
        return 'none' if value in {'ready', 'partial', 'recomputed'} else value
    return 'none'


def _descriptor_metadata(planner_id: str) -> dict[str, object]:
    descriptor = planner_descriptor_for_id(planner_id)
    return {} if descriptor is None else descriptor.as_metadata()


def resolve_planner_metadata(metadata: dict[str, object] | None = None) -> dict[str, object]:
    payload = dict(metadata or {})
    planner_id = str(payload.get('planner_id', payload.get('planner_type', payload.get('mode', 'unknown'))) or 'unknown')
    descriptor_metadata = _descriptor_metadata(planner_id)
    goal_source = str(payload.get('goal_source', descriptor_metadata.get('goal_source', payload.get('mode', 'unknown'))) or 'unknown')
    planner_family = str(payload.get('planner_family', descriptor_metadata.get('family', infer_planner_family(planner_id, goal_source))) or infer_planner_family(planner_id, goal_source))
    resolved = {
        'planner_id': planner_id,
        'planner_family': planner_family,
        'goal_source': goal_source,
        'cache_status': normalize_cache_status(payload.get('cache_status', 'none')),
        'scene_revision': str(payload.get('scene_revision', '0') or '0'),
        'validation_stage': str(payload.get('validation_stage', '') or ''),
        'correlation_id': str(payload.get('correlation_id', '') or ''),
    }
    resolved.update({key: value for key, value in descriptor_metadata.items() if key not in resolved})
    return resolved


def build_planner_metadata(*, planner_id: str, goal_source: str, cache_status: object = 'none', mode: str | None = None, metadata: dict[str, object] | None = None, scene_revision: int | None = None, validation_stage: str | None = None, correlation_id: str | None = None, has_complete_fk: bool = False, has_partial_fk: bool = False) -> dict[str, object]:
    payload = dict(metadata or {})
    canonical_planner_id = str(planner_id)
    canonical_goal_source = str(goal_source)
    descriptor_metadata = _descriptor_metadata(canonical_planner_id)
    canonical_family = str(descriptor_metadata.get('family', infer_planner_family(canonical_planner_id, canonical_goal_source)))
    payload['planner_id'] = canonical_planner_id
    payload['planner_type'] = canonical_planner_id
    payload['planner_family'] = canonical_family
    payload['goal_source'] = canonical_goal_source
    payload['cache_status'] = normalize_cache_status(payload.get('cache_status', cache_status), has_complete_fk=has_complete_fk, has_partial_fk=has_partial_fk)
    payload['correlation_id'] = str(correlation_id or payload.get('correlation_id', '') or '')
    for key, value in descriptor_metadata.items():
        payload.setdefault(key, value)
    if mode is not None and str(mode):
        payload.setdefault('mode', str(mode))
    if scene_revision is not None:
        payload['scene_revision'] = int(scene_revision)
    if validation_stage is not None and str(validation_stage):
        payload['validation_stage'] = str(validation_stage)
    return payload
