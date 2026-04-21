from __future__ import annotations

from robot_sim.application.services.scene_backend_runtime import PlanningSceneBackendRuntime
from robot_sim.plugin_sdk import plugin_payload


class PlanningSceneBackendPlugin(PlanningSceneBackendRuntime):
    """Repository-shipped executable planning-scene backend."""

    def capabilities(self) -> dict[str, object]:
        payload = super().capabilities()
        payload.update(
            {
                'notes': 'Repository-shipped production scene backend used by the stable scene authority runtime.',
                'validation_adapter_model': 'explicit_backend_projection',
            }
        )
        return payload


def build_plugin(**_context):
    plugin = PlanningSceneBackendPlugin()
    return plugin_payload(
        plugin,        metadata={
            **plugin.capabilities(),
            'source': 'shipped_plugin',
            'verification_scope': 'runtime_projection_surface',
        },
    )
