from __future__ import annotations

from pathlib import Path

from robot_sim.domain.enums import ImporterFidelity
from robot_sim.model.canonical_robot_model import CanonicalRobotModel
from robot_sim.model.robot_geometry import RobotGeometry
from robot_sim.model.robot_links import RobotJointSpec, RobotLinkSpec
from robot_sim.model.robot_model_bundle import RobotModelBundle


class YAMLRobotImporter:
    importer_id = 'yaml'

    def __init__(self, robot_registry) -> None:
        self._robot_registry = robot_registry

    def capabilities(self) -> dict[str, object]:
        return {
            'source_format': 'yaml',
            'fidelity': ImporterFidelity.NATIVE.value,
            'family': 'config',
        }

    def load(self, source, **kwargs):
        path = Path(source)
        import yaml
        data = yaml.safe_load(path.read_text(encoding='utf-8')) or {}
        spec = self._robot_registry.from_dict(data)
        geometry = RobotGeometry.simple_capsules(spec.dof)
        canonical_model = spec.canonical_model or self._build_canonical_model(spec)
        spec = type(spec)(
            name=spec.name,
            dh_rows=spec.execution_rows,
            base_T=spec.base_T,
            tool_T=spec.tool_T,
            home_q=spec.home_q,
            display_name=spec.display_name,
            description=spec.description,
            metadata=spec.metadata,
            joint_names=spec.joint_names,
            link_names=spec.link_names,
            joint_types=spec.joint_types,
            joint_axes=spec.joint_axes,
            joint_limits=spec.joint_limits,
            structured_joints=spec.structured_joints,
            structured_links=spec.structured_links,
            kinematic_source=spec.kinematic_source,
            geometry_bundle_ref=spec.geometry_bundle_ref,
            collision_bundle_ref=spec.collision_bundle_ref,
            source_model_summary=spec.source_model_summary,
            canonical_model=canonical_model,
        )
        return RobotModelBundle(
            spec=spec,
            geometry=geometry,
            collision_geometry=geometry,
            fidelity=ImporterFidelity.NATIVE.value,
            warnings=(),
            source_path=str(path),
            importer_id=self.importer_id,
            metadata={'source_format': 'yaml'},
            source_model_summary={
                'source_format': 'yaml',
                'joint_count': int(spec.dof),
                'link_count': int(max(len(spec.link_names), spec.dof + 1 if spec.dof > 0 else 0)),
                'has_visual': bool(spec.geometry_available),
                'has_collision': bool(spec.collision_bundle_ref),
            },
        )

    @staticmethod
    def _build_canonical_model(spec):
        if spec.structured_joints:
            joints = tuple(spec.structured_joints)
        else:
            joints = tuple(
                RobotJointSpec(
                    name=spec.runtime_joint_names[index],
                    parent_link=spec.runtime_link_names[index],
                    child_link=spec.runtime_link_names[index + 1],
                    joint_type=row.joint_type,
                    axis=spec.joint_axes[index] if index < len(spec.joint_axes) else [0.0, 0.0, 1.0],
                    limit=spec.runtime_joint_limits[index],
                    metadata={'source': 'yaml', 'execution_adapter_row': index},
                )
                for index, row in enumerate(spec.execution_rows)
            )
        if spec.structured_links:
            links = tuple(spec.structured_links)
        else:
            links = tuple(
                RobotLinkSpec(name=name, metadata={'source': 'yaml'})
                for name in spec.runtime_link_names
            )
        root_link = spec.runtime_link_names[0] if spec.runtime_link_names else ''
        return CanonicalRobotModel(
            name=spec.name,
            joints=joints,
            links=links,
            root_link=root_link,
            source_format='yaml',
            execution_adapter='canonical_dh_chain',
            execution_rows=tuple(spec.execution_rows),
            fidelity=ImporterFidelity.NATIVE.value,
            metadata={'generated_from': 'yaml_importer', 'execution_surface': 'canonical_model'},
        )
