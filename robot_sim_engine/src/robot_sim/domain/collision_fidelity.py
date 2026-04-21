from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from importlib.resources import files as resource_files
import os
from pathlib import Path
from typing import Mapping

import yaml

from robot_sim.domain.collision_backends import default_collision_backend_registry
from robot_sim.domain.enums import CollisionLevel


@dataclass(frozen=True)
class CollisionFidelityDescriptor:
    collision_level: str
    precision: str
    stable_surface: bool
    promotion_state: str
    summary: str
    roadmap_stage: str = ''
    stable_surface_target: str = ''
    geometry_requirements: tuple[str, ...] = ()
    degradation_policy: str = ''
    contract_version: str = 'v1'


_DEFAULT_POLICY: dict[str, object] = {
    'contract_version': 'v2',
    'roadmap_owner': 'architecture',
    'levels': {
        'none': {
            'collision_level': 'none',
            'precision': 'none',
            'stable_surface': False,
            'promotion_state': 'disabled',
            'summary': 'collision checking disabled',
            'roadmap_stage': 'disabled',
            'stable_surface_target': 'none',
            'geometry_requirements': [],
            'degradation_policy': 'no_collision_queries',
        },
        'aabb': {
            'collision_level': 'aabb',
            'precision': 'broad_phase',
            'stable_surface': True,
            'promotion_state': 'stable',
            'summary': 'AABB broad-phase validation',
            'roadmap_stage': 'stable',
            'stable_surface_target': 'stable',
            'geometry_requirements': ['declaration_projection', 'query_aabb'],
            'degradation_policy': 'native_broad_phase',
        },
        'capsule': {
            'collision_level': 'capsule',
            'precision': 'capsule_narrow_phase',
            'stable_surface': True,
            'promotion_state': 'stable',
            'summary': 'Capsule narrow-phase validation',
            'roadmap_stage': 'stable',
            'stable_surface_target': 'stable',
            'geometry_requirements': ['capsule_primitives', 'link_radii'],
            'degradation_policy': 'fallback_to_aabb_when_capsule_contract_missing',
        },
        'mesh': {
            'collision_level': 'mesh',
            'precision': 'mesh_exact',
            'stable_surface': False,
            'promotion_state': 'planned',
            'summary': 'mesh-level validation',
            'roadmap_stage': 'planned',
            'stable_surface_target': 'mesh_backend_after_exact_contact_validation',
            'geometry_requirements': ['mesh_assets', 'exact_contact_backend'],
            'degradation_policy': 'fallback_to_capsule_or_aabb',
        },
    },
}


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _filesystem_policy_candidates() -> tuple[Path, ...]:
    repo_root = _repo_root()
    candidates: list[Path] = []

    env_override = str(os.environ.get('ROBOT_SIM_COLLISION_FIDELITY_CONFIG', '') or '').strip()
    if env_override:
        candidates.append(Path(env_override).expanduser())

    candidates.append(repo_root / 'configs' / 'collision_fidelity.yaml')
    candidates.append(repo_root / 'build' / 'packaged_config_staging' / 'robot_sim' / 'resources' / 'configs' / 'collision_fidelity.yaml')

    deduped: list[Path] = []
    seen: set[str] = set()
    for path in candidates:
        key = str(path.resolve(strict=False))
        if key in seen:
            continue
        seen.add(key)
        deduped.append(path)
    return tuple(deduped)


def _policy_source_label(raw_source: str) -> str:
    source = str(raw_source or '').strip()
    if not source or source == 'builtin_default':
        return 'builtin_default'
    if source == 'package:robot_sim.resources/configs/collision_fidelity.yaml':
        return 'package_resource'

    env_override = str(os.environ.get('ROBOT_SIM_COLLISION_FIDELITY_CONFIG', '') or '').strip()
    if env_override:
        try:
            if Path(source).resolve(strict=False) == Path(env_override).expanduser().resolve(strict=False):
                return 'env_override'
        except OSError:
            return 'env_override'

    repo_root = _repo_root()
    known_candidates = {
        str((repo_root / 'configs' / 'collision_fidelity.yaml').resolve(strict=False)): 'repo_config',
        str((repo_root / 'build' / 'packaged_config_staging' / 'robot_sim' / 'resources' / 'configs' / 'collision_fidelity.yaml').resolve(strict=False)): 'packaged_staging_config',
    }
    normalized = str(Path(source).resolve(strict=False))
    return known_candidates.get(normalized, 'filesystem_config')


