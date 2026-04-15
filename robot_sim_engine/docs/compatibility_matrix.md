# Compatibility Matrix

This document enumerates the intentionally retained compatibility paths that still exist in V7.2. They are no longer treated as implicit mainline behavior, and new code should stay on the canonical attribute-based APIs.

| Surface | Owner | Compatibility path | Rationale | Removal target |
|---|---|---|---|---|
| bootstrap iterable unpacking | `robot_sim.app.bootstrap.BootstrapContext` | attribute-first bootstrap result with iterable/indexed compatibility for historical unpacking | Older startup callers may still destructure or index the bootstrap result like the historical tuple. | v0.9 |
| legacy config overrides | `ConfigService` | repository-level `app.yaml` / `solver.yaml` override opt-in | Some ad-hoc local workflows may still rely on repository-side override files. | v0.9 |
| main window private alias shim | `MainWindowLegacyAliasMixin` | removed `*_impl` names redirect to public `on_*` handlers | Historical automation may still probe removed private names during staged migration. | v0.9 |
| worker legacy lifecycle signals | `BaseWorker` | legacy `progress` / `finished` / `failed` / `cancelled` signals mirrored from structured events | Existing callbacks and older workers still consume the historical signal surface. | v0.9 |
| presentation facade alias adapters | `robot_sim.presentation.facades` | retained `robot/solver/trajectory/playback/benchmark/export` facade names forward to workflow services through adapter-only concrete types | Historical callers may still depend on facade names or concrete facade classes during staged migration. | v0.9 |

## Governance rules

1. Structured worker events are the canonical lifecycle protocol.
2. Compatibility logic should be confined to adapters/shims and must not become a new mainline implementation path.
3. Any removal must be preceded by a deprecation cycle and by usage validation in downstream automation.

## Runtime usage logging

- `configs/compatibility_budget.yaml` 定义 clean bootstrap / clean headless mainline 的兼容旁路预算，`scripts/verify_compatibility_budget.py` 会在质量门禁中直接执行这些场景，防止旧兼容面重新渗回主链。


- All retained compatibility surfaces are now recorded at runtime through `robot_sim.infra.compatibility_usage.record_compatibility_usage(...)`.
- Logging is de-duplicated per surface/detail pair to avoid noisy repeated warnings during long GUI sessions.
- In-memory usage counters remain available for tests and future telemetry-driven removal planning.
- `scripts/verify_compatibility_budget.py --report-out artifacts/compatibility_usage_report.json` now persists both aggregate counts and per-surface detail counts so compatibility retirement can bind to concrete alias/config consumers.
- `configs/compatibility_downstream_inventory.yaml` is now the audited downstream-consumer inventory for every retained compatibility surface, and `configs/compatibility_retirement.yaml` mirrors that inventory into removal planning. Together they record concrete in-repo consumers, the audited out-of-tree result for each surface, explicit removal checklists, and rollback steps. `docs/compatibility_support_boundary.md` defines that deprecated compatibility surfaces are internal-only and must be explicitly audited before any out-of-tree caller can be treated as confirmed. `python scripts/verify_compatibility_retirement.py` validates that the retirement plan stays aligned with the audited downstream inventory before release evidence is accepted.
- Presentation facade adapters are instantiated lazily from canonical workflows; a clean mainline run should not pay facade construction cost unless a compatibility surface is explicitly accessed.

## Removed in V7.2

- repository-root `robot_sim` package shim 已移除。源码态调用方必须改为 `pip install -e .` 或显式 `PYTHONPATH=src`，避免绕过 `src-layout` 的安装/打包边界。
