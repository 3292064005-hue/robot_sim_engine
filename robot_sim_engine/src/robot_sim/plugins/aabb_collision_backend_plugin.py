from __future__ import annotations

from robot_sim.application.services.collision_backend_runtime import AABBCollisionBackendRuntime
from robot_sim.plugin_sdk import plugin_payload


class AABBCollisionBackendPlugin(AABBCollisionBackendRuntime):
    """Repository-shipped executable collision backend.

    The plugin now exposes the same projection/runtime operations consumed by the
    planning-scene authority and validation pipeline instead of only advertising a
    contract surface.
    """

    def __init__(self) -> None:
        super().__init__()
        self.plugin_backend_id = 'aabb_collision_backend'

    def capabilities(self) -> dict[str, object]:
        payload = super().capabilities()
        payload.update(
            {
                'plugin_backend_id': self.plugin_backend_id,
                'notes': 'Repository-shipped production collision backend used by runtime declaration->query projection.',
            }
        )
        return payload


def build_plugin(**_context):
    plugin = AABBCollisionBackendPlugin()
    return plugin_payload(
        plugin,        metadata={
            **plugin.capabilities(),
            'source': 'shipped_plugin',
            'verification_scope': 'runtime_projection_surface',
        },
    )
