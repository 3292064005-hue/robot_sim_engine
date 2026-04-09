from __future__ import annotations

"""Packaged runtime resources for installed-wheel execution.

<<<<<<< HEAD
The repository keeps ``configs/`` as the single checked-in configuration source of truth.
Wheel and sdist builds stage those configs into the installed ``robot_sim.resources`` package
at build time, and installed runtimes resolve configuration from that packaged copy when a
source checkout layout is not available.
=======
This package mirrors the configuration assets that also exist at the repository root.
Wheel-based launches resolve configuration from this package when a source checkout
layout is not available.
>>>>>>> 3ed78e647985c6d680c085e4480d898855278db3
"""
