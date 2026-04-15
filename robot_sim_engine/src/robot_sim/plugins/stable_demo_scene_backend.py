from __future__ import annotations

from dataclasses import dataclass

from robot_sim.plugin_sdk import plugin_payload


@dataclass(frozen=True)
class StableSceneBackendContractPlugin:
    backend_id: str = 'stable_demo_scene_contract'

    def capabilities(self) -> dict[str, object]:
        return {
            'display_name': 'Stable shipped scene backend contract',
            'plugin_surface': 'scene_backend',
            'scene_geometry_contract_version': 'v1',
            'scene_validation_capability_matrix_version': 'v1',
            'notes': 'Repository-shipped stable fixture that keeps the reserved scene-backend plugin surface alive without mutating runtime behavior.',
        }


def build_plugin(**_context):
    return plugin_payload(
        StableSceneBackendContractPlugin(),
        aliases=('stable_scene_backend_contract',),
        metadata={
            'display_name': 'Stable shipped scene backend contract',
            'plugin_surface': 'scene_backend',
            'scene_geometry_contract_version': 'v1',
            'scene_validation_capability_matrix_version': 'v1',
            'source': 'shipped_plugin',
            'verification_scope': 'capability_surface',
        },
    )
