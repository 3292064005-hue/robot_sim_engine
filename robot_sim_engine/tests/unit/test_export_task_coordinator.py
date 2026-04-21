from types import SimpleNamespace

from robot_sim.presentation.coordinators.export_task_coordinator import ExportTaskCoordinator


class DummyThreader:
    def __init__(self):
        self.started = []

    def start(self, **kwargs):
        self.started.append(kwargs)
        return SimpleNamespace(task_id='export-1', task_kind=kwargs.get('task_kind', 'unknown'))


class DummyWindow:
    def __init__(self):
        self.runtime_facade = SimpleNamespace(state=SimpleNamespace(trajectory=SimpleNamespace()))
        self.export_workflow = SimpleNamespace(
            export_trajectory_bundle=lambda _name='trajectory_bundle.npz': 'trajectory_bundle.npz',
            export_trajectory=lambda _name='trajectory_bundle.npz': 'trajectory_bundle.npz',
            export_trajectory_metrics=lambda _name, _metrics: 'trajectory_metrics.json',
            export_session=lambda _name='session.json', telemetry_detail='full': 'session.json',
            export_package=lambda _name='package.zip', telemetry_detail='minimal': 'package.zip',
            export_benchmark=lambda _name='benchmark_report.json': 'benchmark.json',
            export_benchmark_cases_csv=lambda _name='benchmark_cases.csv': 'benchmark.csv',
        )
        self.metrics_service = SimpleNamespace(summarize_trajectory=lambda _traj: {'mode': 'joint'})
        self.threader = DummyThreader()
        self.status_panel = SimpleNamespace(messages=[], append=lambda message: self.status_panel.messages.append(message))
        self.project_export_messages = lambda *messages: [self.status_panel.append(message) for message in messages]
        self.project_task_started = lambda task_kind, message: self.status_panel.append(f'{task_kind}:{message}')
        self.project_task_registered = lambda task_id, task_kind: self.status_panel.append(f'registered:{task_kind}:{task_id}')
        self._projected = []
        self._project_exception = lambda exc, title='错误': self._projected.append((title, str(exc)))
        self.on_worker_failed = lambda failure: self._projected.append(('failed', str(failure)))
        self.on_worker_cancelled = lambda: self._projected.append(('cancelled', 'cancelled'))


def test_export_task_coordinator_routes_exports_through_background_tasks():
    window = DummyWindow()
    coord = ExportTaskCoordinator(window, runtime=window.runtime_facade, export=window.export_workflow, threader=window.threader, metrics_service=window.metrics_service)
    coord.export_trajectory_bundle()
    coord.export_session()
    coord.export_package()
    coord.export_benchmark()

    assert [item['task_kind'] for item in window.threader.started] == ['export', 'export', 'export', 'export']
    assert window.status_panel.messages == [
        'export:轨迹包导出任务已启动',
        'registered:export:export-1',
        'export:会话导出任务已启动',
        'registered:export:export-1',
        'export:完整导出包任务已启动',
        'registered:export:export-1',
        'export:Benchmark 导出任务已启动',
        'registered:export:export-1',
    ]

    # Simulate worker completion callbacks to verify the projected success messages.
    for start in window.threader.started:
        payload = start['worker']._invoke_with_control()
        start['on_finished'](payload)

    assert window.status_panel.messages[-6:] == [
        '轨迹包已导出：trajectory_bundle.npz',
        '轨迹指标已导出：trajectory_metrics.json',
        '会话已导出：session.json',
        '完整导出包已生成：package.zip',
        'Benchmark 报告已导出：benchmark.json',
        'Benchmark 明细已导出：benchmark.csv',
    ]
