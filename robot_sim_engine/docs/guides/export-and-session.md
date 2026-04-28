---
owner: docs
audience: contributor
status: canonical
source_of_truth: manual
last_reviewed: 2026-04-17
---
# Export and Session Guide

## 导出类型

- trajectory bundle (`.npz`)
- benchmark report (`.json`)
- benchmark cases (`.csv`)
- session snapshot (`.json`)
- artifact bundle / package (`.zip`)

## trajectory bundle

典型字段：

- `t`
- `q`
- `qd`
- `qdd`
- `ee_positions`
- `joint_positions`
- `ee_rotations`
- `manifest_json`
- `metadata_json`
- `quality_json`
- `feasibility_json`

## session snapshot

当前 session 导出会保留：

- 当前机器人/位姿/IK/trajectory/benchmark/playback 摘要
- `planning_scene` 稳定摘要
- `scene_runtime_summary`
- runtime/config/plugin snapshot
- render telemetry（`full` / `minimal` 两档）

## package / artifact bundle

package 语义是 **artifact/audit bundle**，不是“可重放工程目录快照”。manifest 会显式记录：

- `bundle_kind=artifact_bundle`
- `bundle_contract=artifact_audit_bundle`
- `replayable=false`
- runtime environment snapshot
- resolved config snapshot
- scene snapshot
- plugin/runtime feature snapshot

## 注意事项

- session / package schema 必须版本化
- manifest 只暴露 canonical 字段，不再把 migration alias 作为正式 schema surface 输出
- 变更 export schema 时，必须同步更新 `docs/reference/schema-and-contracts.md` 与相关回归

## Headless scene-aware session export

`export-session` now accepts the same optional scene payload accepted by headless `plan` and `validate`. When a caller supplies a scene payload, the exported session records that caller scene as the session planning-scene truth. Runtime assets are still built to materialize geometry and backend summaries, but rebuilt runtime assets do not override the caller scene.

Recommended automation pattern:

1. Submit a replayable `planning_scene` / `scene_snapshot` payload with `obstacles`, `attached_objects`, or `scene_command_history`, or submit a `scene_diff` / `obstacles` shorthand payload. Diagnostic-only snapshots such as `obstacle_ids` are rejected instead of being treated as caller scenes.
2. Inspect `scene_runtime_summary.planning_scene_source` in the exported JSON.
3. Treat `caller_scene` as the reproducible session input and `runtime_default_scene` as the legacy baseline fallback.
4. Keep exported `validation_capabilities` with the session artifact so downstream consumers can identify whether collision, mesh, attached-object, or ACM checks were stable, partial, planned, or unsupported at export time.

Rollback and compatibility behavior:

- Existing `export-session` requests without scene payloads remain valid.
- The previous runtime-derived baseline scene remains the fallback.
- Consumers that do not read the new metadata fields can continue to load the exported session payload.
