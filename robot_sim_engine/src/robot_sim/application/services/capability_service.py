from __future__ import annotations

from robot_sim.application.planner_capabilities import planner_capability_map
from robot_sim.domain.capabilities import CapabilityDescriptor, CapabilityMatrix
from robot_sim.domain.collision_backends import default_collision_backend_registry
from robot_sim.domain.collision_fidelity import validation_backend_capability_matrix
from robot_sim.domain.enums import ModuleStatus
from robot_sim.domain.runtime_contracts import render_capability_matrix_markdown

_PLUGIN_STATUS_TO_MODULE_STATUS = {
    'stable': ModuleStatus.STABLE,
    'beta': ModuleStatus.BETA,
    'experimental': ModuleStatus.EXPERIMENTAL,
    'internal': ModuleStatus.INTERNAL,
    'deprecated': ModuleStatus.DEPRECATED,
}


class CapabilityService:
    """Build and render the runtime capability matrix exposed across the product surface."""

    def __init__(self, runtime_feature_policy=None, plugin_loader=None) -> None:
        self._runtime_feature_policy = runtime_feature_policy
        self._collision_registry = default_collision_backend_registry()
        self._plugin_loader = plugin_loader

    @property
    def _experimental_enabled(self) -> bool:
        return bool(getattr(self._runtime_feature_policy, 'experimental_backends_enabled', False))

    def _scene_features(self) -> tuple[CapabilityDescriptor, ...]:
        validation_matrix = validation_backend_capability_matrix(experimental_enabled=self._experimental_enabled)
        scene_plugin_rows = [row for row in self._plugin_audit_rows() if str(row.get('kind', '')) == 'scene_backend']
        planning_scene_descriptor = CapabilityDescriptor(
            'planning_scene',
            'Planning scene',
            owner_module='collision.scene',
            status=ModuleStatus.STABLE,
            metadata={
                'ui_surface': 'stable_scene_toolbar',
                'integration_scope': 'validation_export_session_scene_toolbar',
                'edit_surface': 'stable_scene_editor',
                'stable_surface_version': 'v3',
                'scene_geometry_contract': 'declaration_validation_render',
                'scene_geometry_contract_version': 'v1',
                'scene_validation_capability_matrix_version': 'v1',
                'declared_backends': list(self._collision_registry.declared_backend_ids()),
                'active_backends': list(self._collision_registry.active_backend_ids(experimental_enabled=self._experimental_enabled)),
                'fallback_backend': self._collision_registry.default_backend,
                'experimental_backends': [
                    descriptor.backend_id for descriptor in self._collision_registry.descriptors() if descriptor.is_experimental
                ],
                'validation_backend_capabilities': validation_matrix,
                'scene_backend_plugin_kinds': ['scene_backend'],
                'scene_backend_plugin_ids': [str(row['id']) for row in scene_plugin_rows if bool(row.get('enabled', False))],
            },
        )
        plugin_surface = CapabilityDescriptor(
            'scene_backend_plugin_surface',
            'Scene backend plugin surface',
            owner_module='plugin_loader',
            status=ModuleStatus.STABLE,
            metadata={
                'plugin_kind': 'scene_backend',
                'plugin_surface_version': 'v1',
                'declared_plugin_ids': [str(row['id']) for row in scene_plugin_rows],
                'enabled_plugin_ids': [str(row['id']) for row in scene_plugin_rows if bool(row.get('enabled', False))],
                'scene_geometry_contract_version': 'v1',
                'scene_validation_capability_matrix_version': 'v1',
            },
        )
        return (planning_scene_descriptor, plugin_surface, *self._collision_registry.scene_capabilities(experimental_enabled=self._experimental_enabled))

    @staticmethod
    def _plugin_status(metadata: dict[str, object]) -> ModuleStatus:
        status = str(metadata.get('status', 'stable') or 'stable')
        return _PLUGIN_STATUS_TO_MODULE_STATUS.get(status, ModuleStatus.STABLE)

    def _plugin_audit_rows(self) -> tuple[dict[str, object], ...]:
        if self._plugin_loader is None:
            return ()
        return tuple(self._plugin_loader.audit())

    def _plugin_features(self) -> tuple[CapabilityDescriptor, ...]:
        audit_rows = self._plugin_audit_rows()
        descriptors = [
            CapabilityDescriptor(
                key='plugin_host',
                label='Plugin host',
                owner_module='plugin_loader',
                status=ModuleStatus.STABLE,
                metadata={
                    'plugin_surface_version': 'v1',
                    'declared_plugin_count': len(audit_rows),
                    'enabled_plugin_count': sum(1 for row in audit_rows if bool(row.get('enabled', False))),
                    'active_profile': str(getattr(self._runtime_feature_policy, 'active_profile', 'default') or 'default'),
                    'plugin_discovery_enabled': bool(getattr(self._runtime_feature_policy, 'plugin_discovery_enabled', False)),
                    'plugin_status_allowlist': list(getattr(self._runtime_feature_policy, 'plugin_status_allowlist', ()) or ()),
                },
            ),
        ]
        descriptors.extend(
            CapabilityDescriptor(
                key=f"plugin_{row['id']}",
                label=str(row['id']),
                owner_module='plugin_loader',
                enabled=bool(row.get('enabled', False)),
                status=self._plugin_status({'status': row.get('status', 'stable')}),
                metadata={
                    'plugin_id': str(row['id']),
                    'kind': str(row.get('kind', '')),
                    'source': str(row.get('source', '')),
                    'reason': str(row.get('reason', '')),
                    'enabled_profiles': list(row.get('enabled_profiles', []) or []),
                    'aliases': list(row.get('aliases', []) or []),
                    'required_host_capabilities': list(row.get('required_host_capabilities', []) or []),
                    'optional_host_capabilities': list(row.get('optional_host_capabilities', []) or []),
                    'negotiated_host_capabilities': list(row.get('negotiated_host_capabilities', []) or []),
                    'missing_optional_host_capabilities': list(row.get('missing_optional_host_capabilities', []) or []),
                    'plugin_surface_version': 'v1',
                    **dict(row.get('metadata', {}) or {}),
                },
            )
            for row in audit_rows
        )
        return tuple(descriptors)

    def build_matrix(self, *, solver_registry, planner_registry, importer_registry) -> CapabilityMatrix:
        """Build the full runtime capability matrix from active registries and runtime policy."""
        solvers = tuple(
            CapabilityDescriptor(
                key=desc.solver_id,
                label=desc.solver_id,
                owner_module='solver_registry',
                status=self._plugin_status(dict(desc.metadata)),
                metadata={'aliases': list(desc.aliases), **dict(desc.metadata)},
            )
            for desc in solver_registry.descriptors()
        )
        planner_defaults = planner_capability_map()
        planners = []
        for desc in planner_registry.descriptors():
            default_descriptor = planner_defaults.get(desc.planner_id)
            merged_metadata = {
                'aliases': list(desc.aliases),
                **({} if default_descriptor is None else default_descriptor.as_metadata()),
                **dict(desc.metadata),
            }
            planners.append(
                CapabilityDescriptor(
                    key=desc.planner_id,
                    label=desc.planner_id,
                    owner_module='planner_registry',
                    status=self._plugin_status(merged_metadata),
                    metadata=merged_metadata,
                )
            )
        importers = tuple(
            CapabilityDescriptor(
                key=desc.importer_id,
                label=desc.importer_id,
                owner_module='importer_registry',
                status=self._plugin_status(dict(desc.metadata)),
                metadata={'aliases': list(desc.aliases), **dict(desc.metadata)},
            )
            for desc in importer_registry.descriptors()
        )
        collision_plugin_rows = [row for row in self._plugin_audit_rows() if str(row.get('kind', '')) == 'collision_backend']
        collision_features = (
            CapabilityDescriptor(
                'collision_backend_plugin_surface',
                'Collision backend plugin surface',
                owner_module='plugin_loader',
                status=ModuleStatus.STABLE,
                metadata={
                    'plugin_kind': 'collision_backend',
                    'plugin_surface_version': 'v1',
                    'declared_plugin_ids': [str(row['id']) for row in collision_plugin_rows],
                    'enabled_plugin_ids': [str(row['id']) for row in collision_plugin_rows if bool(row.get('enabled', False))],
                    'backend_contract_version': 'v1',
                },
            ),
            *self._collision_registry.scene_capabilities(experimental_enabled=self._experimental_enabled),
        )
        render_features = (
            CapabilityDescriptor(
                'scene_toolbar',
                'Scene toolbar',
                owner_module='render',
                status=ModuleStatus.STABLE,
                metadata={'consumed_by': ['ui', 'diagnostics', 'export'], 'capability_surface_version': 'v1'},
            ),
            CapabilityDescriptor(
                'render_diagnostics',
                'Render diagnostics',
                owner_module='presentation.diagnostics',
                status=ModuleStatus.STABLE,
                metadata={'consumed_by': ['diagnostics'], 'capability_surface_version': 'v1'},
            ),
        )
        export_features = (
            CapabilityDescriptor(
                'package_export',
                'Package export',
                owner_module='export',
                status=ModuleStatus.STABLE,
                metadata={'consumed_by': ['export_manifest', 'session_manifest'], 'capability_surface_version': 'v1'},
            ),
            CapabilityDescriptor(
                'capability_manifest_projection',
                'Capability manifest projection',
                owner_module='export',
                status=ModuleStatus.STABLE,
                metadata={'capability_matrix_version': 'v1', 'consumed_by': ['export_manifest', 'diagnostics', 'ui_state']},
            ),
        )
        return CapabilityMatrix(
            solvers=solvers,
            planners=tuple(planners),
            importers=importers,
            render_features=render_features,
            export_features=export_features,
            scene_features=self._scene_features(),
            collision_features=tuple(collision_features),
            plugin_features=self._plugin_features(),
        )

    def render_markdown(self, *, solver_registry=None, planner_registry=None, importer_registry=None) -> str:
        """Render the complete capability matrix as deterministic markdown.

        When registries are unavailable, the renderer emits a stable baseline matrix that still
        documents render/export/scene/collision/plugin host contracts. This keeps checked-in
        contract docs aligned with runtime truth without fabricating dynamic registry entries.
        """
        if solver_registry is not None and planner_registry is not None and importer_registry is not None:
            matrix = self.build_matrix(
                solver_registry=solver_registry,
                planner_registry=planner_registry,
                importer_registry=importer_registry,
            )
        else:
            matrix = CapabilityMatrix(
                render_features=(
                    CapabilityDescriptor('scene_toolbar', 'Scene toolbar', owner_module='render', status=ModuleStatus.STABLE),
                    CapabilityDescriptor('render_diagnostics', 'Render diagnostics', owner_module='presentation.diagnostics', status=ModuleStatus.STABLE),
                ),
                export_features=(
                    CapabilityDescriptor('package_export', 'Package export', owner_module='export', status=ModuleStatus.STABLE),
                    CapabilityDescriptor('capability_manifest_projection', 'Capability manifest projection', owner_module='export', status=ModuleStatus.STABLE),
                ),
                scene_features=self._scene_features(),
                collision_features=(
                    CapabilityDescriptor(
                        'collision_backend_plugin_surface',
                        'Collision backend plugin surface',
                        owner_module='plugin_loader',
                        status=ModuleStatus.STABLE,
                        metadata={'plugin_kind': 'collision_backend', 'plugin_surface_version': 'v1', 'backend_contract_version': 'v1'},
                    ),
                    *self._collision_registry.scene_capabilities(experimental_enabled=self._experimental_enabled),
                ),
                plugin_features=self._plugin_features(),
            )
        return render_capability_matrix_markdown(matrix)

    def render_scene_markdown(self) -> str:
        """Compatibility alias retained for quality-contract callers predating the full matrix."""
        return self.render_markdown()