def _sanitize_policy_load_errors(load_errors: list[str]) -> list[str]:
    sanitized: list[str] = []
    env_override = str(os.environ.get('ROBOT_SIM_COLLISION_FIDELITY_CONFIG', '') or '').strip()
    env_override_path = Path(env_override).expanduser().resolve(strict=False) if env_override else None
    repo_root = _repo_root()
    known_candidates = {
        str((repo_root / 'configs' / 'collision_fidelity.yaml').resolve(strict=False)): 'repo_config',
        str((repo_root / 'build' / 'packaged_config_staging' / 'robot_sim' / 'resources' / 'configs' / 'collision_fidelity.yaml').resolve(strict=False)): 'packaged_staging_config',
    }
    for item in load_errors:
        entry = str(item or '').strip()
        if not entry:
            continue
        if entry.startswith('missing:package:'):
            sanitized.append('missing:package_resource')
            continue
        if entry.startswith('invalid:package:'):
            parts = entry.split(':')
            exc_name = parts[-1] if len(parts) >= 4 else 'UnknownError'
            sanitized.append(f'invalid:package_resource:{exc_name}')
            continue
        if entry.startswith('invalid_mapping:'):
            raw_path = entry.partition(':')[2]
            label = 'filesystem_config'
            try:
                resolved = str(Path(raw_path).resolve(strict=False))
                if env_override_path is not None and resolved == str(env_override_path):
                    label = 'env_override'
                else:
                    label = known_candidates.get(resolved, 'filesystem_config')
            except OSError:
                label = 'filesystem_config'
            sanitized.append(f'invalid_mapping:{label}')
            continue
        parts = entry.split(':', 2)
        kind = parts[0] if parts else 'unknown'
        raw_path = parts[1] if len(parts) > 1 else ''
        suffix = parts[2] if len(parts) > 2 else ''
        label = 'filesystem_config'
        try:
            resolved = str(Path(raw_path).resolve(strict=False)) if raw_path else ''
            if env_override_path is not None and resolved == str(env_override_path):
                label = 'env_override'
            else:
                label = known_candidates.get(resolved, 'filesystem_config') if resolved else 'filesystem_config'
        except OSError:
            label = 'filesystem_config'
        sanitized.append(f'{kind}:{label}' + (f':{suffix}' if suffix else ''))
    return sanitized


def _load_policy_mapping(raw: object, *, source: str, load_errors: list[str]) -> dict[str, object] | None:
    if not isinstance(raw, Mapping):
        load_errors.append(f'invalid_mapping:{source}')
        return None
    return {
        'contract_version': str(raw.get('contract_version', _DEFAULT_POLICY.get('contract_version', 'v1')) or _DEFAULT_POLICY.get('contract_version', 'v1')),
        'roadmap_owner': str(raw.get('roadmap_owner', _DEFAULT_POLICY.get('roadmap_owner', 'architecture')) or _DEFAULT_POLICY.get('roadmap_owner', 'architecture')),
        'levels': dict(raw.get('levels', _DEFAULT_POLICY.get('levels', {})) or _DEFAULT_POLICY.get('levels', {})),
        'policy_source': source,
        'policy_source_label': _policy_source_label(source),
        'policy_load_errors': list(load_errors),
        'policy_load_error_labels': _sanitize_policy_load_errors(load_errors),
    }


