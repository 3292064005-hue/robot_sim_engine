# Stable Surface Migration Notes

## Scope

This document records the implemented migration for the confirmed architecture items:

- P0-01 presentation capability-surface convergence
- P0-02 export artifact taxonomy alignment
- P0-03 release/governance evidence classification
- P1-01 planner capability single source of truth
- P1-02 source model vs execution-adapter semantic split in exported session evidence
- P2-01 compatibility surface concentration

## Capability surface

### Canonical surface

The canonical presentation capability surface is now the workflow layer:

- `RobotWorkflowService`
- `MotionWorkflowService`
- `ExportWorkflowService`

Coordinators and top-level controller flows should depend on workflow services as the stable port.

### Compatibility surface

`WorkflowFacadeBundle` remains available only as a compatibility alias bundle. It is now derived from the workflow bundle through adapter-only concrete facade classes (`RobotFacade`, `SolverFacade`, `TrajectoryFacade`, `PlaybackFacade`, `BenchmarkFacade`, `ExportFacade`) instead of introducing an independent parallel implementation surface. Adapter usage is recorded through the compatibility-usage registry so out-of-tree dependencies can be measured before removal.

Migration rule:

1. Prefer workflow services for all new coordinator and controller integrations.
2. Treat facade accessors as compatibility aliases only.
3. Compatibility facades are now instantiated lazily from the workflow bundle; new code must not force eager facade construction on the clean mainline.
4. Do not add new user-visible methods to facade-only contracts.

Rollback rule:

- If an out-of-tree consumer is ever confirmed to still depend on facade wiring, that consumer must first be recorded in the audited downstream inventory before the compatibility alias bundle can remain in place for another release cycle.

## Export taxonomy

Trajectory export is now canonically a **bundle export**.

### Canonical method

- `export_trajectory_bundle(...)`

### Compatibility alias

- `export_trajectory(...)`

Migration rule:

1. Use `export_trajectory_bundle(...)` in new code and tests.
2. Keep `export_trajectory(...)` only as a compatibility alias.
3. Use centralized artifact defaults from `robot_sim.application.export_artifacts` instead of hard-coded file names.

Rollback rule:

- The compatibility alias remains in place and can continue to forward to the bundle export path.

## Planner capability descriptors

Planner mode exposure, default planner resolution, capability metadata, and exported planner summaries now derive from `robot_sim.application.planner_capabilities`.

Migration rule:

1. Add or promote planners by editing the descriptor table.
2. Keep UI exposure decisions in descriptor metadata instead of hard-coded widget lists.
3. Resolve request defaults through descriptor helpers.

Rollback rule:

- Hidden planners remain registered and can stay profile-gated by descriptor flags without removing registry entries.

## Import/runtime semantics

Session export evidence now distinguishes:

- `source_model_summary`
- `execution_summary`

This preserves the boundary between the imported source model and the runtime execution adapter.

Migration rule:

1. New reports and downstream tooling should consume the explicit summaries.
2. Existing consumers may continue reading legacy summaries during the compatibility window.

Rollback rule:

- Legacy fields remain present alongside the explicit summaries.

## Governance evidence

Quality-gate evidence now records failure classification and environment-specific failures. Aggregated evidence also emits `artifacts/release_manifest.json`, which now separates `artifact_ready`, `environment_ready`, and `release_ready` so a green artifact bundle cannot masquerade as a release-ready environment.

Current classifications include:

- `none`
- `environment_mismatch`
- `tooling_missing`
- `command_failure`

Migration rule:

1. Treat GUI baseline mismatches separately from product regressions.
2. Treat missing external tools separately from runtime defects.
3. Distinguish shim GUI smoke from a real GUI baseline during release review; shim success is useful smoke evidence but does not satisfy the checked-in GUI release contract.
4. Consume evidence JSON/Markdown artifacts for release review instead of only relying on process exit codes.

Rollback rule:

- Existing gate commands are unchanged; only evidence richness increased.

## Compatibility debt

Compatibility shims were not removed wholesale. Instead, they were concentrated behind compatibility aliases so the mainline implementation surface remains singular. The retirement path is now tracked through `configs/compatibility_downstream_inventory.yaml` and `configs/compatibility_retirement.yaml`, which bind each retained surface to an audited downstream-consumer inventory, an explicit audited out-of-tree result, an explicit removal checklist, and rollback steps.

Migration rule:

1. Do not extend legacy alias surfaces with new behavior.
2. Migrate internal call sites to canonical workflow and descriptor APIs first.
3. Delete compatibility shims only after the supported consumer inventory is clean and the out-of-tree policy remains unchanged.

Rollback rule:

- The alias surfaces remain available for a staged deprecation cycle.

## Widget namespace migration

Stable widget import paths for `collision_panel`, `export_panel`, and `scene_options_panel` now exist only as deprecated compatibility aliases that emit `DeprecationWarning`. They no longer silently present experimental widgets as if they were promoted stable implementations.
