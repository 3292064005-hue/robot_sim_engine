from __future__ import annotations

from robot_sim.application.planner_plugins import JointTrapezoidalTrajectoryPlugin
from robot_sim.plugin_sdk import plugin_payload


def build_plugin(*, ik_uc):
    """Return the repository-shipped production planner plugin payload."""
    return plugin_payload(
        JointTrapezoidalTrajectoryPlugin(),        metadata={
            'family': 'joint_space',
            'goal_space': 'joint',
            'requires_ik': False,
            'timing_strategy': 'trapezoidal',
            'display_name': 'Shipped joint-space planner',
            'notes': 'Repository-shipped production planner plugin used by the default runtime surface.',
            'source': 'shipped_plugin',
            'verification_scope': 'registry_smoke',
            'canonical_target': 'joint_trapezoidal',
        },
    )
