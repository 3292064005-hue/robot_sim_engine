---
owner: architecture
audience: contributor
status: canonical
source_of_truth: manual
last_reviewed: 2026-04-18
---
# Schema and Contracts

## Version catalog

当前版本真源：

- `app_version`: 0.7.0
- `schema_version`: v7
- `session_schema_version`: session-v7
- `benchmark_pack_version`: v7

## Manifest / export versions

- `schema_version`：导出 payload schema version
- `export_version`：writer 使用的导出布局版本
- `producer_version`：生成该 payload 的应用版本

## Session payload contract

session exports 必须至少包含：

- `app_state`
- `active_task_id`
- `active_task_kind`
- `scene_revision`
- `warnings`

并可继续包含：

- `planning_scene` 稳定摘要
- `scene_runtime_summary`
- trajectory collision summary
- render telemetry detail

## Task event schema

worker/task 主链使用结构化事件：

- progress event
- finished event
- failed event
- cancelled event

事件 contract 用于：

- UI 状态投影
- diagnostics
- export/session
- thread orchestration policy

## Error taxonomy

`TaskErrorMapper` 负责把领域错误映射到：

- UI 标题
- 用户提示
- 日志 payload

## Generated reference docs

- `docs/generated/module_status.md`
- `docs/generated/capability_matrix.md`
- `docs/generated/exception_catch_matrix.md`

这些文件属于 checked-in contract docs，应视为参考真源，而不是教程文档。



## Headless CLI / batch contract

`python robot_sim_cli.py batch <command>` 现在是稳定的 machine-readable workflow surface。

当前稳定子命令：

- `import`
- `fk`
- `ik`
- `plan`
- `validate`
- `benchmark`
  - `execution_graph`：benchmark request 现在与 IK / trajectory 一样可显式携带 execution graph descriptor
  - descriptor summary 现在显式包含 `source_topology / selected_scope / supported_scope` 三层 execution-scope contract
- benchmark output metadata：`execution_graph` 为 canonical 字段，`execution_scope` 为兼容别名
- `export-session`
- `export-package`

输入 contract：

- `--request-json '{...}'`
- `--request-file path/to/request.json|yaml`

输出 contract：

- 成功：`{"ok": true, "command": ..., "result": {...}}`
- 失败：`{"ok": false, "command": ..., "error_type": "HeadlessRequestError", "message": ...}`
  - malformed JSON / YAML parse error / file-not-found / non-mapping payload / mutually-exclusive request sources 都属于这一层的稳定 request error

该 surface 绑定现有 use case / export / benchmark 真实现，不允许 GUI-only placeholder 命令。

## Runtime / scene contract additions

当前主链新增并稳定消费以下 contract 字段：

- runtime/import side
  - `primary_execution_surface`
  - `execution_contract_version`
  - `execution_layers`
  - `articulated_topology`
  - `execution_layers.execution_adapter.execution_semantics / execution_scope`
  - importer `runtime_fidelity_contract.source_model_layer / articulated_graph_layer / execution_adapter_layer`
- scene side
  - `last_scene_command`
  - `scene_command_log_tail`
  - `scene_graph_diff`
  - `collision_fidelity.roadmap_stage`
  - `collision_fidelity.stable_surface_target`
  - `collision_fidelity.geometry_requirements`
  - `collision_fidelity.degradation_policy`
  - collision validator `backend_evidence / geometry_contract_evidence`

这些字段均属于“主链已消费 contract”，不是仅供文档展示的注释性 metadata。


## Runtime asset cache invalidation

- `RobotRuntimeAssetService` 现在不只定义 cache，还定义显式 invalidation path。
- invalidation 触发源：runtime context/profile/backend 切换、runtime projection reload、GUI scene edit。
- 当前语义仍是 canonical base runtime asset cache，不会把 GUI scene diff 隐式写回 robot-spec cache。
- 内部 authority 已拆成 kinematic runtime / geometry projection / planning scene authority 三层，再由 `RobotRuntimeAssetService` 对外暴露稳定 facade。
