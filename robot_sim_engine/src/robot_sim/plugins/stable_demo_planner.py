from __future__ import annotations

from robot_sim.application.planner_plugins import JointTrapezoidalTrajectoryPlugin
from robot_sim.plugin_sdk import plugin_payload


def build_plugin(*, ik_uc):
    """Return the repository-shipped stable planner plugin payload."""
    return plugin_payload(
        JointTrapezoidalTrajectoryPlugin(),
        aliases=('stable_joint_space',),
        metadata={
            'family': 'joint_space',
            'goal_space': 'joint',
            'requires_ik': False,
            'timing_strategy': 'trapezoidal',
            'display_name': 'Stable shipped joint planner',
            'notes': 'Repository-shipped stable planner plugin fixture used to exercise mainline plugin loading.',
            'source': 'shipped_plugin',
            'verification_scope': 'registry_smoke',
        },
    )
