from __future__ import annotations

import json
import zipfile

from robot_sim.application.services.package_service import PackageService


def test_package_service_exports_zip_with_manifest(tmp_path):
    service = PackageService(tmp_path)
    payload = tmp_path / 'a.json'
    payload.write_text('{"ok": true}', encoding='utf-8')
    manifest = service.build_manifest(robot_id='planar', files=[payload.name])
    path = service.export_package('bundle.zip', [payload], manifest)
    assert path.exists()
    with zipfile.ZipFile(path) as zf:
        assert 'a.json' in zf.namelist()
        meta = json.loads(zf.read('manifest.json').decode('utf-8'))
        assert meta['robot_id'] == 'planar'



def test_package_service_manifest_records_bundle_contract_snapshots(tmp_path):
    service = PackageService(tmp_path)
    manifest = service.build_manifest(
        robot_id='planar',
        files=['session.json'],
        bundle_kind='artifact_bundle',
        bundle_contract='artifact_audit_bundle',
        replayable=False,
        environment={'layout_mode': 'source'},
        config_snapshot={'profile': 'default'},
        scene_snapshot={'scene_fidelity': 'generated'},
        plugin_snapshot={'catalog_counts': {'enabled': 0}},
    )
    assert manifest.bundle_kind == 'artifact_bundle'
    assert manifest.bundle_contract == 'artifact_audit_bundle'
    assert manifest.replayable is False
    assert manifest.environment['layout_mode'] == 'source'
    assert manifest.config_snapshot['profile'] == 'default'
    assert manifest.scene_snapshot['scene_fidelity'] == 'generated'
    assert manifest.plugin_snapshot['catalog_counts']['enabled'] == 0
