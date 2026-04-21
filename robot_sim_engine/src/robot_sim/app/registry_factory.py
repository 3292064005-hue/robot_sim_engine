from __future__ import annotations

from robot_sim.application.importers.urdf_model_importer import URDFModelImporter
from robot_sim.application.importers.urdf_skeleton_importer import URDFSkeletonRobotImporter
from robot_sim.application.importers.yaml_importer import YAMLRobotImporter
from robot_sim.application.registries.importer_registry import ImporterRegistry
from robot_sim.application.registries.planner_registry import PlannerRegistry, build_default_planner_registry
from robot_sim.application.registries.solver_registry import SolverRegistry
from robot_sim.core.ik.analytic_6r import Analytic6RSphericalWristIKSolver
from robot_sim.core.ik.dls import DLSIKSolver
from robot_sim.core.ik.lm import LevenbergMarquardtIKSolver
from robot_sim.core.ik.pseudo_inverse import PseudoInverseIKSolver
from robot_sim.domain.enums import SolverFamily


def build_solver_registry(*, plugin_loader=None) -> SolverRegistry:
    """Build the builtin solver registry."""
    solver_registry = SolverRegistry()
    solver_registry.register(
        'pinv',
        PseudoInverseIKSolver(),
        metadata={
            'family': SolverFamily.ITERATIVE.value,
            'supports_weighted_least_squares': True,
            'supports_nullspace': True,
            'supports_adaptive_damping_fallback': True,
            'supports_joint_limits': True,
            'source': 'builtin',
        },
        source='builtin',
    )
    solver_registry.register(
        'dls',
        DLSIKSolver(),
        metadata={
            'family': SolverFamily.ITERATIVE.value,
            'supports_weighted_least_squares': True,
            'supports_nullspace': True,
            'supports_adaptive_damping': True,
            'supports_joint_limits': True,
            'source': 'builtin',
        },
        source='builtin',
    )
    solver_registry.register(
        'lm',
        LevenbergMarquardtIKSolver(),
        metadata={
            'family': SolverFamily.ITERATIVE.value,
            'supports_weighted_least_squares': True,
            'supports_nullspace': True,
            'supports_adaptive_damping': True,
            'supports_joint_limits': True,
            'algorithm': 'levenberg_marquardt',
            'source': 'builtin',
        },
        aliases=('levenberg_marquardt',),
        source='builtin',
    )
    solver_registry.register(
        'analytic_6r',
        Analytic6RSphericalWristIKSolver(),
        metadata={
            'family': SolverFamily.ANALYTIC.value,
            'supports_weighted_least_squares': False,
            'supports_nullspace': False,
            'supports_joint_limits': True,
            'supports_position_only_via_fallback': True,
            'requires_spherical_wrist': True,
            'supported_dof': 6,
            'algorithm': 'closed_form_spherical_wrist',
            'source': 'builtin',
        },
        aliases=('spherical_wrist_6r',),
        source='builtin',
    )
    if plugin_loader is not None:
        for registration in plugin_loader.capability_registrations('solver'):
            registration_metadata = dict(registration.metadata)
            solver_registry.register(
                registration.plugin_id,
                registration.instance,
                metadata=registration_metadata,
                aliases=tuple(registration.aliases),
                replace=registration.replace,
                source=registration.source,
            )
        for alias, canonical_target in plugin_loader.compatibility_aliases('solver').items():
            solver_registry.register_alias(alias, canonical_target)
    return solver_registry


def build_planner_registry(ik_uc, *, plugin_loader=None) -> PlannerRegistry:
    """Build the builtin planner registry."""
    planner_registry = build_default_planner_registry(ik_uc)
    if plugin_loader is not None:
        for registration in plugin_loader.capability_registrations('planner', ik_uc=ik_uc):
            registration_metadata = dict(registration.metadata)
            planner_registry.register(
                registration.plugin_id,
                registration.instance,
                metadata=registration_metadata,
                aliases=tuple(registration.aliases),
                replace=registration.replace,
                source=registration.source,
            )
        for alias, canonical_target in plugin_loader.compatibility_aliases('planner').items():
            planner_registry.register_alias(alias, canonical_target)
    return planner_registry


def build_importer_registry(robot_registry, *, plugin_loader=None) -> ImporterRegistry:
    """Build the builtin importer registry."""
    importer_registry = ImporterRegistry()
    importer_registry.register(
        'yaml',
        YAMLRobotImporter(robot_registry),
        metadata={
            'source_format': 'yaml',
            'extensions': ('yaml', 'yml'),
            'display_name': 'YAML robot config',
            'fidelity': 'native',
            'family': 'config',
            'source': 'builtin',
        },
        aliases=('yml',),
        source='builtin',
    )
    importer_registry.register(
        'urdf_model',
        URDFModelImporter(),
        metadata={
            'source_format': 'urdf',
            'extensions': ('urdf',),
            'display_name': 'URDF serial model importer',
            'fidelity': 'serial_kinematics',
            'family': 'serial_model_import',
            'notes': 'Preserves serial link/joint structure and visual/collision availability while adapting the runtime to the V7 DH pipeline.',
            'source': 'builtin',
        },
        aliases=('urdf',),
        source='builtin',
    )
    importer_registry.register(
        'urdf_skeleton',
        URDFSkeletonRobotImporter(),
        metadata={
            'source_format': 'urdf',
            'extensions': ('urdf',),
            'display_name': 'URDF skeleton importer',
            'fidelity': 'approximate',
            'family': 'approximate_tree_import',
            'notes': 'Approximates a serial DH-like chain from URDF joint origins. Not a full URDF tree importer.',
            'source': 'builtin',
        },
        source='builtin',
    )
    if plugin_loader is not None:
        for registration in plugin_loader.capability_registrations('importer', robot_registry=robot_registry):
            registration_metadata = dict(registration.metadata)
            importer_registry.register(
                registration.plugin_id,
                registration.instance,
                metadata=registration_metadata,
                aliases=tuple(registration.aliases),
                replace=registration.replace,
                source=registration.source,
            )
        for alias, canonical_target in plugin_loader.compatibility_aliases('importer').items():
            importer_registry.register_alias(alias, canonical_target)
    return importer_registry
