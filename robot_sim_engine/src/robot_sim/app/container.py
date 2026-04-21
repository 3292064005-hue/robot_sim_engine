from __future__ import annotations

"""Compatibility export surface for the application dependency container.

The concrete container dataclasses and builder now live in dedicated modules so the stable
import path remains available while startup assembly is decomposed into smaller units.
"""

from robot_sim.app.container_builder import build_container
from robot_sim.app.container_types import (
    AppBootstrapBundle,
    AppContainer,
    AppRegistryBundle,
    AppServiceBundle,
    AppWorkflowBundle,
)

__all__ = [
    'AppBootstrapBundle',
    'AppContainer',
    'AppRegistryBundle',
    'AppServiceBundle',
    'AppWorkflowBundle',
    'build_container',
]
