from __future__ import annotations

from pathlib import Path

from robot_sim.app.contracts import MainControllerContainerProtocol, build_presentation_bootstrap_bundle
from robot_sim.domain.capabilities import CapabilityDescriptor
from robot_sim.presentation.main_controller_compat import build_compatibility_method, compatibility_method_names
from robot_sim.presentation.main_controller_support import (
    build_presentation_collaborators,
    install_main_controller_collaborators,
)


class MainController:
    """Facade that exposes application services to the Qt layer.

    ``MainController`` now keeps only canonical bootstrap state plus a compatibility
    attribute bridge. Historical method names are projected lazily through
    :mod:`robot_sim.presentation.main_controller_compat` so the controller itself stays a
    thin presentation shell over workflow services.
    """

    _COMPATIBILITY_METHOD_NAMES = set(compatibility_method_names())

    def __init__(self, project_root: str | Path, *, container: MainControllerContainerProtocol) -> None:
        if container is None:
            raise ValueError('MainController requires an explicit application container')
        self.project_root = Path(project_root)
        self.container = container
        self.bootstrap_bundle = build_presentation_bootstrap_bundle(self.project_root, container=container)
        self.runtime_paths = self.bootstrap_bundle.services.runtime_paths
        self.config_service = self.bootstrap_bundle.services.config_service
        self.app_settings = self.config_service.load_app_settings()
        self.solver_settings = self.config_service.load_solver_settings()
        self.app_config = self.app_settings.as_dict()
        self.solver_config = self.solver_settings.as_dict()
        self.registry = self.bootstrap_bundle.registries.robot_registry
        self.exporter = self.bootstrap_bundle.services.export_service
        self.metrics_service = self.bootstrap_bundle.services.metrics_service
        self.capability_service = self.bootstrap_bundle.services.capability_service
        self.module_status_service = self.bootstrap_bundle.services.module_status_service
        self.task_error_mapper = self.bootstrap_bundle.services.task_error_mapper
        self.fk_uc = self.bootstrap_bundle.use_cases.fk_uc
        self.ik_uc = self.bootstrap_bundle.use_cases.ik_uc
        self.traj_uc = self.bootstrap_bundle.use_cases.traj_uc
        self.benchmark_uc = self.bootstrap_bundle.use_cases.benchmark_uc
        self.save_session_uc = self.bootstrap_bundle.use_cases.save_session_uc
        self.playback_service = self.bootstrap_bundle.services.playback_service
        self.playback_uc = self.bootstrap_bundle.use_cases.playback_uc
        self.export_report_uc = self.bootstrap_bundle.use_cases.export_report_uc
        self.export_package_uc = self.bootstrap_bundle.use_cases.export_package_uc
        self.import_robot_uc = self.bootstrap_bundle.use_cases.import_robot_uc
        collaborators = build_presentation_collaborators(self.bootstrap_bundle)
        install_main_controller_collaborators(self, collaborators)

    @property
    def state(self):
        return self.state_store.state

    def __getattr__(self, name: str):
        if name in self._COMPATIBILITY_METHOD_NAMES:
            return build_compatibility_method(self, name)
        raise AttributeError(name)

    def capabilities(self) -> list[CapabilityDescriptor]:
        return self.capability_descriptors()

    def capability_matrix(self):
        registries = self.bootstrap_bundle.registries
        return self.capability_service.build_matrix(
            solver_registry=registries.solver_registry,
            planner_registry=registries.planner_registry,
            importer_registry=registries.importer_registry,
        )

    def capability_descriptors(self) -> list[CapabilityDescriptor]:
        """Build capability descriptors for the current runtime container.

        Returns:
            list[CapabilityDescriptor]: Ordered descriptor list containing the complete
                runtime matrix plus category projections retained for compatibility.

        Raises:
            None: Pure projection of container/runtime state.
        """
        registries = self.bootstrap_bundle.registries
        matrix = self.capability_matrix()
        matrix_payload = matrix.as_dict()
        descriptors: list[CapabilityDescriptor] = [
            CapabilityDescriptor(
                'capability_matrix',
                'Capability matrix',
                metadata={
                    'sections': matrix_payload,
                    'section_order': list(matrix_payload.keys()),
                },
            )
        ]
        for section_name, label in (
            ('solvers', 'IK solvers'),
            ('planners', 'Trajectory planners'),
            ('importers', 'Robot importers'),
            ('render_features', 'Render features'),
            ('export_features', 'Export features'),
            ('scene_features', 'Scene features'),
            ('collision_features', 'Collision features'),
            ('plugin_features', 'Plugin features'),
        ):
            descriptors.append(
                CapabilityDescriptor(
                    section_name,
                    label,
                    metadata={'matrix': matrix_payload.get(section_name, [])},
                )
            )
        scene_summary = dict(getattr(self.state_store.state, 'scene_summary', {}) or {})
        if scene_summary:
            descriptors.append(
                CapabilityDescriptor(
                    'scene_validation_fidelity',
                    'Scene validation fidelity',
                    metadata={
                        'scene_fidelity': scene_summary.get('scene_fidelity', 'unknown'),
                        'collision_fidelity': dict(scene_summary.get('collision_fidelity', {}) or {}),
                        'validation_surface': dict(scene_summary.get('validation_surface', {}) or {}),
                        'validation_backend_capabilities': list(scene_summary.get('validation_backend_capabilities', []) or []),
                    },
                )
            )

        descriptors.extend(
            [
                CapabilityDescriptor(
                    'ik_solvers',
                    'IK solvers',
                    metadata={
                        'ids': registries.solver_registry.ids(),
                        'descriptors': [
                            {
                                'id': desc.solver_id,
                                'aliases': list(desc.aliases),
                                'metadata': dict(desc.metadata),
                                'source': getattr(desc, 'source', ''),
                            }
                            for desc in registries.solver_registry.descriptors()
                        ],
                        'matrix': matrix_payload['solvers'],
                    },
                ),
                CapabilityDescriptor(
                    'trajectory_planners',
                    'Trajectory planners',
                    metadata={
                        'ids': registries.planner_registry.ids(),
                        'descriptors': [
                            {
                                'id': desc.planner_id,
                                'aliases': list(desc.aliases),
                                'metadata': dict(desc.metadata),
                                'source': getattr(desc, 'source', ''),
                            }
                            for desc in registries.planner_registry.descriptors()
                        ],
                        'matrix': matrix_payload['planners'],
                    },
                ),
                CapabilityDescriptor(
                    'robot_importers',
                    'Robot importers',
                    metadata={
                        'ids': registries.importer_registry.ids(),
                        'descriptors': [
                            {
                                'id': desc.importer_id,
                                'aliases': list(desc.aliases),
                                'metadata': dict(desc.metadata),
                                'source': getattr(desc, 'source', ''),
                            }
                            for desc in registries.importer_registry.descriptors()
                        ],
                        'matrix': matrix_payload['importers'],
                    },
                ),
                CapabilityDescriptor(
                    'plugin_features',
                    'Plugin host',
                    metadata={'matrix': matrix_payload.get('plugin_features', [])},
                ),
                CapabilityDescriptor(
                    'package_export',
                    'Package export',
                    metadata={'matrix': matrix_payload.get('export_features', [])},
                ),
            ]
        )
        return descriptors
