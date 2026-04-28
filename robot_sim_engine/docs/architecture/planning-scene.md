---
owner: architecture
audience: contributor
status: canonical
source_of_truth: manual
last_reviewed: 2026-04-20
---
# Planning Scene / ACM

`PlanningScene` 现已进入当前工程的**stable scene surface**，作为环境障碍物、允许碰撞矩阵（ACM）与 scene revision 的统一 authority，并持续服务于校验、导出、session 与 stable scene toolbar/editor。校验主链现在只接受 canonical `planning_scene` 输入。


当前稳定能力范围：

- 环境障碍物与 attached objects 现在支持 `box / sphere / cylinder` 三类稳定 primitive；scene authority 统一收口为 declaration geometry，validation/query 几何通过显式 backend runtime projection 派生，稳定 summary / diagnostics / export 会同时保留 declaration / validation / render 三层 geometry 语义。
- `AllowedCollisionMatrix` 可显式声明 link-link 或 link-object 的 ignore pairs
- `ValidateTrajectoryUseCase` 可接受 `planning_scene`，并输出：
  - `scene_revision`
  - `collision_level`
  - `ignored_pairs`
  - `self_pairs`
  - `environment_pairs`
- session / export 路径会保留 `planning_scene` 的稳定摘要信息（`revision`、`collision_backend`、`obstacle_ids`、`attached_object_ids`、`allowed_collision_pairs`、`geometry_source`、`scene_authority`、`scene_fidelity`、`scene_validation_mode`、`scene_validation_precision` 等字段）；运行时附加摘要单独写入 `scene_runtime_summary`，不再混入 `planning_scene`，并新增 `scene_fidelity_summary` 作为面向用户可见导出/会话的最小 fidelity contract。该 contract 现显式保留 `collision_backend`、`collision_level`、`scene_fidelity`、`precision`、`stable_surface`、`promotion_state`、`backend_status`、`backend_availability`、`scene_validation_mode`、`scene_validation_precision` 与 `scene_geometry_contract`。

当前 stable 主链已补齐 authority 与编辑面：

- 机器人加载 / 导入 / 编辑保存后，运行时会自动重建一份 canonical `planning_scene`
- stable 主窗口会投影 scene backend / revision / obstacle / pair 摘要
- stable `SceneToolbar` 现通过结构化 scene editor 提供 `box / sphere / cylinder` primitive、attached object 与 allowed collision pairs 的编辑入口
- stable scene summary / session export / diagnostics 现在显式暴露 `collision_fidelity` 摘要（level/backend/precision/promotion_state/stable_surface），避免把 AABB 与 capsule 等 backend 说成同一级别语义
- `SceneAuthorityService` 统一管理 scene bootstrap、障碍物 ID 策略、ACM 写入与 scene metadata；scene summary 现显式输出 `scene_geometry_contract`、对象级 `declaration_geometry` / `validation_geometry` / `render_geometry`
- AABB collision backend 仍是 shipped 默认稳定后端；scene/collision backend 现在通过真实 runtime plugin 安装进入主链，非默认更高保真 backend 仍需满足独立 promotion 条件后才会成为稳定承诺。

当前仍不包含：

- 连续碰撞检测
- FCL / mesh 级精确碰撞
- 完整 attached-object authoring
- 多 collision backend 的完整产品化切换


## Scene command / diff authority

- `SceneAuthorityService` 现在除直接返回更新后的 `PlanningScene` 外，还提供命令化入口：`execute_obstacle_edit()` 与 `execute_clear_obstacles()`。
- 每次主链 mutation 都会生成 `SceneCommand`，并把 `command_kind / source / object_id / revision_before / revision_after / scene_graph_diff / metadata` 写入 scene summary。
- `PlanningScene.summary()` 现稳定暴露 `last_scene_command`、`scene_command_log_tail`、`scene_command_history`、`scene_revision_history`、`replay_cursor`、`clone_token`、`concurrent_snapshot_tokens`、`diff_replication` 与 `environment_contract`，用于 diagnostics / export / session 的**环境 authority 证据面**，避免 UI 只暴露编辑结果而没有 authority-level 变更语义。
- `SceneAuthorityService` 现提供 `clone_scene()`、`apply_scene_command()` 与 `replay_scene()`，主链环境 contract 已升级为 cloneable / replay-aware / diff-replication-aware / concurrent-snapshot-aware。
- 当前 command history 仍不是外部事件数据库；它是受控、可导出的 runtime environment contract，而不是任意扩展的持久化 event store。

## Collision fidelity roadmap contract

- collision fidelity roadmap 已从硬编码摘要提升为外置配置：`configs/collision_fidelity.yaml`。
- stable summary 除 `precision / stable_surface / promotion_state` 外，额外保留：
  - `roadmap_stage`
  - `stable_surface_target`
  - `geometry_requirements`
  - `degradation_policy`
  - `capability_contract_version`
- 这使 UI/diagnostics/export 可以区分“当前稳定承诺”和“未来 promotion 目标”，避免把 capsule / mesh 等能力伪装成已经稳定闭环。

## Scene truth and runtime materialization boundary

The planning scene has three distinct roles:

| Layer | Responsibility |
| --- | --- |
| `BaselinePlanningScene` | Robot-spec and geometry-derived default scene. |
| `SessionPlanningScene` | Caller or GUI session truth used by plan, validate, and export-session. |
| `MaterializedPlanningScene` | Runtime projection used by collision/render backends and capability summaries. |

Application façade behavior:

- `SceneSessionAuthority` is the explicit resolver for session scene truth versus runtime materialization.
- Explicit caller/session scenes always win and are labeled `caller_scene`.
- Rebuilt runtime-asset scenes are fallback materializations and are labeled `runtime_default_scene`.
- Each resolved boundary emits `scene_truth_layer`, `materialization_source`, and `scene_materialization_revision_key` so exports and tests can prove which scene was consumed.
- `RobotRuntimeAssetService.build_assets()` accepts `scene_materialization_revision_key` and includes it in the runtime asset cache key. The key is content-addressed: `SceneSessionAuthority.revision_key()` hashes replay-relevant scene content, including obstacles, attached objects, allowed collision pairs, backend, geometry source, and revision. This partitions materialization diagnostics by caller/session scene content while keeping session scene truth owned by `SceneSessionAuthority`.
- Runtime asset cache invalidation does not itself persist scene edits or make edited obstacles canonical.
- Export-session serializes the session planning-scene truth; materialization metadata remains diagnostic context.

This boundary keeps GUI scene edits, headless scene payloads, validation, and export-session replay aligned without deleting the baseline-scene fallback used by legacy no-scene requests.
