from robot_sim.app.container import build_container


def test_importer_descriptor_contains_fidelity(project_root):
    container = build_container(project_root)
<<<<<<< HEAD
    descriptor = {d.importer_id: d for d in container.importer_registry.descriptors()}['urdf_model']
    assert descriptor.metadata['fidelity'] == 'serial_kinematics'
=======
    descriptor = {d.importer_id: d for d in container.importer_registry.descriptors()}['urdf_skeleton']
    assert descriptor.metadata['fidelity'] == 'approximate'
>>>>>>> 3ed78e647985c6d680c085e4480d898855278db3