@lru_cache(maxsize=1)
def collision_fidelity_policy() -> dict[str, object]:
    """Load the collision-fidelity roadmap from source checkout or packaged resources.

    Returns:
        dict[str, object]: Normalized policy mapping keyed by collision level.

    Boundary behavior:
        Missing or malformed external policy files degrade to checked-in defaults instead of
        failing runtime startup. The returned payload includes diagnostic fields describing the
        discovered source and any load errors encountered while probing source/staged/package roots.
    """
    payload = dict(_DEFAULT_POLICY)
    payload['policy_source'] = 'builtin_default'
    payload['policy_source_label'] = 'builtin_default'
    load_errors: list[str] = []

    for candidate in _filesystem_policy_candidates():
        if not candidate.exists():
            load_errors.append(f'missing:{candidate}')
            continue
        try:
            raw = yaml.safe_load(candidate.read_text(encoding='utf-8')) or {}
        except (OSError, UnicodeDecodeError, yaml.YAMLError) as exc:
            load_errors.append(f'invalid:{candidate}:{type(exc).__name__}')
            continue
        normalized = _load_policy_mapping(raw, source=str(candidate), load_errors=load_errors)
        if normalized is not None:
            return normalized

    try:
        packaged_resource = resource_files('robot_sim.resources').joinpath('configs').joinpath('collision_fidelity.yaml')
    except ModuleNotFoundError:
        packaged_resource = None
    if packaged_resource is not None and packaged_resource.is_file():
        try:
            raw = yaml.safe_load(packaged_resource.read_text(encoding='utf-8')) or {}
        except (OSError, UnicodeDecodeError, yaml.YAMLError) as exc:
            load_errors.append(f'invalid:package:robot_sim.resources/configs/collision_fidelity.yaml:{type(exc).__name__}')
        else:
            normalized = _load_policy_mapping(
                raw,
                source='package:robot_sim.resources/configs/collision_fidelity.yaml',
                load_errors=load_errors,
            )
            if normalized is not None:
                return normalized
    else:
        load_errors.append('missing:package:robot_sim.resources/configs/collision_fidelity.yaml')

    payload['policy_load_errors'] = list(load_errors)
    payload['policy_load_error_labels'] = _sanitize_policy_load_errors(load_errors)
    return payload


@lru_cache(maxsize=None)
def _descriptor_table() -> dict[str, CollisionFidelityDescriptor]:
    policy = collision_fidelity_policy()
    levels = dict(policy.get('levels', {}) or {})
    contract_version = str(policy.get('contract_version', 'v1') or 'v1')
    table: dict[str, CollisionFidelityDescriptor] = {}
    for level, raw_payload in levels.items():
        payload = dict(raw_payload) if isinstance(raw_payload, Mapping) else {}
        normalized = str(payload.get('collision_level', level) or level).strip().lower()
        table[normalized] = CollisionFidelityDescriptor(
            collision_level=normalized,
            precision=str(payload.get('precision', 'none') or 'none'),
            stable_surface=bool(payload.get('stable_surface', False)),
            promotion_state=str(payload.get('promotion_state', 'disabled') or 'disabled'),
            summary=str(payload.get('summary', '') or ''),
            roadmap_stage=str(payload.get('roadmap_stage', payload.get('promotion_state', '')) or payload.get('promotion_state', '')),
            stable_surface_target=str(payload.get('stable_surface_target', '') or ''),
            geometry_requirements=tuple(str(item) for item in payload.get('geometry_requirements', ()) or ()),
            degradation_policy=str(payload.get('degradation_policy', '') or ''),
            contract_version=contract_version,
        )
    if CollisionLevel.NONE.value not in table:
        table[CollisionLevel.NONE.value] = CollisionFidelityDescriptor(
            collision_level=CollisionLevel.NONE.value,
            precision='none',
            stable_surface=False,
            promotion_state='disabled',
            summary='collision checking disabled',
            roadmap_stage='disabled',
            stable_surface_target='none',
            geometry_requirements=(),
            degradation_policy='no_collision_queries',
            contract_version=contract_version,
        )
    return table


def collision_fidelity_descriptor(collision_level: str | CollisionLevel | None) -> CollisionFidelityDescriptor:
    """Return the normalized descriptor for a collision-fidelity level.

    Args:
        collision_level: Requested fidelity level identifier or enum.

    Returns:
        CollisionFidelityDescriptor: Stable descriptor for the requested level.

    Raises:
        None: Unknown levels degrade to the ``none`` descriptor.
    """
    normalized = getattr(collision_level, 'value', collision_level)
    normalized = str(normalized or CollisionLevel.NONE.value).strip().lower() or CollisionLevel.NONE.value
    table = _descriptor_table()
    return table.get(normalized, table[CollisionLevel.NONE.value])



