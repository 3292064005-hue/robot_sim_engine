from robot_sim.app.container import build_container


def test_yaml_and_urdf_importers_expose_fidelity(project_root):
    container = build_container(project_root)
    descriptors = {d.importer_id: d.metadata for d in container.importer_registry.descriptors()}
    assert descriptors['yaml']['fidelity'] == 'native'
<<<<<<< HEAD
    assert descriptors['urdf_model']['fidelity'] == 'serial_kinematics'
=======
>>>>>>> 3ed78e647985c6d680c085e4480d898855278db3
    assert descriptors['urdf_skeleton']['fidelity'] == 'approximate'
