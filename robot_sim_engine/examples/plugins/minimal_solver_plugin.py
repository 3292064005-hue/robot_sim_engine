from __future__ import annotations

from robot_sim.core.ik.dls import DLSIKSolver
from robot_sim.domain.enums import SolverFamily
from robot_sim.plugin_sdk import plugin_payload


class MinimalExampleSolver(DLSIKSolver):
    """Tiny example solver plugin used as a public SDK reference."""


def build_plugin(*, display_name: str = 'Example DLS solver'):
    """Return a manifest-compatible plugin payload for ``PluginLoader`` examples."""
    return plugin_payload(
        MinimalExampleSolver(),
        aliases=('example_solver_alias',),
        metadata={
            'family': SolverFamily.ITERATIVE.value,
            'display_name': display_name,
            'source': 'sdk_example',
        },
    )
