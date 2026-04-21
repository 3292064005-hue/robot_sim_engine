from __future__ import annotations

from robot_sim.application.planner_capabilities import planner_capability_map
from robot_sim.domain.capabilities import CapabilityDescriptor, CapabilityMatrix
from robot_sim.domain.collision_backends import default_collision_backend_registry
from robot_sim.domain.collision_fidelity import validation_backend_capability_matrix
from robot_sim.application.services.collision_backend_runtime import install_collision_backend_runtime_plugins, resolve_collision_backend_runtime
from robot_sim.application.services.scene_backend_runtime import install_scene_backend_runtime_plugins, resolve_scene_backend_runtime
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
        if self._plugin_loader is not None:
            install_scene_backend_runtime_plugins(self._plugin_loader.registrations('scene_backend'))
            install_collision_backend_runtime_plugins(self._plugin_loader.registrations('collision_backend'))

    @property
    def _experimental_enabled(self) -> bool:
        return bool(getattr(self._runtime_feature_policy, 'experimental_backends_enabled', False))

    def _scene_features(self) -> tuple[CapabilityDescriptor, ...]:
        validation_matrix = validation_backend_capability_matrix(experimental_enabled=self._experimental_enabled)
        scene_plugin_rows = [row for row in self._plugin_capability_rows() if str(row.get('kind', '')) == 'scene_backend']
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
                'scene_backend_runtime': resolve_scene_backend_runtime('planning_scene_backend').capabilities(),
                'collision_backend_runtimes': {backend: resolve_collision_backend_runtime(backend).capabilities() for backend in self._collision_registry.active_backend_ids(experimental_enabled=self._experimental_enabled)},
                'scene_authority_model': 'canonical_declaration_authority',
                'validation_adapter_model': 'explicit_backend_projection',
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
                'production_plugin_ids': self._plugin_ids_by_tier('scene_backend', 'production'),
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

    def _plugin_capability_rows(self) -> tuple[dict[str, object], ...]:
        if self._plugin_loader is None:
            return ()
        return tuple(self._plugin_loader.audit_split()['capability_entries'])

    def _plugin_ids_by_tier(self, kind: str, tier: str) -> list[str]:
        return [
            str(row['id'])
            for row in self._plugin_capability_rows()
            if str(row.get('kind', '')) == str(kind) and str(row.get('deployment_tier', 'production')) == str(tier) and bool(row.get('enabled', False))
        ]

    def build_plugin_marketplace(self) -> dict[str, object]:
        """Project plugin audit rows into a capability-market summary."""
        audit_rows = list(self._plugin_audit_rows())
        marketplace: dict[str, dict[str, object]] = {}
        for row in audit_rows:
            kind = str(row.get('kind', '') or 'unknown')
            entry = marketplace.setdefault(kind, {
                'kind': kind,
                'declared_plugin_ids': [],
                'enabled_plugin_ids': [],
                'production_plugin_ids': [],
                'experimental_plugin_ids': [],
                'status_counts': {},
                'deployment_tier_counts': {},
            })
            plugin_id = str(row.get('id', '') or '')
            status = str(row.get('status', 'stable') or 'stable')
            tier = str(row.get('deployment_tier', 'production') or 'production')
            if plugin_id:
                entry['declared_plugin_ids'].append(plugin_id)
                if bool(row.get('enabled', False)):
                    entry['enabled_plugin_ids'].append(plugin_id)
                if tier == 'production':
                    entry['production_plugin_ids'].append(plugin_id)
                if tier == 'experimental':
                    entry['experimental_plugin_ids'].append(plugin_id)
            entry['status_counts'][status] = int(entry['status_counts'].get(status, 0)) + 1
            entry['deployment_tier_counts'][tier] = int(entry['deployment_tier_counts'].get(tier, 0)) + 1
        return {
            'plugin_surface_version': 'v1',
            'kinds': {key: value for key, value in sorted(marketplace.items())},
            'total_declared_plugins': int(len(audit_rows)),
            'total_enabled_plugins': int(sum(1 for row in audit_rows if bool(row.get('enabled', False)))),
        }

    def build_domain_map(self, *, solver_registry, planner_registry, importer_registry) -> dict[str, object]:
        """Build a first-class domain map separating core, adapter, and plugin surfaces."""
        return {
            'scene': {
                'canonical_core': 'planning_scene',
                'canonical_runtime': resolve_scene_backend_runtime('planning_scene_backend').capabilities(),
                'adapter_surfaces': ['scene_backend', 'collision_backend'],
                'plugin_surfaces': {
                    'scene_backend': self._plugin_ids_by_tier('scene_backend', 'production'),
                    'collision_backend': self._plugin_ids_by_tier('collision_backend', 'production'),
                },
                'active_collision_backend_runtimes': {backend: resolve_collision_backend_runtime(backend).capabilities() for backend in self._collision_registry.active_backend_ids(experimental_enabled=self._experimental_enabled)},
            },
            'kinematics': {
                'canonical_core': 'ik_solver_registry',
                'alternatives': [descriptor.solver_id for descriptor in solver_registry.descriptors()],
            },
            'planning': {
                'canonical_core': 'trajectory_planner_registry',
                'alternatives': [descriptor.planner_id for descriptor in planner_registry.descriptors()],
            },
            'import': {
                'canonical_core': 'robot_importer_registry',
                'alternatives': [descriptor.importer_id for descriptor in importer_registry.descriptors()],
            },
            'render': {
                'canonical_core': 'render_runtime_state',
                'adapter_surfaces': ['render_runtime_advice'],
            },
            'plugin_marketplace': self.build_plugin_marketplace(),
        }

    def _plugin_features(self) -> tuple[CapabilityDescriptor, ...]:
        audit_rows = self._plugin_audit_rows()
        capability_rows = self._plugin_capability_rows()
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
                    'runtime_provider_count': len(capability_rows),
                    'runtime_provider_enabled_count': sum(1 for row in capability_rows if bool(row.get('enabled', False))),
                    'active_profile': str(getattr(self._runtime_feature_policy, 'active_profile', 'default') or 'default'),
                    'plugin_discovery_enabled': bool(getattr(self._runtime_feature_policy, 'plugin_discovery_enabled', False)),
                    'plugin_status_allowlist': list(getattr(self._runtime_feature_policy, 'plugin_status_allowlist', ()) or ()),
                    'counts_by_tier': {
                        tier: sum(1 for row in audit_rows if str(row.get('deployment_tier', 'production')) == tier)
                        for tier in ('production', 'experimental', 'fixture', 'compatibility')
                    },
                    'plugin_marketplace': self.build_plugin_marketplace(),
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
                    'deployment_tier': str(row.get('deployment_tier', 'production')),
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
            for row in capability_rows
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
        collision_plugin_rows = [row for row in self._plugin_capability_rows() if str(row.get('kind', '')) == 'collision_backend']
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
        domain_map = self.build_domain_map(
            solver_registry=solver_registry,
            planner_registry=planner_registry,
            importer_registry=importer_registry,
        )
        return CapabilityMatrix(
            solvers=solvers,
            planners=tuple(planners),
            importers=importers,
            render_features=render_features,
            export_features=export_features,
            scene_features=self._scene_features(),
            collision_features=tuple(collision_features),
            plugin_features=self._plugin_features() + (CapabilityDescriptor(
                'runtime_domain_map',
                'Runtime domain map',
                owner_module='capability_service',
                status=ModuleStatus.STABLE,
                metadata=domain_map,
            ),),
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
