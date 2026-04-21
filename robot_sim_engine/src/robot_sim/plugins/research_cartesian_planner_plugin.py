from __future__ import annotations

from robot_sim.application.planner_plugins import CartesianSampledTrajectoryPlugin
from robot_sim.plugin_sdk import plugin_payload


def build_plugin(*, ik_uc):
    """Return a repository-shipped planner plugin payload.

    The plugin intentionally reuses the stable Cartesian sampled planner so the plugin path
    exercises context injection without creating a forked planning implementation.
    """
    return plugin_payload(
        CartesianSampledTrajectoryPlugin(ik_uc),        metadata={
            'family': 'cartesian',
            'goal_space': 'cartesian',
            'requires_ik': True,
            'timing_strategy': 'quintic_samples',
            'display_name': 'Research Cartesian planner',
            'notes': 'Repository-shipped planner plugin used by the research runtime surface.',
            'source': 'shipped_plugin',
            'verification_scope': 'registry_smoke',
        },
    )
