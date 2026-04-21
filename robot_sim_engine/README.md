# Robot Sim Engine

基于纯数学推导的多自由度机械臂运动学、轨迹规划与场景校验仿真引擎。

`src/robot_sim` 是唯一运行/打包真源。源码态入口统一使用 `python robot_sim_cli.py ...`，安装态入口使用 `robot-sim` / `robot-sim-gui`。

## 这是什么

当前交付版本为 **V7 工程硬化版**。这一版的主线目标不是继续堆新功能，而是把运行时真源、任务生命周期、导入 fidelity、trajectory validators、scene authority、render telemetry、export/package、plugin/runtime contracts 和质量门禁全部收口到可审计的工程形态。

当前稳定发布线面向**确定性运动学 / 轨迹规划 / 场景校验 / benchmark / export 合同**这一条工程主线；它不是对外宣称的刚体动力学 / 接触 / 闭环物理仿真平台。若未来进入 full simulator 赛道，将按独立 capability track 演进，而不是把现有 execution adapter 边界伪装成已支持的动力学系统。

当前稳定能力重点：

- 统一版本真源：`VersionCatalog` / app / export / session / benchmark pack / 文档口径对齐
- 正式任务生命周期：`TaskState`、`TaskSnapshot`、worker structured events、增强版 `ThreadOrchestrator`
- importer V7：`RobotModelBundle`、importer registry 与 importer 实现拆分、fidelity 明文化
- pose/transform contract：`Pose` / `Transform` 统一校验、组合、逆变换与四元数投影
- trajectory 校验拆分为 validators：timing / path metrics / goal / limits / collision
- trajectory pipeline 已具名化：`trajectory.pipeline_id` / request `pipeline_id` 统一选择可组合规划流水线，`trajectory.pipelines` 可在 profile / local override 中装配具名 pipeline，默认仍为 `default`
- GUI 协调层：coordinator 下沉，主窗口依赖收口到 runtime/workflow/task bundles
- GUI 导入改为 staged load：导入先进入运行时暂存，后续由“保存 YAML”显式落库，避免 UI 导入即写盘
- render runtime state：`scene_3d / plots / screenshot` 降级原因统一进入 `SessionState.render_runtime`
- render telemetry stream：render 能力状态、operation spans、sampling counters、backend performance 已统一进入共享 telemetry 真源
- scene authority：scene declaration / validation / render 三层几何契约已经接入稳定 summary / diagnostics / export 面

## 快速开始

```bash
pip install -e .[dev]
python robot_sim_cli.py source-layout-smoke
python scripts/run_tests.py
python -m pytest -q
python scripts/verify_runtime_baseline.py --mode headless
python -m build
```

GUI 运行：

```bash
robot-sim-gui
# 或源码态
python robot_sim_cli.py gui
```

Headless / 批处理运行：

```bash
python robot_sim_cli.py batch import --request-json '{"robot": "planar_2dof"}'
python robot_sim_cli.py batch fk --request-json '{"robot": "planar_2dof", "q": [0.0, 0.0]}'
python robot_sim_cli.py batch plan --request-file examples/headless_plan_request.yaml --output artifacts/headless_plan.json
```

说明：`batch` 子命令统一消费 JSON/YAML contract，并返回 machine-readable JSON。请求解析现在先经 `HeadlessRequestContractAdapter`，因此 malformed JSON/YAML、文件缺失、非 mapping payload、互斥参数冲突都会在 bootstrap 前返回稳定 `HeadlessRequestError` payload，而不是散落到 GUI 逻辑里。

新的 headless / GUI 主链统一支持：
- canonical GUI 轨迹 contract 统一经 `MotionWorkflowService -> application.request_builders` 生成；legacy `TrajectoryController` 仅保留兼容包装层，不再拥有独立 DTO 装配真源
- `trajectory.pipeline_id`：选择具名 trajectory pipeline（默认 `default`）
- `trajectory.pipelines`：声明 profile/local override 可装配的 pipeline stage 组合（planner / retime / validate / postprocessors）
- `execution_graph`：显式记录 active-path-over-tree 执行描述，IK / trajectory / benchmark 统一消费这一 contract；descriptor 现在经 `ExecutionScopeService` fail-closed 解析，并同时暴露 `source_topology / selected_scope / supported_scope` 三层 execution-scope summary，不允许调用方静默声明 full-tree / closed-loop 等未支持策略；benchmark 输出 metadata 以 `execution_graph` 为 canonical 字段，并保留 `execution_scope` 兼容别名，作为后续 branched execution 升级的稳定 contract
- `ApplicationWorkflowFacade`：GUI / headless 的 import / load / fk / ik / plan / validate / benchmark / export-session / export-package 统一经这一 façade 执行；GUI 仅负责状态投影与任务生命周期，headless 仅负责 transport 解析与 JSON 序列化
- `RobotRegistry`：现已拆为 `RobotCatalogStore / RobotSpecSerializer / RobotSpecMapper / SourcePathNormalizer` 四层职责，registry 本体只保留 orchestration