def summarize_collision_fidelity(*, collision_level: str | CollisionLevel | None, collision_backend: str, scene_fidelity: str, experimental_backends_enabled: bool | None = None) -> dict[str, object]:
    """Project the configured collision-fidelity contract into a user-facing summary.

    Args:
        collision_level: Requested fidelity level.
        collision_backend: Resolved collision backend identifier.
        scene_fidelity: Scene fidelity label exposed by the planning-scene runtime.
        experimental_backends_enabled: Optional backend-profile flag.

    Returns:
        dict[str, object]: Structured fidelity summary used by diagnostics/export/session surfaces.

    Raises:
        None: Missing backend descriptors degrade to unknown availability metadata.
    """
    descriptor = collision_fidelity_descriptor(collision_level)
    policy = collision_fidelity_policy()
    registry = default_collision_backend_registry()
    backend_id = str(collision_backend or registry.default_backend).strip().lower() or registry.default_backend
    backend_descriptor = next((item for item in registry.descriptors() if item.backend_id == backend_id), None)
    experimental_enabled = bool(experimental_backends_enabled) if experimental_backends_enabled is not None else True
    availability = 'unknown'
    backend_status = 'unknown'
    backend_family = ''
    supported_levels: list[str] = []
    if backend_descriptor is not None:
        availability = backend_descriptor.availability(experimental_enabled=experimental_enabled)
        backend_status = backend_descriptor.status.value
        backend_family = str(backend_descriptor.metadata.get('family', '') or '')
        supported_levels = [str(item) for item in backend_descriptor.metadata.get('supported_collision_levels', ())]
    stable_surface = bool(descriptor.stable_surface and availability == 'enabled')
    return {
        'collision_level': descriptor.collision_level,
        'collision_backend': backend_id,
        'precision': descriptor.precision,
        'stable_surface': stable_surface,
        'promotion_state': descriptor.promotion_state,
        'summary': descriptor.summary,
        'backend_status': backend_status,
        'backend_availability': availability,
        'backend_family': backend_family,
        'supported_collision_levels': supported_levels,
        'scene_fidelity': str(scene_fidelity or ''),
        'roadmap_stage': descriptor.roadmap_stage,
        'stable_surface_target': descriptor.stable_surface_target,
        'geometry_requirements': list(descriptor.geometry_requirements),
        'degradation_policy': descriptor.degradation_policy,
        'capability_contract_version': descriptor.contract_version,
        'roadmap_owner': str(policy.get('roadmap_owner', 'architecture') or 'architecture'),
        'policy_source': str(policy.get('policy_source_label', policy.get('policy_source', 'builtin_default')) or 'builtin_default'),
        'policy_load_errors': [str(item) for item in policy.get('policy_load_error_labels', ()) or ()],
    }



def validation_backend_capability_matrix(*, experimental_enabled: bool) -> list[dict[str, object]]:
    """Return per-backend fidelity capability rows for capability-matrix rendering.

    Args:
        experimental_enabled: Whether experimental backends should be advertised as enabled.

    Returns:
        list[dict[str, object]]: Canonical capability rows keyed by backend.

    Raises:
        None: Unsupported mappings are filtered out of the rendered matrix.
    """
    registry = default_collision_backend_registry()
    matrix: list[dict[str, object]] = []
    for descriptor in registry.descriptors():
        backend_id = str(descriptor.backend_id)
        fidelity_rows = [
            summarize_collision_fidelity(
                collision_level=collision_level,
                collision_backend=backend_id,
                scene_fidelity='planning_scene',
                experimental_backends_enabled=experimental_enabled,
            )
            for collision_level in descriptor.metadata.get('supported_collision_levels', ())
        ]
        if not fidelity_rows:
            continue
        matrix.append(
            {
                'backend_id': backend_id,
                'family': str(descriptor.metadata.get('family', '') or ''),
                'status': descriptor.status.value,
                'availability': descriptor.availability(experimental_enabled=experimental_enabled),
                'is_default': backend_id == registry.default_backend,
                'is_experimental': bool(descriptor.is_experimental),
                'supported_collision_levels': [str(item) for item in descriptor.metadata.get('supported_collision_levels', ())],
                'fidelity_rows': fidelity_rows,
                'roadmap_stage': fidelity_rows[0].get('roadmap_stage', ''),
            }
        )
    return matrix
