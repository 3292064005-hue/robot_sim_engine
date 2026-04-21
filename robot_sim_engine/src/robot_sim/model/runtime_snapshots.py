from __future__ import annotations

from collections.abc import Iterator, Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


class MappingSnapshot(Mapping[str, object]):
    """Immutable mapping-style snapshot base used by runtime/bootstrap contracts.

    The runtime previously passed nested ``dict`` payloads across bootstrap, export, and
    presentation layers. The new snapshot surfaces remain mapping-compatible for existing
    call sites while giving startup code one typed contract entrypoint.
    """

    def as_dict(self) -> dict[str, object]:
        raise NotImplementedError

    def __getitem__(self, key: str) -> object:
        return self.as_dict()[key]

    def __iter__(self) -> Iterator[str]:
        return iter(self.as_dict())

    def __len__(self) -> int:
        return len(self.as_dict())

    def get(self, key: str, default: object = None) -> object:
        return self.as_dict().get(key, default)


@dataclass(frozen=True)
class PluginCatalogSnapshot(MappingSnapshot):
    """Split plugin governance audit from runtime capability registrations.

    Attributes:
        governance_entries: All manifest/audit rows allowed to participate in governance.
        capability_entries: Only rows that contribute runtime capability providers.
        scene_backend_runtime_plugins: Installed scene runtime provider ids.
        collision_backend_runtime_plugins: Installed collision runtime provider ids.
    """

    governance_entries: tuple[dict[str, object], ...] = ()
    capability_entries: tuple[dict[str, object], ...] = ()
    scene_backend_runtime_plugins: tuple[str, ...] = ()
    collision_backend_runtime_plugins: tuple[str, ...] = ()

    def counts(self) -> dict[str, int]:
        governance_total = len(self.governance_entries)
        governance_enabled = sum(1 for row in self.governance_entries if bool(row.get('enabled', False)))
        capability_total = len(self.capability_entries)
        capability_enabled = sum(1 for row in self.capability_entries if bool(row.get('enabled', False)))
        return {
            'total': governance_total,
            'enabled': governance_enabled,
            'disabled': governance_total - governance_enabled,
            'capability_total': capability_total,
            'capability_enabled': capability_enabled,
            'capability_disabled': capability_total - capability_enabled,
        }

    def as_dict(self) -> dict[str, object]:
        return {
            'entries': [dict(item) for item in self.governance_entries],
            'governance_entries': [dict(item) for item in self.governance_entries],
            'capability_entries': [dict(item) for item in self.capability_entries],
            'scene_backend_runtime_plugins': list(self.scene_backend_runtime_plugins),
            'collision_backend_runtime_plugins': list(self.collision_backend_runtime_plugins),
            'counts': self.counts(),
        }


@dataclass(frozen=True)
class RuntimeContextSnapshot(MappingSnapshot):
    project_root: str
    resource_root: str
    config_root: str
    robot_root: str
    bundled_robot_root: str
    profiles_root: str
    plugin_manifest_path: str
    plugin_manifest_paths: tuple[str, ...]
    export_root: str
    layout_mode: str
    runtime_feature_policy: dict[str, object] = field(default_factory=dict)
    profiles: tuple[str, ...] = ()
    plugin_discovery_enabled: bool = False
    plugin_catalog: PluginCatalogSnapshot = field(default_factory=PluginCatalogSnapshot)
    source_layout_available: bool = False
    config_resolution: dict[str, object] = field(default_factory=dict)
    startup_environment: dict[str, object] = field(default_factory=dict)
    startup_mode: str = ''

    def with_startup(self, *, startup_environment: Mapping[str, object], startup_mode: str) -> 'RuntimeContextSnapshot':
        return RuntimeContextSnapshot(
            project_root=self.project_root,
            resource_root=self.resource_root,
            config_root=self.config_root,
            robot_root=self.robot_root,
            bundled_robot_root=self.bundled_robot_root,
            profiles_root=self.profiles_root,
            plugin_manifest_path=self.plugin_manifest_path,
            plugin_manifest_paths=self.plugin_manifest_paths,
            export_root=self.export_root,
            layout_mode=self.layout_mode,
            runtime_feature_policy=dict(self.runtime_feature_policy),
            profiles=tuple(self.profiles),
            plugin_discovery_enabled=bool(self.plugin_discovery_enabled),
            plugin_catalog=self.plugin_catalog,
            source_layout_available=bool(self.source_layout_available),
            config_resolution=dict(self.config_resolution),
            startup_environment=dict(startup_environment or {}),
            startup_mode=str(startup_mode or ''),
        )

    def as_dict(self) -> dict[str, object]:
        return {
            'project_root': self.project_root,
            'resource_root': self.resource_root,
            'config_root': self.config_root,
            'robot_root': self.robot_root,
            'bundled_robot_root': self.bundled_robot_root,
            'profiles_root': self.profiles_root,
            'plugin_manifest_path': self.plugin_manifest_path,
            'plugin_manifest_paths': list(self.plugin_manifest_paths),
            'export_root': self.export_root,
            'layout_mode': self.layout_mode,
            'runtime_feature_policy': dict(self.runtime_feature_policy),
            'profiles': list(self.profiles),
            'plugin_discovery_enabled': bool(self.plugin_discovery_enabled),
            'plugin_catalog': self.plugin_catalog.as_dict(),
            'source_layout_available': bool(self.source_layout_available),
            'config_resolution': dict(self.config_resolution),
            'startup_environment': dict(self.startup_environment),
            'startup_mode': self.startup_mode,
        }


