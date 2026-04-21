from __future__ import annotations

"""Frozen compatibility package for legacy controller wrappers.

This package is the only supported import surface for controller-level orchestration that has
been superseded by workflow services. The legacy module paths remain importable for downstream
compatibility, but new integrations must not depend on them.
"""

from robot_sim.presentation.controllers.benchmark_controller import BenchmarkController
from robot_sim.presentation.controllers.export_controller import ExportController
from robot_sim.presentation.controllers.ik_controller import IKController
from robot_sim.presentation.controllers.trajectory_controller import TrajectoryController

LEGACY_CONTROLLER_IDS = (
    'IKController',
    'TrajectoryController',
    'BenchmarkController',
    'ExportController',
)

__all__ = [
    'IKController',
    'TrajectoryController',
    'BenchmarkController',
    'ExportController',
    'LEGACY_CONTROLLER_IDS',
]
