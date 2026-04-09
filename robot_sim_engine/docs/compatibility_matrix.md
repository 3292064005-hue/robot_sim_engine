# Compatibility matrix

V7 mainline no longer retains runtime compatibility shims on the bootstrap/config/main-window/worker lifecycle surfaces.

## Current state

| Surface | Status | Notes |
| --- | --- | --- |
| bootstrap tuple/indexed unpacking | retired | `bootstrap()` now returns an attribute-only `BootstrapContext`. |
| repository-level `app.yaml` / `solver.yaml` overrides | retired | Only explicit `local/*.local.yaml` or environment-selected local override files remain supported. |
| main window private `*_impl` aliases | retired | `MainWindow` exposes only the public `on_*` handlers. |
| worker legacy lifecycle payload signals | retired | `BaseWorker` now emits only structured lifecycle events. |

## Budget policy

- `configs/compatibility_budget.yaml` now evaluates against an empty retained-surface set for clean bootstrap and clean headless mainline.
- `scripts/verify_compatibility_budget.py` remains in the gate so retired surfaces do not silently re-enter the runtime.

## Runtime usage logging

- `robot_sim.infra.compatibility_usage` remains available for future migrations, but the current runtime matrix is empty.
