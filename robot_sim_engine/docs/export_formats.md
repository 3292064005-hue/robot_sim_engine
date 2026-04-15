# Export Formats

## trajectory bundle (`.npz`)

包含字段：

- `t`
- `q`
- `qd`
- `qdd`
- `ee_positions`（若有）
- `joint_positions`（若有）
- `ee_rotations`（若有）
- `manifest_json`
- `metadata_json`
- `quality_json`
- `feasibility_json`

## benchmark report (`.json`)

包含字段：

- `robot`
- `num_cases`
- `success_rate`
- `cases`
- `aggregate`
- `metadata`
- `comparison`

## benchmark cases (`.csv`)

按 case 明细导出，每行一个 benchmark case 结果。

## session (`.json`)

保存当前机器人、位姿、IK 结果、trajectory 概要、benchmark 概要与 playback 状态。manifest 现同时记录 `bundle_kind=session_snapshot`、resolved config snapshot、scene snapshot 与 plugin/runtime feature snapshot；render telemetry 支持 `full` 与 `minimal` 两档导出粒度。

## package (`.zip`)

当前 package 明确定义为 **artifact/audit bundle**，包含一组导出工件及 `manifest.json`，manifest 中会显式记录：

- `bundle_kind=artifact_bundle`
- `bundle_contract=artifact_audit_bundle`
- package 导出的内嵌 `session.json` 默认使用 `telemetry_detail=minimal`，仅保留计数/序列等最小观测集；显式导出 session 仍默认 `full`。
- `replayable=false`
- runtime environment snapshot
- resolved config snapshot
- scene snapshot
- plugin/runtime feature snapshot
