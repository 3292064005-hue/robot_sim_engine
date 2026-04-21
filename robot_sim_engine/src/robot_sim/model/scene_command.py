from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class SceneCommand:
    """Structured scene-authority command emitted for stable planning-scene mutations.

    Attributes:
        command_kind: Stable mutation category such as ``upsert_obstacle`` or
            ``clear_obstacles``.
        source: Stable caller/source label projected from the UI or orchestration layer.
        object_id: Target object identifier when the command acts on one scene record.
        revision_before: Scene revision before the command executes.
        revision_after: Scene revision after the command executes.
        scene_graph_diff: Structured graph diff observed across the mutation.
        metadata: Additional deterministic command metadata for diagnostics/export.
    """

    command_kind: str
    source: str
    object_id: str = ''
    revision_before: int = 0
    revision_after: int = 0
    scene_graph_diff: dict[str, object] = field(default_factory=dict)
    metadata: dict[str, object] = field(default_factory=dict)

    def summary(self) -> dict[str, object]:
        return {
            'command_kind': str(self.command_kind or ''),
            'source': str(self.source or ''),
            'object_id': str(self.object_id or ''),
            'revision_before': int(self.revision_before),
            'revision_after': int(self.revision_after),
            'scene_graph_diff': dict(self.scene_graph_diff or {}),
            'metadata': dict(self.metadata or {}),
        }


@dataclass(frozen=True)
class SceneMutationResult:
    """Return one canonical scene mutation together with its emitted command."""

    scene: object
    command: SceneCommand

    def summary(self) -> dict[str, object]:
        return {
            'command': self.command.summary(),
        }
