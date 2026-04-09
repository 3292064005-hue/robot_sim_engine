from __future__ import annotations

from robot_sim.domain.capabilities import CapabilityDescriptor, CapabilityMatrix
from robot_sim.domain.collision_backends import default_collision_backend_registry
from robot_sim.domain.enums import ModuleStatus
from robot_sim.domain.runtime_contracts import render_capability_matrix_markdown

<<<<<<< HEAD
_PLUGIN_STATUS_TO_MODULE_STATUS = {
    'stable': ModuleStatus.STABLE,
    'beta': ModuleStatus.BETA,
    'experimental': ModuleStatus.EXPERIMENTAL,
    'internal': ModuleStatus.INTERNAL,
    'deprecated': ModuleStatus.DEPRECATED,
}

=======
>>>>>>> 3ed78e647985c6d680c085e4480d898855278db3

class CapabilityService:
    """Build the runtime capability matrix exposed to the presentation layer."""

    def __init__(self, runtime_feature_policy=None) -> None:
        self._runtime_feature_policy = runtime_feature_policy
        self._collision_registry = default_collision_backend_registry()

    def _scene_features(self) -> tuple[CapabilityDescriptor, ...]:
        experimental_enabled = bool(getattr(self._runtime_feature_policy, 'experimental_backends_enabled', False))
        planning_scene_descriptor = CapabilityDescriptor(
            'planning_scene',
            'Planning scene',
            owner_module='collision.scene',
            status=ModuleStatus.STABLE,
            metadata={
<<<<<<< HEAD
                'ui_surface': 'stable_scene_toolbar',
                'integration_scope': 'validation_export_session_scene_toolbar',
                'edit_surface': 'stable_scene_editor',
                'declared_backends': list(self._collision_registry.declared_backend_ids()),
                'active_backends': list(self._collision_registry.active_backend_ids(experimental_enabled=experimental_enabled)),
=======
                'supported_backends': list(self._collision_registry.supported_backend_ids(experimental_enabled=experimental_enabled)),
>>>>>>> 3ed78e647985c6d680c085e4480d898855278db3
                'fallback_backend': self._collision_registry.default_backend,
                'experimental_backends': [
                    descriptor.backend_id for descriptor in self._collision_registry.descriptors() if descriptor.is_experimental
                ],
            },
        )
        return (planning_scene_descriptor, *self._collision_registry.scene_capabilities(experimental_enabled=experimental_enabled))

<<<<<<< HEAD
    @staticmethod
    def _plugin_status(metadata: dict[str, object]) -> ModuleStatus:
        status = str(metadata.get('status', 'stable') or 'stable')
        return _PLUGIN_STATUS_TO_MODULE_STATUS.get(status, ModuleStatus.STABLE)

=======
>>>>>>> 3ed78e647985c6d680c085e4480d898855278db3
    def build_matrix(self, *, solver_registry, planner_registry, importer_registry) -> CapabilityMatrix:
        """Build a capability matrix from active registries.

        Args:
            solver_registry: Solver registry.
            planner_registry: Planner registry.
            importer_registry: Importer registry.

        Returns:
            CapabilityMatrix: Structured runtime capability matrix.

        Raises:
            Exception: Propagates registry descriptor failures.
        """
        solvers = tuple(
            CapabilityDescriptor(
                key=desc.solver_id,
                label=desc.solver_id,
                owner_module='solver_registry',
<<<<<<< HEAD
                status=self._plugin_status(dict(desc.metadata)),
=======
                status=ModuleStatus.STABLE,
>>>>>>> 3ed78e647985c6d680c085e4480d898855278db3
                metadata={'aliases': list(desc.aliases), **dict(desc.metadata)},
            )
            for desc in solver_registry.descriptors()
        )
        planners = tuple(
            CapabilityDescriptor(
                key=desc.planner_id,
                label=desc.planner_id,
                owner_module='planner_registry',
<<<<<<< HEAD
                status=self._plugin_status(dict(desc.metadata)),
=======
                status=ModuleStatus.STABLE,
>>>>>>> 3ed78e647985c6d680c085e4480d898855278db3
                metadata={'aliases': list(desc.aliases), **dict(desc.metadata)},
            )
            for desc in planner_registry.descriptors()
        )
        importers = tuple(
            CapabilityDescriptor(
                key=desc.importer_id,
                label=desc.importer_id,
                owner_module='importer_registry',
<<<<<<< HEAD
                status=self._plugin_status(dict(desc.metadata)),
=======
                status=ModuleStatus.STABLE,
>>>>>>> 3ed78e647985c6d680c085e4480d898855278db3
                metadata={'aliases': list(desc.aliases), **dict(desc.metadata)},
            )
            for desc in importer_registry.descriptors()
        )
        return CapabilityMatrix(
            solvers=solvers,
            planners=planners,
            importers=importers,
            render_features=(CapabilityDescriptor('scene_toolbar', 'Scene toolbar', owner_module='render', status=ModuleStatus.STABLE),),
            export_features=(CapabilityDescriptor('package_export', 'Package export', owner_module='export', status=ModuleStatus.STABLE),),
            scene_features=self._scene_features(),
        )

    def render_scene_markdown(self) -> str:
        """Render the scene-capability subset as deterministic markdown.

        Returns:
            str: Markdown bullet list describing scene capabilities and statuses.

        Raises:
            None: Rendering is a pure formatting operation.
        """
        return render_capability_matrix_markdown(self._scene_features())
