from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

from robot_sim.application.services.export_service import ExportService
from robot_sim.core.collision.scene import PlanningScene
from robot_sim.model.imported_robot_package import ImportedRobotPackage
from robot_sim.model.robot_geometry_model import RobotGeometryModel
from robot_sim.model.session_state import SessionState


def test_save_session_projects_rich_scene_and_import_fidelity(tmp_path: Path, planar_spec) -> None:
    export = ExportService(tmp_path)
    imported = ImportedRobotPackage(
        package_id='demo',
        importer_id='urdf_model',
        source_path='demo.urdf',
        runtime_model=planar_spec.runtime_model,
        geometry_model=RobotGeometryModel(metadata={'geometry_contract': 'declaration_validation_render'}),
        fidelity_breakdown={
            'roadmap_level': 'serial_with_collision',
            'downgrade_records': [{'kind': 'fixed_joints_collapsed', 'detail': 'demo'}],
            'degradation_reasons': ['fixed_joints_collapsed'],
        },
    )
    state = SessionState(planning_scene=PlanningScene())
    state.robot_spec = replace(planar_spec, imported_package=imported)
    out = export.save_session('session.json', state)
    payload = json.loads(out.read_text(encoding='utf-8'))
    fidelity = payload['scene_fidelity_summary']
    assert fidelity['precision'] == 'broad_phase'
    assert fidelity['stable_surface'] is True
    assert fidelity['promotion_state'] == 'stable'
    assert fidelity['scene_validation_mode'] == 'aabb_planning_scene'
    assert payload['import_fidelity_breakdown']['downgrade_records'][0]['kind'] == 'fixed_joints_collapsed'
