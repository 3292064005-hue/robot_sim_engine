from __future__ import annotations

from dataclasses import dataclass, field
from typing import Mapping

from robot_sim.model.render_runtime import RenderCapabilityState, RenderRuntimeState
from robot_sim.model.session_state import SessionState

_RENDER_TITLES: dict[str, str] = {
    'scene_3d': '3D 视图',
    'plots': '曲线面板',
    'screenshot': '截图能力',
}
_STATUS_TEXT: dict[str, str] = {
    'available': '可用',
    'degraded': '降级',
    'unsupported': '不可用',
}
_SEVERITY_ORDER: dict[str, int] = {'nominal': 0, 'warning': 1, 'critical': 2}
_STATUS_SEVERITY: dict[str, str] = {
    'available': 'nominal',
    'degraded': 'warning',
    'unsupported': 'critical',
}


@dataclass(frozen=True)
class RenderCapabilityAlertState:
    """Typed UI projection for a single render capability status row."""

    capability: str
    title: str
    severity: str
    status_text: str
    metric_text: str
    detail_text: str
    tooltip_text: str
    message: str
    backend: str
    reason: str
    error_code: str
    metadata: Mapping[str, object] = field(default_factory=dict)

    @classmethod
    def from_capability(cls, capability_state: RenderCapabilityState) -> 'RenderCapabilityAlertState':
        severity = _STATUS_SEVERITY.get(capability_state.status, 'warning')
        title = _RENDER_TITLES.get(capability_state.capability, capability_state.capability)
        status_text = _STATUS_TEXT.get(capability_state.status, capability_state.status)
        detail_parts = [
            part
            for part in (
                capability_state.backend,
                capability_state.reason,
                capability_state.error_code,
            )
            if str(part or '') != ''
        ]
        detail_text = ' / '.join(str(part) for part in detail_parts) or (capability_state.message or '运行正常')
        metric_text = status_text if detail_text == '' else f'{status_text} ({detail_text})'
        tooltip_lines = [f'{title}: {status_text}']
        if capability_state.message:
            tooltip_lines.append(capability_state.message)
        if detail_parts:
            tooltip_lines.append(f'细节: {detail_text}')
        return cls(
            capability=capability_state.capability,
            title=title,
            severity=severity,
            status_text=status_text,
            metric_text=metric_text,
            detail_text=detail_text,
            tooltip_text='\n'.join(tooltip_lines),
            message=capability_state.message,
            backend=capability_state.backend,
            reason=capability_state.reason,
            error_code=capability_state.error_code,
            metadata=dict(capability_state.metadata),
        )


@dataclass(frozen=True)
class RenderRuntimePanelState:
    """Typed UI state used by the status panel to render render-runtime degradation.

    Attributes:
        alerts: Ordered per-capability alert projections.
        overall_severity: Aggregate severity used by the status-strip headline.
        summary_text: Human-readable aggregate summary shown in the render group header.
        advice_summary: Human-readable operator guidance derived from runtime telemetry.
        advice_rows: Per-capability strategy guidance projected into the UI.
    """

    alerts: tuple[RenderCapabilityAlertState, ...]
    overall_severity: str
    summary_text: str
    advice_summary: str = 'Render 建议：无'
    advice_rows: Mapping[str, str] = field(default_factory=dict)

    @property
    def metric_payload(self) -> dict[str, str]:
        """Return compact metric text used by the status strip summary rows."""
        payload = {alert.capability: alert.metric_text for alert in self.alerts}
        payload['render_advice'] = self.advice_summary
        return payload

    @property
    def detail_rows(self) -> dict[str, str]:
        """Return per-capability detail text rendered inside the detailed render panel."""
        return {alert.capability: alert.detail_text or alert.message or '运行正常' for alert in self.alerts}

    @property
    def degraded_alerts(self) -> tuple[RenderCapabilityAlertState, ...]:
        """Return only warning/critical alerts for downstream diagnostics consumers."""
        return tuple(alert for alert in self.alerts if alert.severity != 'nominal')


