from __future__ import annotations

import warnings

from robot_sim.presentation.experimental.widgets.export_panel import ExportPanel as _ExperimentalExportPanel


class ExportPanel(_ExperimentalExportPanel):
    """Deprecated stable-path alias for the experimental ExportPanel widget.

    The stable namespace no longer silently re-exports experimental widgets as if they were
    promoted surfaces. This alias remains only to preserve transitional imports while making
    the compatibility status explicit to callers and migration tooling.
    """

    def __init__(self, *args, **kwargs) -> None:
        warnings.warn(
            'robot_sim.presentation.widgets.export_panel.ExportPanel is a deprecated compatibility alias; import the experimental widget directly until the surface is promoted',
            DeprecationWarning,
            stacklevel=2,
        )
        super().__init__(*args, **kwargs)


__all__ = ['ExportPanel']