## 文档导航

- 文档总索引：`docs/index.md`
- headless CLI / machine-readable contract：`docs/reference/schema-and-contracts.md`
- 上手与仓库结构：`docs/getting-started/quickstart.md`、`docs/getting-started/repository-layout.md`
- 架构主线：
  - `docs/architecture/overview.md`
  - `docs/architecture/execution-model.md`
  - `docs/architecture/planning-scene.md`
  - `docs/architecture/importer-model.md`
  - `docs/architecture/render-runtime.md`
- 使用/扩展指南：
  - `docs/guides/configuration-profiles.md`
  - `docs/guides/plugin-development.md`
  - `docs/guides/export-and-session.md`
  - `docs/guides/packaging-and-release.md`
  - `docs/guides/testing-and-quality.md`
- 参考真源：
  - `docs/reference/schema-and-contracts.md`
  - `docs/reference/benchmark-suite.md`
  - `docs/reference/kinematics-and-trajectory.md`
  - `docs/reference/generated-contracts.md`
- 治理与路线：
  - `docs/governance/compatibility-policy.md`
  - `docs/governance/documentation-governance.md`
  - `docs/governance/technical-debt.md`
  - `docs/governance/roadmap.md`
  - `docs/governance/external-code-intake-policy.md`

说明：`docs/` 根目录下仍保留一组 legacy entry pages，用于兼容既有链接、质量门禁和生成脚本；**canonical 讲解文档** 已迁移到上述分层目录。文档治理规则见 `docs/governance/documentation-governance.md`。

## V7 质量门禁

当前门禁已显式分层：

- release blockers：`python scripts/verify_release_blockers.py`
- runtime contracts：`python scripts/verify_runtime_gate_layer.py`
- governance evidence：`python scripts/verify_governance_gate_layer.py`

分层展开（与 `src/robot_sim/domain/quality_gate_catalog.py` 和 `docs/generated/quality_gates.md` 保持一致）：

- release blockers：`python scripts/verify_release_blockers.py` ⇒ `quick_quality` + `compatibility_budget` + `unit_and_regression` + `gui_smoke`
- runtime contracts：`python scripts/verify_runtime_gate_layer.py` ⇒ `runtime_contracts` + `performance_smoke` + `headless_runtime_baseline` + `planning_scene_regression` + `collision_validation_matrix` + `scene_capture_baseline`
- runtime contract gate：`python scripts/verify_runtime_contracts.py --mode headless --check-packaged-configs` + `python scripts/verify_compatibility_retirement.py` + `python scripts/verify_perf_budget_config.py`
- runtime baseline/details：`python scripts/verify_runtime_baseline.py --mode headless` + `pytest tests/unit/test_planning_scene_v2.py tests/unit/test_scene_authority_service.py -q` + `pytest tests/unit/test_planning_scene_validation.py tests/unit/test_scene_capability_surface.py -q` + `pytest tests/unit/test_scene_capture_support.py tests/unit/test_scene_render_contracts.py -q` + `pytest tests/performance/test_ik_smoke.py -q`
- governance evidence：`python scripts/verify_governance_gate_layer.py` ⇒ `governance_evidence` + `docs_sync`
- governance evidence detail：`python scripts/verify_module_governance.py --execute-gates --evidence-out artifacts/module_governance_evidence.json` + `python scripts/verify_benchmark_matrix.py --execute-gates --execute --evidence-out artifacts/benchmark_matrix_evidence.json` + `python scripts/collect_quality_evidence.py --out artifacts/quality_evidence.json --markdown-out artifacts/quality_evidence.md --release-manifest-out artifacts/release_manifest.json --merge artifacts/module_governance_evidence.json artifacts/benchmark_matrix_evidence.json runtime_contracts compatibility_budget performance_smoke`
- unit/regression：`pytest tests/unit tests/regression -q`；CI 仍以 `pytest --collect-only -q` 的实际收集结果为准，避免把局部子集通过误写成全量验证结论。
- shipped behavior contracts：repo profiles 必须保持可区分；coordinator 主链必须继续走显式依赖注入；`export` / `screenshot` 主链必须继续走 worker 生命周期；render 降级状态必须沉入 `SessionState.render_runtime` 并经 typed status-panel subscription 流转；render telemetry 必须继续被 diagnostics / export / quality gate 消费；scene authority summary 必须同时暴露 declaration / validation / render geometry layers；public plugin SDK 示例必须保持可装配；snapshot renderer 与 importer fidelity 基线必须能通过已提交 fixture 复现
- full validation：`pytest --cov=src/robot_sim --cov-report=term-missing --cov-report=json:coverage.json -q` + `python scripts/verify_partition_coverage.py --coverage-json coverage.json`，coverage `fail_under = 80`
- gui smoke：执行 `python scripts/verify_gui_smoke.py`；该 gate 优先使用真实 `PySide6`，若当前环境未提供 Qt，则仅在验证进程内启用仓库自带的受控 Qt test shim 做 offscreen smoke。证据必须保留 `runtime_kind`、`gui_real_runtime_ok`、`gui_shim_runtime_ok`。
- clean source bundle：执行 `python scripts/package_release.py --output dist/source-release.zip --top-level-dir robot_sim_engine`；该脚本会先构造一个可写 staging 树，在 staging 中再生成并校验 contract docs，然后才输出最终 clean source bundle，避免把 stale docs 或本地工件直接打包出去。
- contract regeneration：执行 `python scripts/regenerate_quality_contracts.py` + `python scripts/verify_docs_information_architecture.py` 后，`docs/` 目录不得产生未提交 diff；文档 gate 会强制检查 canonical / entry-page / generated 三层关系与 explanatory-doc semantic coverage。