@dataclass(frozen=True)
class StatusPanelProjection:
    """Typed status-panel projection derived from shared session state."""

    playback_text: str
    render_runtime: RenderRuntimePanelState

    @property
    def metric_payload(self) -> dict[str, str]:
        payload = {'playback': self.playback_text}
        payload.update(self.render_runtime.metric_payload)
        return payload


def _render_summary(alerts: tuple[RenderCapabilityAlertState, ...]) -> tuple[str, str]:
    degraded = tuple(alert for alert in alerts if alert.severity == 'warning')
    critical = tuple(alert for alert in alerts if alert.severity == 'critical')
    if not degraded and not critical:
        return 'nominal', 'Render 状态：全部可用'
    parts: list[str] = []
    if critical:
        parts.append(f"{len(critical)} 个不可用")
    if degraded:
        parts.append(f"{len(degraded)} 个降级")
    impacted = ', '.join(alert.title for alert in (*critical, *degraded))
    summary = f"Render 状态：{'，'.join(parts)}"
    if impacted:
        summary = f'{summary}（{impacted}）'
    severity = 'critical' if critical else 'warning'
    return severity, summary


def _build_render_advice_projection(runtime_advice: Mapping[str, object] | None) -> tuple[str, dict[str, str]]:
    advice = dict(runtime_advice or {})
    recommendations = advice.get('recommendations', ()) or ()
    if not recommendations:
        return 'Render 建议：无', {}
    rows: dict[str, str] = {}
    labels: list[str] = []
    for item in recommendations:
        if not isinstance(item, Mapping):
            continue
        capability = str(item.get('capability', '') or '').strip()
        action = str(item.get('action', '') or '').strip() or 'review_runtime'
        rationale = str(item.get('rationale', '') or '').strip()
        backend = str(item.get('backend', '') or '').strip()
        label = _RENDER_TITLES.get(capability, capability or 'runtime')
        detail_parts = [part for part in (backend, action, rationale) if part]
        detail = ' / '.join(detail_parts) if detail_parts else action
        if capability:
            rows[capability] = detail
        labels.append(f'{label}:{action}')
    summary = 'Render 建议：' + ('；'.join(labels) if labels else '无')
    return summary, rows


def format_playback_metric(playback) -> str:
    """Format the compact playback metric shown in the status strip."""
    total_frames = int(getattr(playback, 'total_frames', 0) or 0)
    if total_frames <= 0:
        return '无轨迹'
    return f"{'播放中' if bool(getattr(playback, 'is_playing', False)) else '就绪'} @ {float(getattr(playback, 'speed_multiplier', 1.0) or 1.0):.1f}x"


def build_render_runtime_panel_state(
    render_runtime: RenderRuntimeState | Mapping[str, object],
    runtime_advice: Mapping[str, object] | None = None,
) -> RenderRuntimePanelState:
    """Project structured render-runtime state into a typed status-panel model."""
    runtime = RenderRuntimeState.from_mapping(render_runtime)
    alerts = tuple(
        RenderCapabilityAlertState.from_capability(capability)
        for capability in (runtime.scene_3d, runtime.plots, runtime.screenshot)
    )
    severity, summary = _render_summary(alerts)
    advice_summary, advice_rows = _build_render_advice_projection(runtime_advice)
    if advice_rows and severity == 'nominal':
        severity = 'warning'
    return RenderRuntimePanelState(
        alerts=alerts,
        overall_severity=severity,
        summary_text=summary,
        advice_summary=advice_summary,
        advice_rows=advice_rows,
    )


def build_status_panel_projection(state: SessionState) -> StatusPanelProjection:
    """Build the status-panel projection from shared runtime session state."""
    return StatusPanelProjection(
        playback_text=format_playback_metric(state.playback),
        render_runtime=build_render_runtime_panel_state(
            RenderRuntimeState.from_mapping(state.render_runtime),
            state.render_runtime_advice,
        ),
    )
