from robot_sim.application.services.export_service import ExportService


def test_manifest_exposes_only_canonical_fields(tmp_path):
    service = ExportService(tmp_path)
    manifest = service.build_manifest(robot_id='r')
    assert 'migration_aliases' not in manifest
    assert 'compatibility_notes' not in manifest
    assert manifest['schema_version']
    assert manifest['export_version']
    assert manifest['producer_version']
