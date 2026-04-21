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
