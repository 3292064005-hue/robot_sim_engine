# Architecture

## Layers

- `model`: FK / IK / trajectory / benchmark / export manifest 等不可变结果对象。
- `core`: 纯数学内核，不依赖 Qt。
- `application`: DTO、registry、use case、service、worker，是业务编排中间层。
- `presentation`: 主窗体、线程编排器、分层 controller、workflow service、widget。
- `render`: PyVista / pyqtgraph 适配层、截图、plot sync。render capability 降级原因统一投影到 `SessionState.render_runtime`，再通过 typed status-panel subscription flow 下发到 UI；render 状态变化会进一步生成 `SessionState.render_telemetry`，同时 UI runtime probe / screenshot capture 会写入 `render_operation_spans` / `render_sampling_counters` 并汇总为 `render_backend_performance`。这条链现在由 `presentation.render_telemetry_service.RenderTelemetryService` 统一持有，再通过兼容 `StateStore` / `RenderStateSegmentStore` 接口投影给 diagnostics / export / 质量门禁消费。
- `infra`: 配置、日志、文件、schema。
- `domain.quality_gate_catalog` 现承载跨层共享的 quality-gate 定义；governance / benchmark 读取 catalog 时不再通过 `infra` 反向回灌到领域层。
- `model.robot_geometry_serialization` 现承载 `RobotGeometry` 的持久化协议；`RobotGeometryModel` 与 registry/export round-trip 不再依赖 application service 侧 helper。

## Registry / Plugin entry

V4 开始，以下能力通过 registry 接入：

- `solver_registry`: IK solver
- `planner_registry`: trajectory planner
- `importer_registry`: robot importer

插件 manifest / SDK 现在受三层约束：

- `src/robot_sim/plugin_sdk/plugin_payload(...)` 是公共 SDK payload builder，仓库示例与 shipped plugin 都通过同一 helper 暴露 manifest-compatible payload


- `kind / source / api_version / sdk_contract_version / status` 必须通过 `PluginLoader` 静态校验，并把 `min_host_version` 一并投影到 audit / diagnostics
- profile 通过 `features.plugin_status_allowlist` 决定允许装配的 plugin rollout 等级
- `plugin_discovery_enabled=false` 时，仅允许 `builtin / shipped_plugin` 来源继续装配

后续新增 6R 解析 IK、冗余约束求解、URDF importer、collision adapter 时，不应再直接修改主控制器或主窗口。插件 loader 现在除版本校验外，还会对 `required_host_capabilities / optional_host_capabilities` 做宿主能力协商；研究型 shipped plugin 通过 `features.plugin_status_allowlist` 与 host-capability 协商共同决定是否可加载。

## Presentation split

当前 GUI 编排拆成：

- `RobotController`: 机器人加载、保存、FK、采样
- `IKController`: 目标位姿构造、IK request 构造、结果回写
- `TrajectoryController`: joint/cartesian 轨迹 request 构造与应用
- `PlaybackController`: 播放索引、帧切换、倍率和循环控制
- `BenchmarkController`: benchmark config 构造与批量运行
- `ExportController`: trajectory / benchmark / metrics / session / package 导出
- `DiagnosticsController`: 当前会话诊断快照

## Threading rules

1. `core` 不能导入 Qt。
2. IK / trajectory / benchmark / playback / export / screenshot 都优先走 worker。
3. GUI 线程只做参数收集、状态更新和渲染调用。
4. 取消与停止必须通过统一线程编排器传播。

## Data rules

1. 轨迹对象必须携带 `metadata / feasibility / quality`。
2. Playback 优先使用预缓存 FK 结果，而不是每帧在 UI 线程重算。
3. Euler angles 只允许出现在 UI 输入层，IK 核心使用旋转矩阵 / rotation vector / quaternion。
4. 导出对象必须版本化并能被离线分析脚本复用。
5. `scene_3d / plots / screenshot` 的 runtime capability 必须进入统一状态存储，而不是只停留在 placeholder 或日志层。
6. `RobotSpec` 运行时执行语义现统一收口到 `ArticulatedRobotModel` + `RuntimeRobotModel.execution_summary`：FK/Jacobian/数值 IK 消费 articulated transforms，legacy DH execution rows 仅作为兼容 adapter / analytic solver surface。
7. importer/registry/runtime asset/export 现在必须优先处理 `ImportedRobotPackage`：source model、runtime model、articulated model 与 visual/collision geometry 被拆成平级对象，而不是继续把所有运行时语义塞回一份 YAML metadata。
8. scene object 摘要现同时暴露 `declaration_geometry` / `validation_geometry` / `render_geometry`；稳定产品面禁止只暴露解析后 AABB 而丢失声明或渲染几何语义，同时保留 `declared_geometry` / `resolved_geometry` 兼容别名。
9. `planning_scene.summary()` 现在必须同时携带 `geometry_authority` 与 `scene_graph_authority`；scene edit 不允许丢失运行时机器人 frame graph；`render_runtime.screenshot` 则必须同时暴露 `level / provenance`，禁止把 live capture 与 snapshot fallback 伪装成同一种能力。


## Runtime path model

- `bootstrap()` / `build_container()` 使用 `RuntimePaths` 作为统一运行时路径真源。
- `project_root` 只表示源码工程根或兼容根语义；资源读取、插件清单读取、机器人配置读取、导出目录写入必须走显式路径字段。
- GUI / controller / facade 不允许再直接硬编码 `project_root / "exports"` 或 `project_root / "configs"`；安装态默认导出目录必须与当前工作目录解耦。

## Coordinator dependency rule

- presentation object graph 现在由 `presentation.assembly.PresentationAssembly` 统一构建，`MainWindow` 不再内联 new controller / orchestrator / coordinator；主窗口依赖被收口为 runtime services / workflow façades / task orchestration 三类 bundle。
- coordinator 主路径通过显式注入获取 facade、metrics service、thread orchestrator 与 view contract。
- coordinator 构造不再允许从 window/controller 猜 facade/threader；测试与生产都必须显式提供依赖。
- `project_playback_stopped()` 与 `project_trajectory_result()` 已移除通过 action 回流触发 seek 的主路径。

## Stable capture path

- screenshot 主链现在经 `application.use_cases.capture_scene.CaptureSceneUseCase` 收口。
- `SceneCoordinator` 只负责 worker 编排、UI 投影与 telemetry 归档；不再直接承担底层截图 service 语义。


9. benchmark / release 治理不再只靠文档约定：`configs/benchmark_matrix.yaml` 与 `configs/release_environment.yaml` 已成为 checked-in contract，分别由 `verify_benchmark_matrix.py` 与 `verify_release_environment.py` 负责执行校验。

## Quality evidence

- benchmark / governance / runtime baseline / performance smoke 的执行结果现在可以通过 `scripts/collect_quality_evidence.py` 汇总为 `artifacts/quality_evidence.json`。
- `docs/quality_gates.md` 保留静态契约说明，`docs/quality_evidence.md` 明确区分“checked-in contract docs”与“最近一次执行证据 artifact”。
- release / CI 审计不应再仅凭文档说明判断闭环，必须结合 evidence artifact 与相应 gate 输出。
