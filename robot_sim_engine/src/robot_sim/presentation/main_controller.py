from __future__ import annotations

from pathlib import Path

from robot_sim.app.contracts import MainControllerContainerProtocol, build_presentation_bootstrap_bundle
from robot_sim.domain.capabilities import CapabilityDescriptor
from robot_sim.presentation.main_controller_support import (
    build_presentation_collaborators,
    install_main_controller_collaborators,
)


class MainController:
    """Facade that exposes application services to the Qt layer.

    ``MainController`` now keeps only canonical bootstrap state plus explicit workflow
    delegates. Most capabilities delegate to the canonical workflow surfaces consumed by the
    Qt shell. Import/save entrypoints intentionally retain historical controller semantics so
    programmatic callers can still persist robots immediately when required.
    """


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



    def robot_names(self):
        return self.robot_workflow.robot_names()

    def robot_entries(self):
        return self.robot_workflow.robot_entries()

    def importer_entries(self):
        return self.robot_workflow.importer_entries()

    def available_specs(self):
        return self.robot_workflow.available_specs()

    def import_robot(self, source: str, importer_id: str | None = None):
        """Import a robot and persist it immediately for compatibility callers.

        GUI task orchestration continues to use ``RobotWorkflowService`` for staged imports.
        This facade keeps the historical persisted-import behavior expected by programmatic
        callers and regression tests that reload the imported robot from the registry.
        """
        return self.robot_workflow.import_robot(source, importer_id=importer_id, persist=True)

    def load_robot(self, name: str):
        return self.robot_workflow.load_robot(name)

    def build_robot_from_editor(self, existing_spec, rows, home_q):
        return self.robot_workflow.build_robot_from_editor(existing_spec, rows, home_q)

    def save_current_robot(self, rows=None, home_q=None, name: str | None = None):
        return self.robot_workflow.save_current_robot(rows=rows, home_q=home_q, name=name)

    def run_fk(self, q=None):
        return self.robot_workflow.run_fk(q=q)

    def sample_ee_positions(self, q_samples):
        return self.robot_workflow.sample_ee_positions(q_samples)

    def solver_defaults(self) -> dict[str, object]:
        return self.motion_workflow.solver_defaults()

    def trajectory_defaults(self) -> dict[str, object]:
        return self.motion_workflow.trajectory_defaults()

    def build_target_pose(self, values6, orientation_mode: str = 'rvec'):
        return self.motion_workflow.build_target_pose(values6, orientation_mode=orientation_mode)

    def build_ik_request(self, values6, **kwargs):
        return self.motion_workflow.build_ik_request(values6, **kwargs)

    def apply_ik_result(self, req, result) -> None:
        self.motion_workflow.apply_ik_result(req, result)

    def run_ik(self, values6, **kwargs):
        return self.motion_workflow.run_ik(values6, **kwargs)

    def build_benchmark_config(self, **kwargs):
        return self.motion_workflow.build_benchmark_config(**kwargs)

    def run_benchmark(self, config=None, *, execution_graph=None):
        return self.motion_workflow.run_benchmark(config=config, execution_graph=execution_graph)

    def trajectory_goal_or_raise(self):
        return self.motion_workflow.trajectory_goal_or_raise()

    def build_trajectory_request(self, **kwargs):
        return self.motion_workflow.build_trajectory_request(**kwargs)

    def plan_trajectory(self, **kwargs):
        return self.motion_workflow.plan_trajectory(**kwargs)

    def apply_trajectory(self, traj) -> None:
        self.motion_workflow.apply_trajectory(traj)

    def current_playback_frame(self):
        return self.motion_workflow.current_playback_frame()

    def set_playback_frame(self, frame_idx: int):
        return self.motion_workflow.set_playback_frame(frame_idx)

    def next_playback_frame(self):
        return self.motion_workflow.next_playback_frame()

    def set_playback_options(self, *, speed_multiplier=None, loop_enabled=None) -> None:
        self.motion_workflow.set_playback_options(speed_multiplier=speed_multiplier, loop_enabled=loop_enabled)

    def export_trajectory_bundle(self, name: str = 'trajectory_bundle.npz'):
        return self.export_workflow.export_trajectory_bundle(name=name)

    def export_trajectory_metrics(self, name: str = 'trajectory_metrics.json', metrics: dict[str, object] | None = None):
        return self.export_workflow.export_trajectory_metrics(name=name, metrics=metrics)

    def export_benchmark(self, name: str = 'benchmark_report.json'):
        return self.export_workflow.export_benchmark(name=name)

    def export_benchmark_cases_csv(self, name: str = 'benchmark_cases.csv'):
        return self.export_workflow.export_benchmark_cases_csv(name=name)

    def export_session(self, name: str = 'session.json', *, telemetry_detail: str = 'full'):
        return self.export_workflow.export_session(name=name, telemetry_detail=telemetry_detail)

    def export_package(self, name: str = 'robot_sim_package.zip', *, telemetry_detail: str = 'minimal'):
        return self.export_workflow.export_package(name=name, telemetry_detail=telemetry_detail)

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
                runtime matrix plus category projections exposed for diagnostics and UI composition.

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
