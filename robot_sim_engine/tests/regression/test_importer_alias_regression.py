from robot_sim.app.container import build_container


def test_importer_alias_urdf_maps_to_canonical_urdf_model(tmp_path):
    container = build_container(tmp_path)
    importer = container.importer_registry.resolve('urdf')
    canonical = container.importer_registry.resolve('urdf_model')
    assert importer is canonical


def test_importer_alias_yml_maps_to_canonical_yaml(tmp_path):
    container = build_container(tmp_path)
    importer = container.importer_registry.resolve('yml')
    canonical = container.importer_registry.resolve('yaml')
    assert importer is canonical