当前测试基线：**以 CI / pytest 实际收集结果为准**。建议在做主链改动时至少执行：

```bash
python scripts/verify_release_blockers.py
python scripts/verify_runtime_gate_layer.py
python scripts/verify_governance_gate_layer.py
python scripts/verify_runtime_contracts.py --mode headless --check-packaged-configs
python scripts/verify_compatibility_budget.py --scenario clean_headless_mainline
python scripts/verify_gui_smoke.py
python scripts/regenerate_quality_contracts.py
python scripts/regenerate_importer_fidelity_baseline.py
python scripts/package_release.py --output dist/source-release.zip --top-level-dir robot_sim_engine
pytest tests/unit tests/regression -q
```

## Experimental 模块

以下模块当前明确标记为 experimental，不纳入稳定主链承诺：

- `presentation.experimental.widgets.collision_panel`
- `presentation.experimental.widgets.export_panel`
- `presentation.experimental.widgets.scene_options_panel`
- `render.experimental.picking`
- `render.experimental.plot_sync`

## 运行环境与 profile

- 操作系统：**Ubuntu 22.04 LTS**
- Python：**3.10+**，CI 与本地建议优先使用 **3.10**
- GUI 框架：**PySide6 >= 6.5**
- 3D 渲染：**PyVista >= 0.43**、**pyvistaqt >= 0.11**
- 2D 曲线：**pyqtgraph >= 0.13**

常用 profile：

- `configs/profiles/default.yaml`：共享默认基线
- `configs/profiles/dev.yaml`：本地开发配置
- `configs/profiles/ci.yaml`：CI 回归配置
- `configs/profiles/gui.yaml`：GUI 运行配置
- `configs/profiles/release.yaml`：发布打包配置

运行时 feature policy：

- 默认 / GUI / CI / release profile 均关闭 experimental 模块运行时启用、experimental backend 宣告与外部 plugin discovery
- `research.yaml` 显式开启：
  - `experimental_modules_enabled`
  - `experimental_backends_enabled`
  - `plugin_discovery_enabled`

## Compatibility / schema / generated docs

- compatibility matrix：当前 shipped mainline 不保留兼容旁路；若未来必须重新引入兼容面，仍需先登记到 `docs/compatibility_matrix.md` 与 `robot_sim.app.compatibility_matrix.COMPATIBILITY_MATRIX`，再通过 `robot_sim.infra.compatibility_usage.record_compatibility_usage(...)` 进行审计。
- schema / contract 真源请优先阅读 `docs/reference/schema-and-contracts.md`，生成型参考仍保留在：
  - `docs/generated/capability_matrix.md`
  - `docs/generated/module_status.md`
  - `docs/generated/exception_catch_matrix.md`
- importer fidelity baseline：`tests/regression/baselines/importer_fidelity_baseline.json` 由 `python scripts/regenerate_importer_fidelity_baseline.py` 维护，用于锁定 native YAML 与 structured URDF 导入摘要。

## License and third-party intake

- repository license: `MIT`
- third-party intake register: `THIRD_PARTY_NOTICES.md`
- source absorption policy: `docs/governance/external-code-intake-policy.md`
