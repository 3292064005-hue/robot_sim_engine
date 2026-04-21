from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class ExportManifest:
    app_name: str
    app_version: str
    schema_version: str
    export_version: str = ''
    producer_version: str = ''
    correlation_id: str = ''
    robot_id: str | None = None
    solver_id: str | None = None
    planner_id: str | None = None
    timestamp_utc: str = ""
    reproducibility_seed: int | None = None
    bundle_kind: str = 'artifact_bundle'
    bundle_contract: str = 'artifact_audit_bundle'
    replayable: bool = False
    files: tuple[str, ...] = ()
    environment: dict[str, object] = field(default_factory=dict)
    config_snapshot: dict[str, object] = field(default_factory=dict)
    scene_snapshot: dict[str, object] = field(default_factory=dict)
    plugin_snapshot: dict[str, object] = field(default_factory=dict)
    capability_snapshot: dict[str, object] = field(default_factory=dict)
    metadata: dict[str, object] = field(default_factory=dict)
