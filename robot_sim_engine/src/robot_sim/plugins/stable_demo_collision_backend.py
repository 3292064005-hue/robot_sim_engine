from __future__ import annotations

from dataclasses import dataclass

from robot_sim.plugin_sdk import plugin_payload


@dataclass(frozen=True)
class StableCollisionBackendContractPlugin:
    backend_id: str = 'stable_demo_collision_backend'

    def capabilities(self) -> dict[str, object]:
        return {
            'display_name': 'Stable shipped collision backend contract',
            'plugin_surface': 'collision_backend',
            'backend_contract_version': 'v1',
            'validation_fidelity': 'approximate_aabb',
            'notes': 'Repository-shipped stable fixture that reserves the collision-backend plugin surface without changing the canonical runtime fallback backend.',
        }


def build_plugin(**_context):
    return plugin_payload(
        StableCollisionBackendContractPlugin(),
        aliases=('stable_collision_backend_contract',),
        metadata={
            'display_name': 'Stable shipped collision backend contract',
            'plugin_surface': 'collision_backend',
            'backend_contract_version': 'v1',
            'validation_fidelity': 'approximate_aabb',
            'source': 'shipped_plugin',
            'verification_scope': 'capability_surface',
        },
    )
