---
owner: architecture
audience: contributor
status: canonical
source_of_truth: manual
last_reviewed: 2026-04-20
---
# Architecture Overview

## 分层

- `model`：FK / IK / trajectory / benchmark / export manifest 等不可变结果对象
- `core`：纯数学与纯规则内核，不依赖 Qt
- `application`：DTO、registry、use case、service、worker
- `presentation`：主窗口、controller、coordinator、thread orchestrator、widget
- `render`：PyVista / pyqtgraph 适配、截图、plot sync、render telemetry
- `infra`：配置、日志、文件、schema、质量门禁支撑

## 当前主线设计原则

1. `src/robot_sim` 是唯一运行/打包真源
2. `core` 不导入 Qt
3. GUI 线程只负责参数收集、状态投影与渲染调用
4. 重任务通过 worker + `ThreadOrchestrator` 走结构化生命周期
5. 场景语义、导入 fidelity、render runtime、export/session contract 都必须有明确 authority 和 summary

## Registry / plugin entry

当前这些能力通过 registry 接入：

- `solver_registry`
- `planner_registry`
- `importer_registry`
- scene / collision backend runtime plugins

插件装配规则：

- manifest 必须通过 `PluginLoader` 静态校验
- `features.plugin_status_allowlist` 决定允许装配的 rollout 等级
- `plugin_discovery_enabled=false` 时，仅允许 `builtin / shipped_plugin` 继续装配
- host capability negotiation 决定 research/experimental plugin 是否可载入
- `PluginLoader.audit_split()` 现在显式拆分 **governance registrations** 与 **capability registrations**：alias-only shipped plugin 仍保留审计/治理身份，但不会再伪装成新的 runtime provider

扩展新能力时，不应直接把逻辑塞进 `MainWindow` 或总控制器；应先定义 contract，再经 registry / loader / service 装配。

## Presentation split

当前激活的 GUI 编排面已收口为：

- `RobotWorkflowService`
- `MotionWorkflowService`
- `ExportWorkflowService`
- `DiagnosticsController`

其中 **canonical application path** 为 `ApplicationWorkflowFacade -> use cases / runtime services`；`MotionWorkflowService`、`RobotWorkflowService` 与 `HeadlessWorkflowService` 只负责各自表面的状态投影或 transport 适配。`IKController / TrajectoryController / BenchmarkController / ExportController` 仍保留在仓库中，但它们现在只承担兼容测试、窄表面适配或 editor/runtime projection 辅助职责，不再参与主启动图，也不应再各自维护独立 request DTO 装配逻辑。

主窗口依赖已收口到三类 bundle；应用容器同时补充了 `registry_bundle / service_bundle / workflow_bundle / bootstrap_bundle / workflow_facade`，避免新的启动/编排代码继续直接铺开 mega-container：

- `RuntimeServiceBundle`
- `WorkflowServiceBundle`
- `TaskOrchestrationBundle`

## 数据与 authority 约束

- trajectory 必须携带 `metadata / feasibility / quality`
- playback 走预缓存 FK，不在 UI 线程做 live FK fallback
- Euler angle 只允许出现在 UI 输入层
- scene summary 必须同时暴露 `declaration_geometry / validation_geometry / render_geometry`
- `planning_scene.summary()` 必须显式给出 geometry authority / scene graph authority
- importer/registry/runtime/export 主链优先消费 typed object（`ImportedRobotPackage`、`ArticulatedRobotModel`、`RobotGeometryModel`），不再以 metadata 充当唯一 authority

## Registry / execution scope / runtime asset 分层

- `RobotRegistry` 现在只保留 orchestration；目录查找、YAML transport、spec 映射、source_path 归一化分别由 `RobotCatalogStore`、`RobotSpecSerializer`、`RobotSpecMapper`、`SourcePathNormalizer` 负责。
- `execution_graph` 已显式区分 `source_topology / selected_scope / supported_scope`，并由 `ExecutionScopeService` 执行 fail-closed negotiation；协商结果会同步投影 `execution_capability_matrix`，把 source-model fidelity 与 runtime execution capability 分开表达。
- `RobotRuntimeAssetService` 内部继续保留 façade，但 cache / invalidation、kinematic runtime、geometry projection、planning scene authority 已分层，后续 scene / dynamics 扩展不再继续堆到单一 service。
- `workflow_services.py`、`workflow_facade.py`、`container.py`、`runtime_asset_service.py` 现仅保留稳定导出路径；具体实现分别下沉到 `presentation/workflows`、`app/workflows`、`app/container_{types,builder}.py`、`application/services/runtime_assets/*`，避免兼容入口再次回长成中心文件。
- trajectory pipeline 现在同时支持 shipped stage bundle 与 `trajectory.stage_catalog` 外置声明；新增 stage provider 必须通过工厂路径显式注册，而不是继续把阶段硬编码进 registry。
