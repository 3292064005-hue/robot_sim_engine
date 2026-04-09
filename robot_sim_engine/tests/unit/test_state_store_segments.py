from __future__ import annotations

from robot_sim.model.session_state import SessionState
from robot_sim.presentation.state_store import StateStore


class _CapabilityMatrix:
    def as_dict(self):
        return {'solver': {'available': True}}


class _Presentation:
    user_message = 'boom'
    log_payload = {'code': 'x'}
    error_code = 'E_X'
    title = 'Error'
    severity = 'critical'
    remediation_hint = 'retry'


class _TaskSnapshot:
    task_id = 't-1'
    task_kind = 'ik'
    state = 'running'
    stop_reason = ''
    correlation_id = 'corr-1'


def test_state_store_exposes_segmented_substores_without_breaking_facade() -> None:
    store = StateStore(SessionState())

    store.session.patch_scene({'robots': 1}, scene_revision=2)
    store.patch_capabilities(_CapabilityMatrix())
    store.task.patch_task(_TaskSnapshot())
    store.patch_error(_Presentation())
    store.patch_warning('warn', 'be careful')
    store.render.patch_render_capability('plots', {'status': 'degraded', 'backend': 'pyqtgraph'})

    snapshot = store.snapshot()
    assert snapshot.scene_summary == {'robots': 1}
    assert snapshot.scene_revision == 2
    assert snapshot.capability_matrix == {'solver': {'available': True}}
    assert snapshot.active_task_id == 't-1'
    assert snapshot.last_error_code == 'E_X'
    assert snapshot.active_warning_codes == ('warn',)
    assert snapshot.render_runtime.plots.backend == 'pyqtgraph'


def test_render_segment_notify_does_not_wake_unrelated_segment_subscribers() -> None:
    store = StateStore(SessionState())
    seen: list[str] = []

    store.subscribe(lambda state: seen.append('global'), segment='global')
    store.subscribe(lambda state: seen.append('task'), segment='task')
    store.subscribe(lambda state: seen.append('render'), segment='render')

    store.record_render_sampling_counter('screenshot', 'drawable_samples', value=1.0)

    assert seen == ['global', 'render']


def test_state_store_notify_isolates_subscriber_failures() -> None:
    store = StateStore(SessionState())
    seen: list[str] = []

    def _broken(_state) -> None:
        raise RuntimeError('subscriber boom')

    store.subscribe(_broken)
    store.subscribe(lambda state: seen.append('healthy'))

    store.patch(is_busy=True)

    assert seen == ['healthy']
