# Technical Debt Register

## 已关闭

- 版本口径分散：已统一到 `VersionCatalog`
- `MainWindow` 单文件过重：已拆成 `main_window.py` + mixins
- importer registry 与 importer 实现混放：已拆分
- trajectory validator 大一统：已拆分为 validators
- 任务生命周期字符串散落：已统一为 `TaskState` / `TaskSnapshot` / structured worker events
- `ThreadOrchestrator` 缺失 `queue_latest` / timeout 异常流：已补齐
- `PlanTrajectoryUseCase` 残留 `v4` 版本漂移：已改为 `v7` 版本真源

## 当前已知边界

- 稳定 GUI/worker/thread/model 主链已移除本地 Qt fallback/dummy shim；生产代码只接受真实 `PySide6`，非 GUI 自动化测试（`tests/unit`、`tests/regression`）仅在测试进程内注入 `robot_sim.testing.qt_shims` 伪 `PySide6` 包。
- CI 默认以 Ubuntu 22.04 + Python 3.10 作为一致性基线，GUI 相关测试仍会按依赖自动跳过
- `mypy` 仍聚焦关键核心路径，未宣称对全部 GUI 壳层进行完全类型化治理

## 后续建议

- 若进入 V8，可继续把 render telemetry 扩展到长周期 retention / 离线分析索引，但 percentile、rolling-window 指标、rate/throughput 与 diagnostics timeline 已不再属于当前主链缺口。

## 本轮已收口债务

- 执行真源分散 metadata：FK/Jacobian/数值 IK 已切到 `RobotSpec.articulated_model` 真执行面；`RobotSpec.execution_summary` 仅保留 runtime/export/compatibility 摘要职责。
- screenshot service 直连 coordinator：已收口到 `CaptureSceneUseCase`，coordinator 仅保留编排职责。
- export workflow 语义漂移：`ExportWorkflowService` 不再承载 `import_robot()` 旁路。
- MainWindow UI Qt helper 已拆到 `presentation.main_window_qt_helpers`，scene authority 归一化已拆到 `application.services.scene_authority_support`，render telemetry backend 聚合已拆到 `model.render_telemetry_backend_performance`，热点文件职责继续收口。
- 运行时路径寻址：已统一到 `RuntimePaths`，源码态/安装态共享同一装配语义。
- GUI 导出路径硬编码：已收口到 `RuntimeFacade.export_root`。
- repository profile 覆盖失真：默认容器路径已停止把仓库级 `app.yaml` / `solver.yaml` 当作 profile 覆盖层。
- export / screenshot 同步阻塞：已切入 `ExportWorker` / `ScreenshotWorker`，统一纳入 `ThreadOrchestrator` 生命周期。
- MainWindow 对象图内联构造：已抽出 `presentation.assembly` 作为 composition root。
- trajectory/playback 缓存边界：已禁止 live playback 在 UI 线程做 FK fallback。
- plugin factory `TypeError` 误吞：已改为签名判定后调用。
- `ThreadOrchestrator` 单文件多职责：已拆分内部职责模块，外部 API 保持不变。
- coordinator 构造 fallback 旁路：已删除 window/controller 猜依赖路径，主链彻底收口到显式注入。
- offscreen / screenshot baseline：已补 `tests/regression/test_scene_capture_snapshot_baseline.py` 与 checked-in baseline fixture，GUI offscreen smoke 也已覆盖 snapshot export。
- render backend telemetry：已细化到 backend latency buckets、duration percentiles、rolling-window rate/throughput、live counters 与 diagnostics timeline，并贯通 diagnostics/export/质量门禁。

## 仍保留的兼容旁路

- `bootstrap()` 现返回 `BootstrapContext`；旧调用方仍可继续解包/索引，但该行为已收口为显式兼容面，主链改为属性访问 `context.project_root / context.container`。
- live render backend 缺失时仍会退化为 placeholder / snapshot renderer，但该行为只存在于 render backend 层；稳定 Qt 构造面本身已不再伪装为可用。

- 分散兼容旁路：现已集中登记到 `docs/compatibility_matrix.md` 与 `robot_sim.app.compatibility_matrix`，主链不再隐式承载兼容清单。

- compatibility shell 现已从 widget/render 类历史面收口到少量核心保留面；主链不再依赖 scene diff/geometry/import 的 metadata 旁路。

- stable scene authority：机器人加载/导入/保存后已统一经 `RobotRuntimeAssetService` 生成 canonical planning scene，routine scene edit 也会保留 runtime robot frame graph，collision 不再依赖 UI 外部手工注入 scene。
- imported geometry consumption：runtime geometry 已进入 stable scene/live render/snapshot/export 链，并可经 registry round-trip 恢复；mesh primitive 仍取决于源文件可恢复性。
- stable scene editor：scene toolbar 已升级为结构化 scene editor（box / sphere / cylinder、attached object、allowed collision pairs），并贯通 scene authority / summary / validation / export。
