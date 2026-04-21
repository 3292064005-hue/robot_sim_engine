from __future__ import annotations

"""Presentation controller package surface.

The active startup surface is workflow-first. Only stable controllers that still participate in
current bootstrap flows remain in the default package export list. Legacy controller wrappers are
frozen under :mod:`robot_sim.presentation.controllers.compatibility`.
"""

__all__ = [
    'RobotController',
    'PlaybackController',
    'DiagnosticsController',
]
