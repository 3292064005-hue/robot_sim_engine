from __future__ import annotations

from dataclasses import dataclass, field
from typing import Mapping

_ALLOWED_RENDER_STATUSES = frozenset({"available", "degraded", "unsupported"})


@dataclass(frozen=True)
class RenderCapabilityState:
    """Structured runtime status for a single render-related capability.

    Attributes:
        capability: Stable capability identifier such as ``scene_3d`` or ``screenshot``.
        status: Availability class for the capability.
        backend: Effective backend identifier.
        reason: Stable degradation or activation reason.
        error_code: Stable error code when the capability is not fully available.
        message: User-facing diagnostic message.
        level: Capability-level classification such as ``live_3d`` or ``snapshot_capture``.
        metadata: Structured auxiliary payload.
        provenance: Structured provenance describing where the rendered result comes from.
    """

    capability: str
    status: str = 'available'
    backend: str = ''
    reason: str = ''
    error_code: str = ''
    message: str = ''
    level: str = ''
    metadata: dict[str, object] = field(default_factory=dict)
    provenance: dict[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        normalized_status = str(self.status or 'available')
        if normalized_status not in _ALLOWED_RENDER_STATUSES:
            raise ValueError(f'unsupported render capability status: {self.status!r}')
        object.__setattr__(self, 'capability', str(self.capability))
        object.__setattr__(self, 'status', normalized_status)
        object.__setattr__(self, 'backend', str(self.backend or ''))
        object.__setattr__(self, 'reason', str(self.reason or ''))
        object.__setattr__(self, 'error_code', str(self.error_code or ''))
        object.__setattr__(self, 'message', str(self.message or ''))
        object.__setattr__(self, 'level', str(self.level or ''))
        object.__setattr__(self, 'metadata', dict(self.metadata or {}))
        object.__setattr__(self, 'provenance', dict(self.provenance or {}))

    @property
    def is_available(self) -> bool:
        return self.status == 'available'

    @property
    def is_degraded(self) -> bool:
        return self.status == 'degraded'

    @property
    def is_supported(self) -> bool:
        return self.status != 'unsupported'

    @property
    def capability_badges(self) -> tuple[str, ...]:
        return (
            f'capability:{self.capability}',
            f'status:{self.status}',
            f'backend:{self.backend or "none"}',
            f'level:{self.level or "unknown"}',
        )

    def has_capability_badge(self, badge: str) -> bool:
        return str(badge or '') in set(self.capability_badges)

    def require_level(self, *levels: str) -> None:
        allowed = tuple(str(item or '').strip() for item in levels if str(item or '').strip())
        if allowed and self.level not in allowed:
            raise ValueError(
                f'render capability {self.capability!r} does not provide one of the required levels {allowed!r}: {self.level!r}'
            )

    def as_dict(self) -> dict[str, object]:
        return {
            'capability': self.capability,
            'status': self.status,
            'is_available': self.is_available,
            'is_degraded': self.is_degraded,
            'is_supported': self.is_supported,
            'backend': self.backend,
            'reason': self.reason,
            'error_code': self.error_code,
            'message': self.message,
            'level': self.level,
            'metadata': dict(self.metadata),
            'provenance': dict(self.provenance),
        }

    @classmethod
    def from_mapping(cls, capability: str, payload: Mapping[str, object] | 'RenderCapabilityState' | object | None) -> 'RenderCapabilityState':
        if isinstance(payload, cls):
            return payload
        if payload is None:
            data: dict[str, object] = {}
        elif isinstance(payload, Mapping):
            data = dict(payload)
        else:
            data = {
                'status': getattr(payload, 'status', 'available'),
                'backend': getattr(payload, 'backend', ''),
                'reason': getattr(payload, 'reason', ''),
                'error_code': getattr(payload, 'error_code', ''),
                'message': getattr(payload, 'message', ''),
                'level': getattr(payload, 'level', ''),
                'metadata': getattr(payload, 'metadata', {}),
                'provenance': getattr(payload, 'provenance', {}),
            }
        return cls(
            capability=capability,
            status=str(data.get('status', 'available') or 'available'),
            backend=str(data.get('backend', '') or ''),
            reason=str(data.get('reason', '') or ''),
            error_code=str(data.get('error_code', '') or ''),
            message=str(data.get('message', '') or ''),
            level=str(data.get('level', '') or ''),
            metadata=dict(data.get('metadata', {}) or {}),
            provenance=dict(data.get('provenance', {}) or {}),
        )

    @classmethod
    def available_state(
        cls,
        capability: str,
        *,
        backend: str = '',
        reason: str = '',
        message: str = '',
        level: str = '',
        metadata: Mapping[str, object] | None = None,
        provenance: Mapping[str, object] | None = None,
    ) -> 'RenderCapabilityState':
        return cls(
            capability=capability,
            status='available',
            backend=backend,
            reason=reason,
            message=message,
            level=level,
            metadata=dict(metadata or {}),
            provenance=dict(provenance or {}),
        )


@dataclass(frozen=True)
class RenderRuntimeState:
    """Aggregate runtime status for render-related surfaces exposed by the GUI shell."""

    scene_3d: RenderCapabilityState = field(default_factory=lambda: RenderCapabilityState.available_state('scene_3d'))
    plots: RenderCapabilityState = field(default_factory=lambda: RenderCapabilityState.available_state('plots'))
    screenshot: RenderCapabilityState = field(default_factory=lambda: RenderCapabilityState.available_state('screenshot'))

    def __post_init__(self) -> None:
        object.__setattr__(self, 'scene_3d', RenderCapabilityState.from_mapping('scene_3d', self.scene_3d))
        object.__setattr__(self, 'plots', RenderCapabilityState.from_mapping('plots', self.plots))
        object.__setattr__(self, 'screenshot', RenderCapabilityState.from_mapping('screenshot', self.screenshot))

    @property
    def degraded_capabilities(self) -> tuple[str, ...]:
        return tuple(cap.capability for cap in (self.scene_3d, self.plots, self.screenshot) if not cap.is_available)

    def as_dict(self) -> dict[str, object]:
        return {
            'scene_3d': self.scene_3d.as_dict(),
            'plots': self.plots.as_dict(),
            'screenshot': self.screenshot.as_dict(),
            'degraded_capabilities': list(self.degraded_capabilities),
        }

    @classmethod
    def from_mapping(cls, payload: Mapping[str, object] | 'RenderRuntimeState' | None) -> 'RenderRuntimeState':
        if isinstance(payload, cls):
            return payload
        data = dict(payload or {})
        return cls(
            scene_3d=RenderCapabilityState.from_mapping('scene_3d', data.get('scene_3d')),
            plots=RenderCapabilityState.from_mapping('plots', data.get('plots')),
            screenshot=RenderCapabilityState.from_mapping('screenshot', data.get('screenshot')),
        )
