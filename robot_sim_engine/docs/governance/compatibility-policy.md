---
owner: governance
audience: maintainer
status: canonical
source_of_truth: manual
last_reviewed: 2026-04-17
---
# Compatibility Policy

## 当前结论

当前 shipped mainline **不保留已登记 compatibility surface**。任何未来 compatibility surface 若需要重新引入，必须同时完成：

1. 在 `robot_sim.app.compatibility_matrix.COMPATIBILITY_MATRIX` 登记；
2. 在 `configs/compatibility_downstream_inventory.yaml` 中补 audited downstream inventory；
3. 在 `configs/compatibility_retirement.yaml` 中补 retirement 计划；
4. 更新 `docs/compatibility_*.md` 与对应回归覆盖。

## 已完成的收口方向

- source-tree package shim 已移除
- window/controller facade accessors 已移除
- stable-path widget alias modules 已移除
- worker lifecycle legacy signal surface 已移除
- importer fallback / planning-scene obstacle adapter 已移除
- runtime helper / manifest 层不再暴露公开 compatibility alias surface

## Canonical surfaces

- Main window/runtime composition：`RuntimeServiceBundle`、`WorkflowServiceBundle`、`TaskOrchestrationBundle`
- Robot operations：`RobotWorkflowService`
- Motion operations：`MotionWorkflowService`
- Export operations：`ExportWorkflowService`
- Trajectory export：`export_trajectory_bundle(...)`
- Source-tree entry：`python robot_sim_cli.py ...`

## Audited downstream inventory

当前 `configs/compatibility_downstream_inventory.yaml` 与 `configs/compatibility_retirement.yaml` 均为空，含义是：

- shipped mainline 没有 retained compatibility surface；
- 任何未来兼容面都必须先把 inventory / retirement / evidence 建起来，而不是先上代码再补治理。

## Out-of-tree policy

out-of-tree compatibility consumers **不是默认支持的扩展契约**。一旦确认存在，必须作为显式审计事件处理，而不能继续保持“未知但默认容忍”的状态。

## Rollback / migration rule

如某个版本因 release 风险必须临时保留 compatibility surface，应至少补齐：

- owner
- removal_target
- migration_owner
- inventory_evidence
- known_consumers
- rollback_strategy

否则不得进入 shipped mainline。
