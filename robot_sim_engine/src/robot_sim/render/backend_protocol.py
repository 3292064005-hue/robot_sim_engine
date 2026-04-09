from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol

from robot_sim.model.render_runtime import RenderCapabilityState


@dataclass(frozen=True)
class CaptureResult:
    path: str
    runtime_state: RenderCapabilityState
    provenance: dict[str, object] = field(default_factory=dict)


class CaptureBackend(Protocol):
    """Protocol implemented by screenshot backends."""

    backend_id: str

    def runtime_state(self, scene_widget) -> RenderCapabilityState:
        ...

    def capture(self, scene_widget, path: str) -> CaptureResult:
        ...
