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


def test_export_controller_exports_benchmark_json(tmp_path):
    state = StateStore(SessionState(benchmark_report=BenchmarkReport(robot='Planar', num_cases=1, success_rate=1.0)))
    exporter = ExportService(tmp_path)
    controller = ExportController(state, exporter, ExportReportUseCase(exporter), SaveSessionUseCase(exporter))
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
    controller = ExportController(
        state,
        exporter,
        ExportReportUseCase(exporter),
        SaveSessionUseCase(exporter),
        runtime_facade=_DummyRuntimeFacade(),
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
    controller = ExportController(
        state,
        exporter,
        ExportReportUseCase(exporter),
        SaveSessionUseCase(exporter),
        runtime_facade=_DummyRuntimeFacade(),
    )
    path = controller.export_session('session.json', telemetry_detail='minimal')
    payload = json.loads(path.read_text(encoding='utf-8'))
    assert payload['render_telemetry']['detail'] == 'minimal'
    assert 'events' not in payload['render_telemetry']


def test_export_controller_package_defaults_to_minimal_session_telemetry(tmp_path):
    state = StateStore(SessionState())
    exporter = ExportService(tmp_path)
    package_service = PackageService(tmp_path)
    controller = ExportController(
        state,
        exporter,
        ExportReportUseCase(exporter),
        SaveSessionUseCase(exporter),
        export_package_uc=ExportPackageUseCase(package_service),
        runtime_facade=_DummyRuntimeFacade(),
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
    controller = ExportController(
        state,
        exporter,
        ExportReportUseCase(exporter),
        SaveSessionUseCase(exporter),
        runtime_facade=None,
    )
    path = controller.export_session('session.json')
    payload = json.loads(path.read_text(encoding='utf-8'))
    manifest = payload['manifest']
    assert manifest['capability_snapshot'] == {'scene_features': {'validation_fidelity': 'aabb_v1'}}


def test_export_controller_package_manifest_preserves_capability_snapshot_without_runtime_facade(tmp_path):
    state = StateStore(SessionState(capability_matrix={'scene_features': {'validation_fidelity': 'aabb_v1'}}))
    exporter = ExportService(tmp_path)
    package_service = PackageService(tmp_path)
    controller = ExportController(
        state,
        exporter,
        ExportReportUseCase(exporter),
        SaveSessionUseCase(exporter),
        export_package_uc=ExportPackageUseCase(package_service),
        runtime_facade=None,
    )
    bundle_path = controller.export_package('bundle.zip')
    assert bundle_path.exists()
    import json as _json
    import zipfile as _zipfile
    with _zipfile.ZipFile(bundle_path) as zf:
        manifest = _json.loads(zf.read('manifest.json').decode('utf-8'))
    assert manifest['capability_snapshot'] == {'scene_features': {'validation_fidelity': 'aabb_v1'}}
