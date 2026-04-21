from __future__ import annotations

"""Compatibility export surface for the canonical application workflow façade.

The concrete workflow implementation now lives in ``robot_sim.app.workflows`` so the
public import path remains stable while import/session orchestration is split into
smaller, single-purpose modules.
"""

from robot_sim.app.workflows import ApplicationWorkflowFacade, ResolvedImportBundle

__all__ = ['ApplicationWorkflowFacade', 'ResolvedImportBundle']
