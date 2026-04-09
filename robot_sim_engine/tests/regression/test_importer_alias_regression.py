from robot_sim.app.container import build_container


<<<<<<< HEAD
def test_importer_alias_urdf_maps_to_canonical_urdf_model(tmp_path):
    container = build_container(tmp_path)
    importer = container.importer_registry.resolve('urdf')
    canonical = container.importer_registry.resolve('urdf_model')
    assert importer is canonical


def test_importer_alias_yml_maps_to_canonical_yaml(tmp_path):
    container = build_container(tmp_path)
    importer = container.importer_registry.resolve('yml')
    canonical = container.importer_registry.resolve('yaml')
=======
def test_importer_alias_urdf_maps_to_canonical_urdf_skeleton(tmp_path):
    container = build_container(tmp_path)
    importer = container.importer_registry.resolve('urdf')
    canonical = container.importer_registry.resolve('urdf_skeleton')
>>>>>>> 3ed78e647985c6d680c085e4480d898855278db3
    assert importer is canonical
