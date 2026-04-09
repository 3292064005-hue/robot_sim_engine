from __future__ import annotations

from robot_sim.application.planner_plugins import CartesianSampledTrajectoryPlugin


def build_plugin(*, ik_uc):
    """Return a repository-shipped planner plugin payload.

    The plugin intentionally reuses the stable Cartesian sampled planner so the plugin path
    exercises context injection without creating a forked planning implementation.
    """
    return {
        'instance': CartesianSampledTrajectoryPlugin(ik_uc),
        'aliases': ('research_cartesian',),
        'metadata': {
            'family': 'cartesian',
            'goal_space': 'cartesian',
            'requires_ik': True,
            'timing_strategy': 'quintic_samples',
            'display_name': 'Research demo Cartesian planner',
            'notes': 'Repository-shipped planner plugin fixture used to exercise controlled plugin discovery.',
            'source': 'shipped_plugin',
            'verification_scope': 'registry_smoke',
        },
    }
