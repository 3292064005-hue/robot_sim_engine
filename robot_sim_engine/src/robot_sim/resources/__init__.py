from __future__ import annotations

"""Packaged runtime resources for installed-wheel execution.

The repository keeps ``configs/`` as the single checked-in configuration source of truth.
Wheel and sdist builds stage those configs into the installed ``robot_sim.resources`` package
at build time, and installed runtimes resolve configuration from that packaged copy when a
source checkout layout is not available.
"""
