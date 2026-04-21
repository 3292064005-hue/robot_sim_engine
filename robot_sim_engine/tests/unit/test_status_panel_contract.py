from __future__ import annotations

from robot_sim.presentation.qt_runtime import QApplication
from robot_sim.presentation.status_panel_state import build_render_runtime_panel_state
from robot_sim.presentation.widgets.status_panel import StatusPanel


def _app():
    return QApplication.instance() or QApplication([])


def test_status_panel_renders_structured_render_runtime_projection() -> None:
    _app()
    panel = StatusPanel()
    state = build_render_runtime_panel_state(
        {
            'scene_3d': {
                'status': 'unsupported',
                'backend': 'pyvistaqt',
                'reason': 'backend_dependency_missing',
                'message': '缺少 3D 后端依赖',
            },
            'plots': {
                'status': 'degraded',
                'backend': 'pyqtgraph',
                'reason': 'operation_failed',
            },
            'screenshot': {
                'status': 'available',
                'backend': 'snapshot_renderer',
            },
        }
    )

    panel.set_render_runtime(state)

    assert panel.render_summary.text() == state.summary_text
    assert panel.render_detail_labels['scene_3d'].text() == 'pyvistaqt / backend_dependency_missing'
    assert panel.render_detail_labels['plots'].text() == 'pyqtgraph / operation_failed'
    assert panel.render_detail_labels['screenshot'].text() == 'snapshot_renderer'
    assert '缺少 3D 后端依赖' in panel.render_detail_labels['scene_3d'].toolTip()


def test_render_runtime_panel_state_exposes_separate_metric_and_detail_views() -> None:
    state = build_render_runtime_panel_state(
        {
            'scene_3d': {'status': 'degraded', 'backend': 'pyvistaqt', 'reason': 'operation_failed'},
            'plots': {'status': 'available', 'backend': 'pyqtgraph'},
            'screenshot': {'status': 'available', 'backend': 'snapshot_renderer'},
        }
    )

    assert state.metric_payload['scene_3d'].startswith('降级')
    assert state.detail_rows['scene_3d'] == 'pyvistaqt / operation_failed'
    assert state.detail_rows['plots'] == 'pyqtgraph'


def test_status_panel_renders_runtime_advice_projection() -> None:
    _app()
    panel = StatusPanel()
    state = build_render_runtime_panel_state(
        {
            'scene_3d': {'status': 'available', 'backend': 'pyvistaqt'},
            'plots': {'status': 'available', 'backend': 'pyqtgraph'},
            'screenshot': {'status': 'available', 'backend': 'snapshot_renderer'},
        },
        {
            'recommendations': [
                {
                    'capability': 'plots',
                    'backend': 'pyqtgraph',
                    'action': 'reduce_sampling_rate',
                    'rationale': 'latency high',
                }
            ]
        },
    )
    panel.set_render_runtime(state)
    assert 'reduce_sampling_rate' in panel.render_advice_summary.text()
    assert 'reduce_sampling_rate' in panel.render_detail_labels['plots'].text()
