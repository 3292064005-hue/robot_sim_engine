from __future__ import annotations

from robot_sim.core.ik.dls import DLSIKSolver
from robot_sim.domain.enums import SolverFamily


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
    return {
        'instance': ResearchDemoDLSIKSolver(),
        'aliases': ('research_demo',),
        'metadata': {
            'family': SolverFamily.ITERATIVE.value,
            'display_name': 'Research demo DLS solver',
            'notes': 'Repository-shipped plugin fixture used to exercise controlled plugin discovery.',
            'source': 'shipped_plugin',
        },
    }