@dataclass(frozen=True)
class StartupSummarySnapshot(MappingSnapshot):
    app_version: str
    schemas: dict[str, object] = field(default_factory=dict)
    capabilities: dict[str, object] = field(default_factory=dict)
    runtime: dict[str, object] = field(default_factory=dict)
    startup_environment: dict[str, object] = field(default_factory=dict)
    startup_mode: str = ''

    def as_dict(self) -> dict[str, object]:
        return {
            'app_version': self.app_version,
            'schemas': dict(self.schemas),
            'capabilities': dict(self.capabilities),
            'runtime': dict(self.runtime),
            'startup_environment': dict(self.startup_environment),
            'startup_mode': self.startup_mode,
        }


@dataclass(frozen=True)
class EnvironmentSnapshot(MappingSnapshot):
    """Authoritative environment snapshot for diagnostics/export surfaces.

    The environment surface is now cloneable, replay-aware, diff-replication aware, and suitable
    for concurrent planner snapshots. The snapshot still preserves mapping compatibility for
    existing callers while projecting richer environment semantics across export/session/runtime
    surfaces.
    """

    revision: int = 0
    collision_backend: str = 'aabb'
    scene_fidelity: str = 'unknown'
    obstacle_ids: tuple[str, ...] = ()
    attached_object_ids: tuple[str, ...] = ()
    allowed_collision_pairs: tuple[tuple[str, str], ...] = ()
    scene_authority: str = ''
    scene_geometry_contract: str = ''
    last_scene_command: dict[str, object] = field(default_factory=dict)
    scene_command_log_tail: tuple[dict[str, object], ...] = ()
    scene_command_history: tuple[dict[str, object], ...] = ()
    scene_revision_history: tuple[dict[str, object], ...] = ()
    replay_cursor: str = ''
    clone_token: str = ''
    concurrent_snapshot_tokens: tuple[str, ...] = ()
    diff_replication: dict[str, object] = field(default_factory=dict)
    environment_contract: dict[str, object] = field(default_factory=dict)
    log_policy: dict[str, object] = field(default_factory=lambda: {
        'retention_model': 'bounded_tail_plus_history',
        'intended_use': 'diagnostic_log_and_replay',
        'supports_replay': True,
        'supports_clone': True,
        'supports_diff_replication': True,
        'supports_concurrent_snapshots': True,
    })

    @classmethod
    def from_scene_summary(cls, payload: Mapping[str, object] | None) -> 'EnvironmentSnapshot':
        raw = dict(payload or {})
        return cls(
            revision=int(raw.get('revision', 0) or 0),
            collision_backend=str(raw.get('collision_backend', 'aabb') or 'aabb'),
            scene_fidelity=str(raw.get('scene_fidelity', 'unknown') or 'unknown'),
            obstacle_ids=tuple(str(item) for item in raw.get('obstacle_ids', ()) or ()),
            attached_object_ids=tuple(str(item) for item in raw.get('attached_object_ids', ()) or ()),
            allowed_collision_pairs=tuple(tuple(str(part) for part in pair) for pair in raw.get('allowed_collision_pairs', ()) or ()),
            scene_authority=str(raw.get('scene_authority', '') or ''),
            scene_geometry_contract=str(raw.get('scene_geometry_contract', '') or ''),
            last_scene_command=dict(raw.get('last_scene_command', {}) or {}),
            scene_command_log_tail=tuple(dict(item) for item in raw.get('scene_command_log_tail', ()) or ()),
            scene_command_history=tuple(dict(item) for item in raw.get('scene_command_history', ()) or ()),
            scene_revision_history=tuple(dict(item) for item in raw.get('scene_revision_history', ()) or ()),
            replay_cursor=str(raw.get('replay_cursor', f"rev:{int(raw.get('revision', 0) or 0)}") or f"rev:{int(raw.get('revision', 0) or 0)}"),
            clone_token=str(raw.get('clone_token', '') or ''),
            concurrent_snapshot_tokens=tuple(str(item) for item in raw.get('concurrent_snapshot_tokens', ()) or ()),
            diff_replication=dict(raw.get('diff_replication', {}) or {}),
            environment_contract=dict(raw.get('environment_contract', {}) or {
                'version': 'v2',
                'supports_clone': True,
                'supports_replay': True,
                'supports_diff_replication': True,
                'supports_concurrent_snapshots': True,
            }),
            log_policy=dict(raw.get('log_policy', {}) or {
                'retention_model': 'bounded_tail_plus_history',
                'intended_use': 'diagnostic_log_and_replay',
                'supports_replay': True,
                'supports_clone': True,
                'supports_diff_replication': True,
                'supports_concurrent_snapshots': True,
            }),
        )

    def as_dict(self) -> dict[str, object]:
        return {
            'revision': int(self.revision),
            'collision_backend': self.collision_backend,
            'scene_fidelity': self.scene_fidelity,
            'obstacle_ids': list(self.obstacle_ids),
            'attached_object_ids': list(self.attached_object_ids),
            'allowed_collision_pairs': [list(pair) for pair in self.allowed_collision_pairs],
            'scene_authority': self.scene_authority,
            'scene_geometry_contract': self.scene_geometry_contract,
            'last_scene_command': dict(self.last_scene_command),
            'scene_command_log_tail': [dict(item) for item in self.scene_command_log_tail],
            'scene_command_history': [dict(item) for item in self.scene_command_history],
            'scene_revision_history': [dict(item) for item in self.scene_revision_history],
            'replay_cursor': str(self.replay_cursor),
            'clone_token': str(self.clone_token),
            'concurrent_snapshot_tokens': list(self.concurrent_snapshot_tokens),
            'diff_replication': dict(self.diff_replication),
            'environment_contract': dict(self.environment_contract),
            'log_policy': dict(self.log_policy),
        }

