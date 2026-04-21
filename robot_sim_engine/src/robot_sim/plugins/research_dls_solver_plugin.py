from __future__ import annotations

from robot_sim.core.ik.dls import DLSIKSolver
from robot_sim.domain.enums import SolverFamily
from robot_sim.plugin_sdk import plugin_payload


class ResearchDemoDLSIKSolver(DLSIKSolver):
    """Repository-shipped research-profile demo plugin.

    The solver intentionally reuses the stable DLS implementation so plugin discovery can be
    verified without introducing an additional algorithm-specific maintenance burden.
    """


def build_plugin():
    """Return the shipped research demo solver plugin payload.

    Returns:
        dict[str, object]: Registry payload compatible with ``PluginLoader``.
    """
    return plugin_payload(
        ResearchDemoDLSIKSolver(),        metadata={
            'family': SolverFamily.ITERATIVE.value,
            'display_name': 'Research DLS solver',
            'notes': 'Repository-shipped experimental plugin used by the research runtime surface.',
            'source': 'shipped_plugin',
        },
    )
