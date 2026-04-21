from __future__ import annotations

from dataclasses import dataclass, field

from robot_sim.core.collision.scene import PlanningScene
from robot_sim.model.robot_geometry import RobotGeometry
from robot_sim.model.robot_geometry_model import RobotGeometryModel


@dataclass(frozen=True)
class RuntimeAssetCacheEntry:
    """Cached runtime asset projection for one spec/geometry signature."""

    cache_key: str
    assets: 'RobotRuntimeAssets'


@dataclass(frozen=True)
class RobotRuntimeAssets:
    """Runtime projection assets derived from a robot specification."""

    robot_geometry: RobotGeometry | None
    collision_geometry: RobotGeometry | None
    geometry_model: RobotGeometryModel
    planning_scene: PlanningScene
    scene_summary: dict[str, object]


@dataclass(frozen=True)
class RuntimeAssetInvalidationEvent:
    """Structured invalidation record used by tests and diagnostics."""

    reason: str
    spec_name: str | None
    removed_entries: int
    context_signature: str


@dataclass
class RuntimeAssetCacheStore:
    """Own the runtime-asset cache independently from the façade service."""

    entries: dict[str, RuntimeAssetCacheEntry] = field(default_factory=dict)

    def get(self, cache_key: str) -> RuntimeAssetCacheEntry | None:
        return self.entries.get(cache_key)

    def put(self, cache_key: str, assets: RobotRuntimeAssets) -> None:
        self.entries[cache_key] = RuntimeAssetCacheEntry(cache_key=cache_key, assets=assets)

    def clear(self) -> int:
        removed = len(self.entries)
        self.entries.clear()
        return removed

    def remove_for_spec(self, spec_name: str) -> int:
        prefix = f"{spec_name}:"
        removed = 0
        for key in tuple(self.entries):
            if key.startswith(prefix):
                self.entries.pop(key, None)
                removed += 1
        return removed

    def entry_count(self) -> int:
        return len(self.entries)


@dataclass
class RuntimeAssetInvalidationJournal:
    """Own structured invalidation logging independently from cache storage."""

    events: list[RuntimeAssetInvalidationEvent] = field(default_factory=list)

    def record(self, *, reason: str, spec_name: str | None, removed_entries: int, context_signature: str) -> None:
        self.events.append(
            RuntimeAssetInvalidationEvent(
                reason=str(reason or 'manual'),
                spec_name=None if spec_name in (None, '') else str(spec_name),
                removed_entries=int(removed_entries),
                context_signature=str(context_signature),
            )
        )

    def snapshot(self) -> tuple[RuntimeAssetInvalidationEvent, ...]:
        return tuple(self.events)

    def count(self) -> int:
        return len(self.events)


@dataclass(frozen=True)
class KinematicRuntimeSurface:
    """Stable summary of the kinematic/runtime authority for one robot spec."""

    runtime_model_summary: dict[str, object]
    articulated_model_summary: dict[str, object]
    execution_summary: dict[str, object]


@dataclass(frozen=True)
class GeometryProjectionResult:
    """Geometry/projection output used to build runtime scene assets."""

    robot_geometry: RobotGeometry | None
    collision_geometry: RobotGeometry | None
    geometry_model: RobotGeometryModel
