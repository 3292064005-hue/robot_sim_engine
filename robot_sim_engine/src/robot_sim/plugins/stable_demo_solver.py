from __future__ import annotations

from dataclasses import replace

from robot_sim.core.ik.lm import LevenbergMarquardtIKSolver
from robot_sim.domain.enums import IKSolverMode, SolverFamily
from robot_sim.plugin_sdk import plugin_payload


class StableDemoLMIKSolver(LevenbergMarquardtIKSolver):
    """Repository-shipped stable solver plugin used to keep the stable plugin path alive.

    Boundary behavior:
        The stable shipped plugin exposes its own registry id while intentionally reusing the
        canonical LM implementation. Incoming configs that reference the plugin id are coerced
        back to ``IKSolverMode.LM`` before the inherited iterative solver logic runs.
    """

    def solve(self, spec, target, q0, config, cancel_flag=None, progress_cb=None, *, attempt_idx: int = 0):
        normalized_config = config
        if getattr(getattr(config, 'mode', None), 'value', None) is None and str(getattr(config, 'mode', '') or '') == 'stable_demo_lm':
            normalized_config = replace(config, mode=IKSolverMode.LM)
        return super().solve(
            spec,
            target,
            q0,
            normalized_config,
            cancel_flag=cancel_flag,
            progress_cb=progress_cb,
            attempt_idx=attempt_idx,
        )


def build_plugin():
    """Return the repository-shipped stable solver plugin payload."""
    return plugin_payload(
        StableDemoLMIKSolver(),
        aliases=('stable_lm',),
        metadata={
            'family': SolverFamily.ITERATIVE.value,
            'display_name': 'Stable shipped LM solver',
            'notes': 'Repository-shipped stable plugin fixture used to exercise mainline plugin loading.',
            'source': 'shipped_plugin',
            'verification_scope': 'registry_smoke',
        },
    )
