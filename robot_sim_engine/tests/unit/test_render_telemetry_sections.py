from __future__ import annotations

from datetime import datetime, timezone

from robot_sim.model.render_telemetry import RenderTelemetryEvent
from robot_sim.presentation.render_telemetry_state import build_render_telemetry_panel_state


def test_render_telemetry_panel_state_exposes_structured_log_sections() -> None:
    state = build_render_telemetry_panel_state(
        [
            RenderTelemetryEvent(
                sequence=1,
                capability='scene_3d',
                event_kind='state_changed',
                severity='warning',
                status='degraded',
                message='fallback enabled',
                source='unit_test',
                emitted_at=datetime.now(timezone.utc),
            )
        ]
    )
    sections = {section.section_id: section for section in state.log_sections}
    assert set(sections) == {'events', 'spans', 'counters', 'backend_performance', 'timeline'}
    assert 'fallback enabled' in sections['events'].body_text
