from types import SimpleNamespace

from robot_sim.presentation.coordinators.benchmark_task_coordinator import BenchmarkTaskCoordinator
from robot_sim.presentation.state_events import BenchmarkReportProjectedEvent


class DummyStore:
    def __init__(self):
        self.events = []
        self.state = SimpleNamespace()

    def dispatch(self, event):
        self.events.append(event)
        return self.state


class DummyThreader:
    def __init__(self):
        self.started = None

    def start(self, **kwargs):
        self.started = kwargs
        return SimpleNamespace(task_id='task-1', task_kind=kwargs['task_kind'])


class DummyWindow:
    def __init__(self):
        self.controller = SimpleNamespace(
            state=SimpleNamespace(robot_spec=object()),
            benchmark_uc=object(),
            build_benchmark_config=lambda **kwargs: kwargs,
            state_store=DummyStore(),
        )
        self.runtime_facade = SimpleNamespace(state=SimpleNamespace(robot_spec=object()), state_store=DummyStore())
        self.motion_workflow = SimpleNamespace(benchmark_use_case=object(), build_benchmark_config=lambda **kwargs: kwargs)
        self.threader = DummyThreader()
        self.metrics_service = SimpleNamespace(summarize_benchmark=lambda report: {'cases': 1})
        self.status_panel = SimpleNamespace(messages=[], append=lambda message: self.status_panel.messages.append(message))
        self.read_solver_kwargs = lambda: {'mode': 'dls'}
        self._set_busy_calls = []
        self.project_task_started = lambda task_kind, message: (self._set_busy_calls.append((True, task_kind)), self.status_panel.append(message))
        self.project_task_registered = lambda task_id, task_kind: self.runtime_facade.state_store.dispatch(SimpleNamespace(task_id=task_id, task_kind=task_kind))
        self.on_benchmark_finished = lambda report: None
        self.on_worker_failed = lambda failure: None
        self.on_worker_cancelled = lambda: None
        self.project_benchmark_result = lambda report, summary: self.status_panel.append(f'benchmark:{summary["cases"]}')
        self._projected = []
        self._project_exception = lambda exc, title='错误': self._projected.append((title, str(exc)))
        self.project_busy_state = lambda is_busy, reason='': self._set_busy_calls.append((bool(is_busy), reason))


def test_benchmark_task_coordinator_starts_worker_and_dispatches_task_state():
    window = DummyWindow()
    BenchmarkTaskCoordinator(window, runtime=window.runtime_facade, benchmark=window.motion_workflow, threader=window.threader).run()
    assert window.threader.started['task_kind'] == 'benchmark'
    assert window._set_busy_calls[0] == (True, 'benchmark')


def test_benchmark_task_coordinator_dispatches_benchmark_report_on_finish():
    window = DummyWindow()
    coordinator = BenchmarkTaskCoordinator(window, runtime=window.runtime_facade, benchmark=window.motion_workflow, threader=window.threader)
    report = SimpleNamespace(num_cases=1)
    coordinator.handle_finished(report)
    assert any(isinstance(event, BenchmarkReportProjectedEvent) for event in window.runtime_facade.state_store.events)
    assert 'benchmark:1' in window.status_panel.messages
