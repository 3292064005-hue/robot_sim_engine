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

该 surface 绑定现有 use case / export / benchmark 真实现，不允许 GUI-only 占位命令。

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

## Headless planning-scene payload contract

The headless `plan`, `validate`, and `export-session` commands accept an optional planning-scene payload. Legacy requests without scene fields remain valid and continue to use the runtime-derived baseline scene.

Accepted scene entry points:

- `planning_scene`: replayable scene snapshot or command payload. A replayable snapshot must include object records under `obstacles` / `attached_objects` or replay commands under `scene_command_history`; diagnostic-only summaries such as `obstacle_ids` are rejected.
- `scene`: alias for `planning_scene`.
- `scene_snapshot`: alias for replayable scene snapshot.
- `scene_diff` / `diff`: incremental obstacle and collision-pair updates applied on top of the baseline scene.
- `obstacles`: shorthand obstacle list for simple automation requests.
- `attached_objects`: shorthand attached-object list.
- `allowed_collision_pairs`: shorthand allowed-collision matrix entries.

Supported primitive obstacle fields:

- `id`, `name`, or `object_id`: stable obstacle identifier.
- `kind` or `shape`: stable headless obstacle primitives are `box`, `sphere`, and `cylinder`.
- `center` or `position`: obstacle center in the scene frame. `pose.position` is also accepted as an alias.
- `size` or `dimensions`: box dimensions.
- `radius`: sphere radius, or cylinder radius.
- `height` or `length`: cylinder height.
- `metadata`: optional user metadata.

Boundary behavior:

- When a scene payload is present, headless parsing fails closed on malformed, empty, unknown, or diagnostic-only payloads. A non-empty payload must contain at least one executable scene field.
- Caller-provided scenes are labeled `caller_scene` once they cross the application façade.
- Requests without scene payloads are labeled `runtime_default_scene` and keep the previous fallback semantics.
- Scene summaries written by plan/validate/export-session include `scene_truth_layer`, `materialization_source`, and `scene_materialization_revision_key` from `SceneSessionAuthority`; this key includes a stable content hash so same-revision scenes with different objects do not share cache partitions.
- Unsupported primitive declarations such as `mesh` or `capsule` fail closed in the stable headless scene payload instead of being silently approximated.
- Mesh and capsule collision support remains governed by importer/runtime collision-fidelity capabilities, not by the stable obstacle shorthand schema.

## Docs-to-contract matrix

| Capability claim | Executable contract |
| --- | --- |
| GUI/session planning scene reaches planning | `tests/unit/test_scene_contract_pipeline.py::test_gui_motion_workflow_forwards_session_planning_scene` |
| Headless scene payload reaches canonical request | `tests/unit/test_scene_contract_pipeline.py::test_headless_plan_scene_payload_reaches_application_request` |
| Session export prefers caller/session scene truth over rebuilt runtime assets | `tests/unit/test_scene_contract_pipeline.py::test_session_projection_prefers_caller_scene_truth` |
| Malformed scene diff payloads fail closed | `tests/unit/test_scene_contract_pipeline.py::test_headless_scene_diff_non_mapping_fails_closed` |
| Replayable full scene snapshots restore obstacle records | `tests/unit/test_scene_contract_pipeline.py::test_headless_full_snapshot_replays_exported_obstacle_records` |
| Diagnostic-only or unknown scene payloads fail closed | `tests/unit/test_scene_contract_pipeline.py::test_headless_unknown_or_diagnostic_only_scene_payload_fails_closed` |
| Malformed allowed-collision payloads fail closed | `tests/unit/test_scene_contract_pipeline.py::test_headless_malformed_allowed_collision_pairs_fail_closed` |
| Runtime materialization cache partitions by scene revision | `tests/unit/test_scene_contract_pipeline.py::test_runtime_asset_cache_partitions_by_scene_materialization_revision` |
| Stable obstacle aliases match implementation support | `tests/unit/test_scene_contract_pipeline.py::test_headless_obstacle_aliases_are_normalized_and_unsupported_shapes_fail` |
| Validation capability metadata exposes required keys | `tests/unit/test_scene_contract_pipeline.py::test_validation_capability_schema_uses_required_keys` |
| PlanningScene remains export-serializable | `tests/unit/test_planning_scene_session_export.py` |
| Legacy trajectory workflow compatibility remains intact | `tests/unit/test_motion_workflow_contracts.py` |

## Validation capability summary

Planning, validation, and session export metadata may expose `validation_capabilities` to prevent ambiguity about the active safety surface. The summary distinguishes stable checks from partial or unsupported checks.

Required capability keys:

- `joint_limits`: joint vector and trajectory limit validation status.
- `goal_validation`: final-goal validation status.
- `collision_broad_phase`: broad-phase collision coverage status.
- `continuous_collision`: continuous collision status; currently `False` unless a future continuous checker records support.
- `mesh_collision`: mesh collision status; currently `False` for the stable scene obstacle shorthand.
- `attached_object_validation`: attached-object collision status.
- `allowed_collision_matrix`: allowed-collision matrix status.
- `scene_validation_mode`: validation mode selected by the runtime scene/fidelity profile.
- `scene_validation_precision`: effective scene-validation precision hint.

Profiles that intentionally skip full collision validation must surface this through `validation_capabilities` and result metadata instead of relying on implicit profile knowledge.
