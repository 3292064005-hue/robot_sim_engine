from __future__ import annotations

from types import SimpleNamespace

from robot_sim.presentation.workflow_services import ExportWorkflowService, MotionWorkflowService, RobotWorkflowService


class _Registry:
    def list_names(self):
        return ['planar']

    def list_entries(self):
        return ['entry']

    def list_specs(self):
        return ['spec']


class _ImporterRegistry:
    def descriptors(self):
        return ['yaml']


class _RobotController:
    def load_robot(self, name):
        return {'loaded': name}

    def import_robot(self, source, importer_id=None):
        return {'source': source, 'importer_id': importer_id}

    def build_robot_from_editor(self, existing_spec, rows, home_q):
        return {'existing_spec': existing_spec, 'rows': rows, 'home_q': home_q}

    def save_current_robot(self, rows=None, home_q=None, name=None):
        return {'rows': rows, 'home_q': home_q, 'name': name}

    def run_fk(self, q=None):
        return {'q': q}

    def sample_ee_positions(self, q_samples):
        return {'samples': q_samples}


class _IKController:
    def build_target_pose(self, values6, orientation_mode='rvec'):
        return {'values6': values6, 'orientation_mode': orientation_mode}

    def build_ik_request(self, values6, **kwargs):
        return {'values6': values6, 'kwargs': kwargs}

    def apply_ik_result(self, req, result):
        self.applied = (req, result)

    def run_ik(self, values6, **kwargs):
        return {'values6': values6, 'kwargs': kwargs}


class _TrajectoryController:
    def trajectory_goal_or_raise(self):
        return 'goal'

    def build_trajectory_request(self, **kwargs):
        return kwargs

    def plan_trajectory(self, **kwargs):
        return {'planned': kwargs}

    def apply_trajectory(self, traj):
        self.applied = traj


class _BenchmarkController:
    def build_benchmark_config(self, **kwargs):
        return kwargs

    def run_benchmark(self, config=None):
        return {'benchmark': config}


class _PlaybackController:
    def current_playback_frame(self):
        return 'current'

    def set_playback_frame(self, frame_idx):
        return frame_idx

    def next_playback_frame(self):
        return 'next'

    def set_playback_options(self, *, speed_multiplier=None, loop_enabled=None):
        self.options = (speed_multiplier, loop_enabled)

    def ensure_playback_ready(self, *, strict=True):
        self.strict = strict


class _ExportController:
    def export_trajectory_bundle(self, name='trajectory_bundle.npz'):
        return name

    def export_trajectory(self, name='trajectory_bundle.npz'):
        return name

    def export_trajectory_metrics(self, name='trajectory_metrics.json', metrics=None):
        return name, metrics

    def export_benchmark(self, name='benchmark_report.json'):
        return name

    def export_benchmark_cases_csv(self, name='benchmark_cases.csv'):
        return name

    def export_session(self, name='session.json', *, telemetry_detail='full'):
        return name, telemetry_detail

    def export_package(self, name='robot_sim_package.zip', *, telemetry_detail='minimal'):
        return name, telemetry_detail


def test_robot_workflow_uses_registry_and_controller_directly():
    workflow = RobotWorkflowService(
        registry=_Registry(),
        controller=_RobotController(),
        importer_registry=_ImporterRegistry(),
    )
    assert workflow.robot_names() == ['planar']
    assert workflow.robot_entries() == ['entry']
    assert workflow.available_specs() == ['spec']
    assert workflow.importer_entries() == ['yaml']
    assert workflow.load_robot('planar') == {'loaded': 'planar'}
    assert workflow.import_robot('demo.urdf', importer_id='urdf') == {'source': 'demo.urdf', 'importer_id': 'urdf'}


def test_motion_workflow_uses_controllers_directly():
    solver_settings = SimpleNamespace(
        ik=SimpleNamespace(as_dict=lambda: {'mode': 'dls'}),
        trajectory=SimpleNamespace(as_dict=lambda: {'dt': 0.02}),
    )
    ik_controller = _IKController()
    trajectory_controller = _TrajectoryController()
    benchmark_controller = _BenchmarkController()
    playback_controller = _PlaybackController()
    workflow = MotionWorkflowService(
        solver_settings=solver_settings,
        ik_controller=ik_controller,
        trajectory_controller=trajectory_controller,
        benchmark_controller=benchmark_controller,
        playback_controller=playback_controller,
        playback_service='playback_service',
        ik_use_case='ik_uc',
        trajectory_use_case='traj_uc',
        benchmark_use_case='bench_uc',
    )
    assert workflow.solver_defaults() == {'mode': 'dls'}
    assert workflow.trajectory_defaults() == {'dt': 0.02}
    assert workflow.build_target_pose([0, 0, 0, 0, 0, 0])['orientation_mode'] == 'rvec'
    assert workflow.build_ik_request([0, 0, 0, 0, 0, 0], seed=1)['kwargs']['seed'] == 1
    workflow.apply_ik_result('req', 'result')
    assert ik_controller.applied == ('req', 'result')
    assert workflow.plan_trajectory(duration=1.0) == {'planned': {'duration': 1.0}}
    workflow.apply_trajectory('traj')
    assert trajectory_controller.applied == 'traj'
    workflow.set_playback_options(speed_multiplier=2.0, loop_enabled=True)
    assert playback_controller.options == (2.0, True)
    workflow.ensure_playback_ready(strict=False)
    assert playback_controller.strict is False


def test_export_workflow_exposes_telemetry_detail_controls():
    workflow = ExportWorkflowService(export_controller=_ExportController())
    assert workflow.export_session('session.json', telemetry_detail='minimal') == ('session.json', 'minimal')
    assert workflow.export_package('bundle.zip') == ('bundle.zip', 'minimal')
