from __future__ import annotations

import json

from robot_sim.application.services.export_service import ExportService
from robot_sim.application.use_cases.export_package import ExportPackageUseCase
from robot_sim.application.use_cases.export_report import ExportReportUseCase
from robot_sim.application.use_cases.save_session import SaveSessionUseCase
from robot_sim.application.services.package_service import PackageService
from robot_sim.model.benchmark_report import BenchmarkReport
from robot_sim.model.session_state import SessionState
from robot_sim.presentation.controllers.export_controller import ExportController
from robot_sim.presentation.state_store import StateStore


class _WorkflowFacadeStub:
    def __init__(self, exporter: ExportService, save_session_uc: SaveSessionUseCase, export_package_uc: ExportPackageUseCase | None):
        self._exporter = exporter
        self._save_session_uc = save_session_uc
        self._export_package_uc = export_package_uc

    def export_trajectory_bundle(self, name, trajectory, *, robot_id=None, solver_id=None, planner_id=None):
        return self._exporter.save_trajectory_bundle(name, trajectory, robot_id=robot_id, solver_id=solver_id, planner_id=planner_id)

    def export_benchmark_report(self, name: str, payload: dict[str, object]):
        return self._exporter.save_benchmark_report(name, payload)

    def export_session(self, name: str, state: SessionState, **kwargs):
        return self._save_session_uc.execute(name, state, **kwargs)

    def export_package(self, name: str, files, **manifest_kwargs):
        if self._export_package_uc is None:
            raise RuntimeError('package export not configured')
        return self._export_package_uc.execute(name, files, **manifest_kwargs)


def test_export_controller_exports_benchmark_json(tmp_path):
    state = StateStore(SessionState(benchmark_report=BenchmarkReport(robot='Planar', num_cases=1, success_rate=1.0)))
    exporter = ExportService(tmp_path)
    save_session_uc = SaveSessionUseCase(exporter)
    controller = ExportController(
        state,
        exporter,
        ExportReportUseCase(exporter),
        save_session_uc,
        application_workflow=_WorkflowFacadeStub(exporter, save_session_uc, None),
    )
    path = controller.export_benchmark('bench.json')
    assert path.exists()


class _DummyRuntimeFacade:
    project_root = '.'
    resource_root = '.'
    config_root = '.'
    export_root = '.'
    runtime_context = {'layout_mode': 'source'}
    startup_summary = {'startup_mode': 'headless'}
    effective_config_snapshot = {
        'profile': 'default',
        'app': {'window': {'title': 'Robot Sim Engine'}},
        'solver': {'ik': {'solver_id': 'dls'}},
        'resolution': {'profile_source': 'configs/profiles/default.yaml'},
    }


def test_export_controller_session_manifest_uses_effective_config_snapshot(tmp_path):
    state = StateStore(SessionState())
    exporter = ExportService(tmp_path)
    save_session_uc = SaveSessionUseCase(exporter)
    controller = ExportController(
        state,
        exporter,
        ExportReportUseCase(exporter),
        save_session_uc,
        runtime_facade=_DummyRuntimeFacade(),
        application_workflow=_WorkflowFacadeStub(exporter, save_session_uc, None),
    )
    path = controller.export_session('session.json')
    payload = json.loads(path.read_text(encoding='utf-8'))
    manifest = payload['manifest']
    assert manifest['config_snapshot']['profile'] == 'default'
    assert manifest['config_snapshot']['app']['window']['title'] == 'Robot Sim Engine'
    assert manifest['config_snapshot']['resolution']['profile_source'] == 'configs/profiles/default.yaml'



def test_export_controller_session_manifest_supports_minimal_telemetry(tmp_path):
    state = StateStore(SessionState())
    exporter = ExportService(tmp_path)
    save_session_uc = SaveSessionUseCase(exporter)
    controller = ExportController(
        state,
        exporter,
        ExportReportUseCase(exporter),
        save_session_uc,
        runtime_facade=_DummyRuntimeFacade(),
        application_workflow=_WorkflowFacadeStub(exporter, save_session_uc, None),
    )
    path = controller.export_session('session.json', telemetry_detail='minimal')
    payload = json.loads(path.read_text(encoding='utf-8'))
    assert payload['render_telemetry']['detail'] == 'minimal'
    assert 'events' not in payload['render_telemetry']


def test_export_controller_package_defaults_to_minimal_session_telemetry(tmp_path):
    state = StateStore(SessionState())
    exporter = ExportService(tmp_path)
    package_service = PackageService(tmp_path)
    export_package_uc = ExportPackageUseCase(package_service)
    save_session_uc = SaveSessionUseCase(exporter)
    controller = ExportController(
        state,
        exporter,
        ExportReportUseCase(exporter),
        save_session_uc,
        export_package_uc=export_package_uc,
        runtime_facade=_DummyRuntimeFacade(),
        application_workflow=_WorkflowFacadeStub(exporter, save_session_uc, export_package_uc),
    )
    bundle_path = controller.export_package('bundle.zip')
    assert bundle_path.exists()
    import json as _json
    import zipfile as _zipfile
    with _zipfile.ZipFile(bundle_path) as zf:
        session_payload = _json.loads(zf.read('session.json').decode('utf-8'))
    assert session_payload['render_telemetry']['detail'] == 'minimal'


def test_export_controller_session_manifest_preserves_capability_snapshot_without_runtime_facade(tmp_path):
    state = StateStore(SessionState(capability_matrix={'scene_features': {'validation_fidelity': 'aabb_v1'}}))
    exporter = ExportService(tmp_path)
    save_session_uc = SaveSessionUseCase(exporter)
    controller = ExportController(
        state,
        exporter,
        ExportReportUseCase(exporter),
        save_session_uc,
        runtime_facade=None,
        application_workflow=_WorkflowFacadeStub(exporter, save_session_uc, None),
    )
    path = controller.export_session('session.json')
    payload = json.loads(path.read_text(encoding='utf-8'))
    manifest = payload['manifest']
    assert manifest['capability_snapshot'] == {'scene_features': {'validation_fidelity': 'aabb_v1'}}


def test_export_controller_package_manifest_preserves_capability_snapshot_without_runtime_facade(tmp_path):
    state = StateStore(SessionState(capability_matrix={'scene_features': {'validation_fidelity': 'aabb_v1'}}))
    exporter = ExportService(tmp_path)
    package_service = PackageService(tmp_path)
    export_package_uc = ExportPackageUseCase(package_service)
    save_session_uc = SaveSessionUseCase(exporter)
    controller = ExportController(
        state,
        exporter,
        ExportReportUseCase(exporter),
        save_session_uc,
        export_package_uc=export_package_uc,
        runtime_facade=None,
        application_workflow=_WorkflowFacadeStub(exporter, save_session_uc, export_package_uc),
    )
    bundle_path = controller.export_package('bundle.zip')
    assert bundle_path.exists()
    import json as _json
    import zipfile as _zipfile
    with _zipfile.ZipFile(bundle_path) as zf:
        manifest = _json.loads(zf.read('manifest.json').decode('utf-8'))
    assert manifest['capability_snapshot'] == {'scene_features': {'validation_fidelity': 'aabb_v1'}}
