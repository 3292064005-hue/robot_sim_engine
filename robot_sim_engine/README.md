# Robot Sim Engine

基于纯数学推导的多自由度机械臂运动学与轨迹规划仿真引擎。

## 当前版本重点

- 统一版本真源：`VersionCatalog` / app / export / session / benchmark pack / 文档口径对齐
- 正式任务生命周期：`TaskState`、`TaskSnapshot`、worker structured events、增强版 `ThreadOrchestrator`
- importer V7：`RobotModelBundle`、importer registry 与 importer 实现拆分、fidelity 明文化
<<<<<<< HEAD
- robot model contract：`RobotSpec` 现已同时承载稳定 DH 运行时面与结构化 joint/link/source-model 摘要
- pose/transform contract：新增 `Pose` / `Transform` 统一校验、组合、逆变换与四元数投影入口
- trajectory 校验拆分为 validators：timing / path metrics / goal / limits / collision
- GUI 协调层：新增 coordinators，开始将 MainWindow 的任务编排逻辑下沉
- render runtime state：`scene_3d / plots / screenshot` 降级原因已统一进入 `SessionState.render_runtime`，并同步投影到状态栏、诊断快照与 session 导出
- render telemetry stream：render 能力状态现在同时沉入 `SessionState.render_telemetry` / `render_operation_spans` / `render_sampling_counters` / `render_backend_performance`，形成状态事件 + operation spans + sampling counters + backend-specific performance telemetry 的细粒度事件流，并进一步输出 backend latency buckets、duration percentiles、rolling-window rate/throughput 与 diagnostics timeline 视图；高频 span/counter 写入现已通过专用 `RenderTelemetryService` + `RenderTelemetryAggregator` 子系统只刷新 render 分段订阅与受影响 backend，避免再次把 render telemetry 扇回 `StateStore` 的全局 selector 热路径。
=======
- trajectory 校验拆分为 validators：timing / path metrics / goal / limits / collision
- GUI 协调层：新增 coordinators，开始将 MainWindow 的任务编排逻辑下沉
>>>>>>> 3ed78e647985c6d680c085e4480d898855278db3

当前交付版本为 **V7 工程硬化版**。在 V3 的可运行基础上，这一版进一步补硬了平台能力：

- 标准 D-H 建模、FK、中间变换缓存、解析几何 Jacobian
- 数值 IK：Pseudo-inverse / DLS / LM / 自适应阻尼 / 加权最小二乘 / position-only / 零空间二级目标
- 解析 IK：新增 `analytic_6r` 球腕 6R 闭式求解插件（当前对 PUMA-like 标准 DH 样机可用）
- IK 稳定性增强：粗工作空间预检查、失败自动多起点重试、结果诊断、solver registry、请求约束适配器流水线
- 请求约束适配器：初值限位修复、目标旋转矩阵正交化、姿态失败时的 position-only 定向降级重试
- 四元数、SO(3) 对数映射、Slerp、五次多项式轨迹规划
- Joint-space、Cartesian-pose、Trapezoidal 插件轨迹与 Waypoint Graph 规划骨架
- `JointTrajectory` 预缓存 FK，并记录 feasibility / quality / collision summary / metadata
<<<<<<< HEAD
- 轻量 collision / planning scene 主链：AABB broad-phase、自碰撞风险、环境碰撞风险、clearance metric 已接入 stable scene surface；当前 stable UI 暴露为结构化 scene editor（box / sphere / cylinder primitive、attached object、allowed collision pairs），但校验真源仍统一收口为 AABB authority；更高保真 scene/backend 能力仍保留到后续版本
- Benchmark：默认 case pack、baseline compare、solver matrix（含解析 6R solver）
- Export：trajectory bundle、metrics、benchmark、session、完整 ZIP package
- Registry / plugin contracts：solver、planner、robot importer
- 导入适配：YAML robot config、结构化 `urdf_model` serial importer 与兼容 `urdf_skeleton` 近似 importer
- PySide6 GUI、Qt worker、Benchmark 面板、Diagnostics 面板、Scene Toolbar、Package Export 入口；稳定 GUI 面在无 Qt 运行时时不再走 production fallback；非 GUI 单元测试只会在测试进程内注入 `robot_sim.testing.qt_shims` 伪 `PySide6` 包
- pytest 单元 / 集成 / benchmark / performance / GUI smoke（PySide6 缺失时自动跳过；pytest 默认注入 `QT_QPA_PLATFORM=offscreen`，显式设置 `ROBOT_SIM_PYTEST_FORCE_GUI_DISPLAY=1` 可改走桌面显示）
=======
- 轻量 collision 预检查：AABB broad-phase、自碰撞风险、环境碰撞风险、clearance metric
- Benchmark：默认 case pack、baseline compare、solver matrix（含解析 6R solver）
- Export：trajectory bundle、metrics、benchmark、session、完整 ZIP package
- Registry / plugin contracts：solver、planner、robot importer
- 导入适配：YAML robot config 与简化 URDF importer
- PySide6 GUI、Qt worker、Benchmark 面板、Diagnostics 面板、Scene Toolbar、Package Export 入口
- pytest 单元 / 集成 / benchmark / performance / GUI smoke（GUI 测试按依赖自动跳过）
>>>>>>> 3ed78e647985c6d680c085e4480d898855278db3
- GitHub Actions CI：执行 `ruff check`、`mypy`（针对核心数学/领域/轨迹模型）以及带 coverage gate 的 `pytest --cov`
- pre-commit：提供 ruff / mypy / pytest 本地提交前门禁
- 当前测试基线：**以 CI / pytest 实际收集结果为准**
- 发布打包：使用 `python scripts/package_release.py --output dist/release.zip --top-level-dir robot_sim_engine` 生成洁净交付包（自动排除缓存/覆盖率/本地工件）

## V7 质量门禁

<<<<<<< HEAD
- quick quality：`ruff check src tests`、targeted `mypy`（以 `pyproject.toml` 的 `tool.mypy.files` 为准）、`python scripts/verify_quality_contracts.py`、`python scripts/verify_runtime_baseline.py --mode headless`、`python scripts/verify_compatibility_budget.py --scenario clean_headless_mainline`、`python scripts/verify_perf_budget_config.py`、`pytest tests/unit tests/regression -q`
- shipped behavior contracts：仓库 profile 必须保持可区分，coordinator 主链必须继续走显式依赖注入，`export` / `screenshot` 主链必须继续走 worker 生命周期，`scene_3d / plots / screenshot` 降级状态必须沉入 `SessionState.render_runtime`，且状态变化、operation spans、sampling counters、backend-specific performance telemetry、latency buckets 与 live counters 必须继续写入共享 render telemetry 真源；clean bootstrap / clean headless mainline 不能越过 compatibility budget，public plugin SDK 示例必须保持可装配，snapshot renderer 与 importer fidelity 两套基线都必须能通过已提交 fixture 复现
- full validation：`pytest --cov=src/robot_sim --cov-report=term-missing --cov-report=json:coverage.json -q`、`python scripts/verify_partition_coverage.py --coverage-json coverage.json`，coverage `fail_under = 80`
- gui smoke：在 **Ubuntu 22.04 + Python 3.10 + PySide6>=6.5** 环境执行 `python scripts/verify_runtime_baseline.py --mode gui`、`pytest tests/gui -q`；pytest 默认注入 `QT_QPA_PLATFORM=offscreen` 以保证无桌面会话时的稳定复现，若需改走真实桌面显示则显式设置 `ROBOT_SIM_PYTEST_FORCE_GUI_DISPLAY=1`，并保留 `tests/regression/test_scene_capture_snapshot_baseline.py` 的 snapshot baseline 回归
=======
- quick quality：`ruff check src tests`、targeted `mypy`、`python scripts/verify_quality_contracts.py`、`pytest tests/unit tests/regression -q`
- full validation：`pytest --cov=src/robot_sim --cov-report=term-missing -q`，coverage `fail_under = 80`
- gui smoke：在 **Ubuntu 22.04 + Python 3.10 + PySide6>=6.5** 环境执行 `pytest tests/gui -q`
>>>>>>> 3ed78e647985c6d680c085e4480d898855278db3
- quality contracts：`docs/quality_gates.md`、`docs/module_status.md`、`docs/capability_matrix.md`、`docs/exception_catch_matrix.md` 必须与运行时服务真源一致
- contract regeneration：执行 `python scripts/regenerate_quality_contracts.py` 后，`docs/` 目录不得产生未提交 diff

## Experimental 模块

以下模块当前明确标记为 experimental，不纳入稳定主链承诺：

<<<<<<< HEAD
- `presentation.experimental.widgets.collision_panel`
- `presentation.experimental.widgets.export_panel`
- `presentation.experimental.widgets.scene_options_panel`
- `render.experimental.picking`
- `render.experimental.plot_sync`
=======
- `presentation.widgets.collision_panel`
- `presentation.widgets.export_panel`
- `presentation.widgets.scene_options_panel`
- `render.picking`
- `render.plot_sync`
>>>>>>> 3ed78e647985c6d680c085e4480d898855278db3

## 运行环境与版本约束

- 操作系统：**Ubuntu 22.04 LTS**（项目计划书中的首选验证环境）
- Python：**3.10+**，CI 与本地建议优先使用 **3.10** 以保持与计划书、类型配置和 GUI 依赖基线一致
- GUI 框架：**PySide6 >= 6.5**
- 3D 渲染：**PyVista >= 0.43**、**pyvistaqt >= 0.11**
- 2D 曲线：**pyqtgraph >= 0.13**

说明：README、`pyproject.toml`、CI 工作流和计划书应保持这一运行基线一致。

## 配置 Profile

- `configs/profiles/default.yaml`：共享默认基线
- `configs/profiles/dev.yaml`：本地开发配置
- `configs/profiles/ci.yaml`：CI 回归配置
- `configs/profiles/gui.yaml`：GUI 运行配置
- `configs/profiles/release.yaml`：发布打包配置
<<<<<<< HEAD
- `trajectory.validation_layers`：按 profile 声明默认轨迹验证层（timing / path_metrics / goal_metrics / collision / limits），调用方仍可按请求显式覆盖

`ConfigService` 默认采用 **代码保底默认值 -> configs/profiles/default.yaml -> 指定 profile -> 可选本地 override** 的合并顺序。仓库内 `configs/app.yaml` 与 `configs/solver.yaml` 现在仅保留为 legacy 兼容占位文件，默认容器路径不会再把它们当作 profile 覆盖层。

可选本地 override 路径如下：

- `configs/local/app.local.yaml`
- `configs/local/solver.local.yaml`
- `ROBOT_SIM_APP_CONFIG_OVERRIDE`
- `ROBOT_SIM_SOLVER_CONFIG_OVERRIDE`

只有在显式设置 `ROBOT_SIM_ENABLE_LEGACY_LOCAL_OVERRIDE=1` 时，仓库级 `app.yaml` / `solver.yaml` 才会重新参与覆盖。`configs/` 是唯一人工维护真源；构建与 CI 会将其 staging 到 `build/packaged_config_staging/robot_sim/resources/configs/`，wheel 打包时再直接安装到 `robot_sim.resources` 包内，不再维护仓库内常驻镜像目录。
运行时路径解析现在保持无副作用：源码态直接读取仓库 `configs/`，安装态优先读取包内资源；源码校验/CI 若已经存在 build 期生成的 staging mirror，可只读复用，但启动期不会再隐式触发 staging 修复。



## License and third-party intake

- repository license: `MIT`
- third-party intake register: `THIRD_PARTY_NOTICES.md`
- source absorption policy: `docs/external_code_intake_policy.md`
=======
- `configs/profiles/research.yaml`：研究/实验能力开启配置（允许 experimental backend / plugin discovery）

`ConfigService` 采用 **代码默认值 -> default profile -> 指定 profile -> 本地 app.yaml / solver.yaml** 的合并顺序，避免环境口径再次漂移。

>>>>>>> 3ed78e647985c6d680c085e4480d898855278db3

## Runtime Feature Policy

- 默认 / GUI / CI / release profile 均关闭 experimental 模块运行时启用、experimental backend 宣告与外部 plugin discovery
- `research.yaml` 显式开启：
  - `experimental_modules_enabled`
  - `experimental_backends_enabled`
  - `plugin_discovery_enabled`
<<<<<<< HEAD
- 外部插件必须先在 `configs/plugins.yaml` 中白名单声明，且满足 `api_version: v1` 才允许被受控装配层接入；shipped plugin 允许在关闭外部 discovery 的 profile 下继续通过 allowlist 装配。仓库现内置三个仅在 `research` profile 启用的 shipped demo plugins（solver / planner / importer），用于持续验证三条插件主链
- repo 级广义异常捕获边界由 `docs/exception_catch_matrix.md` 与 `python scripts/verify_quality_contracts.py` 共同约束
- perf 预算除配置校验外，CI 还会显式执行 `tests/performance/test_ik_smoke.py` 进行 smoke 门禁
=======
- 外部插件必须先在 `configs/plugins.yaml` 中白名单声明，才允许被受控装配层接入
- repo 级广义异常捕获边界由 `docs/exception_catch_matrix.md` 与 `python scripts/verify_quality_contracts.py` 共同约束
>>>>>>> 3ed78e647985c6d680c085e4480d898855278db3

## 快速开始

```bash
pip install -e .[dev]
python scripts/run_tests.py
python -m pytest -q
<<<<<<< HEAD
python scripts/verify_runtime_baseline.py --mode headless
python -m build
```

源码态现在统一要求通过 **editable install** 或显式 `PYTHONPATH=src` 运行；仓库根目录不再保留隐式 `robot_sim` 包 shim。

=======
```

>>>>>>> 3ed78e647985c6d680c085e4480d898855278db3
安装 GUI 依赖后可运行图形界面：

```bash
pip install -e .[gui,dev]
python -m robot_sim.app.main
```

## 目录

```text
src/robot_sim/
  app/            启动、版本、依赖装配
  domain/         能力描述、错误、plugin 契约
  model/          FK / IK / trajectory / benchmark / export manifest 等数据模型
  core/           纯数学核心、trajectory / collision 子系统
  application/    DTO、registry、use case、service、worker
  presentation/   Qt 主窗体、controller、线程编排、widget
  render/         3D / 2D 渲染、截图、plot sync
  infra/          配置、日志、schema、文件
```

## 当前可直接演示的链路

- 加载样例机器人
- 编辑 DH / home q 并保存 YAML
- 执行 FK / IK
- 生成关节空间轨迹、笛卡尔位姿轨迹、Trapezoidal 轨迹
- 轨迹播放、曲线游标同步、3D 机械臂联动
- 运行 benchmark，并导出 JSON / CSV / ZIP package
<<<<<<< HEAD
- 导入 YAML / 简化 URDF 机器人配置（导入后自动落库并载入 stable 主链；运行时执行面统一收口到 canonical execution rows）
=======
- 导入简化 URDF 机器人配置
>>>>>>> 3ed78e647985c6d680c085e4480d898855278db3
- 导出 trajectory bundle、trajectory metrics、benchmark report、session、完整实验包

## 工程约束

- `core/` 不依赖 Qt
<<<<<<< HEAD
- GUI 中的 IK / trajectory / benchmark / playback / export / screenshot 都必须走 worker
=======
- GUI 中的 IK / trajectory / benchmark / playback 都必须走 worker
>>>>>>> 3ed78e647985c6d680c085e4480d898855278db3
- 3D 视图尽量走 actor 持久更新而不是全量 `clear()`
- 新增 solver / planner / importer 必须通过 registry 接入
- 轨迹对象必须能被日志、诊断和导出解释，不能只靠动画展示


## Runtime resource and export resolution

- 启动装配链现在通过 `robot_sim.app.runtime_paths.resolve_runtime_paths()` 统一解析运行时路径，而不是要求所有调用方自行拼接 repo 根目录。
<<<<<<< HEAD
- `bootstrap()` 现在返回 `BootstrapContext`，主链通过 `context.project_root / context.container` 访问；旧式解包与索引仍保留为显式兼容面。`build_container()` 与运行时容器内部仍显式区分：`project_root`、`resource_root`、`config_root`、`robot_root`、`plugin_manifest_path`、`export_root`，并输出 `layout_mode` 与 `config_resolution` 诊断摘要。
- GUI 截图、导出服务、package export 统一写入 `export_root`。导出与截图主链现在都通过 `ThreadOrchestrator` 进入统一任务生命周期；可通过环境变量 `ROBOT_SIM_EXPORT_DIR` 覆盖默认导出目录。安装态默认写入用户数据目录（优先 `XDG_DATA_HOME/robot-sim-engine/exports`，否则回退 `~/.local/share/robot-sim-engine/exports`），仅在显式设置 `ROBOT_SIM_EXPORT_POLICY=legacy_cwd` 时才回退到当前工作目录。
- wheel / 安装态运行优先使用包内 `robot_sim.resources.configs` 资源；源码态运行继续优先使用仓库 `configs/`。安装态下 `bundled_robot_root` 保持只读，stable 机器人导入/保存统一写入用户目录 `robot_root`（优先 `XDG_DATA_HOME/robot-sim-engine/robots`，否则回退 `~/.local/share/robot-sim-engine/robots`），并通过 registry overlay 同时暴露内置机器人与用户导入机器人。
- MainWindow 已移除重复的私有 `*_impl` 实现路径；主窗口对象图现在通过 `presentation.assembly.build_presentation_assembly()` 统一构建。主窗口依赖现已先收敛到 `RuntimeServiceBundle` / `WorkflowFacadeBundle` / `TaskOrchestrationBundle` 三个稳定 bundle，并通过 `WindowRuntime` 的只读兼容属性暴露给现有 mixin / 测试 / 少量仓库外自动化脚本。`MainController` 则进一步退化为对 `PresentationBootstrapBundle` 的兼容壳：对象图装配被归并到 typed bootstrap bundle + grouped collaborator 构建函数中，而不是继续在控制器内部直接拉取整个容器表面。
- `presentation.main_window_feature_builders` 现已承载 left / center / right / layout / signal wiring 的 feature builders；`MainWindowUIMixin` 保留兼容方法表面，但 widget 组装职责已从 UI 壳中剥离。
- 仓库根目录的 `robot_sim` 包 shim 已移除；源码态运行必须走 `src` 布局真源，不再允许根目录隐式导入绕过打包/安装边界。
- `StateStore` 现已内聚为兼容 façade + `session_store` / `task_store` / `render_store` 三段子 store；其中 render 子链进一步下沉到 `RenderTelemetryService`，并新增 segment-local subscriber registry。现有 `patch_*` / `record_render_*` / `subscribe_render_*` 接口保持不变，但 render telemetry 变更默认只刷新 render 分段订阅与全局兼容订阅，不再把所有 selector 一并拖入热路径。
- 视图契约已从单体 `MainWindowLike` 拆为 `MainWindowActionView`、`MainWindowTaskView`、`MainWindowUIContract` 三层，避免任务/动作 mixin 再依赖整个主窗体表面。
=======
- `bootstrap()` 与 `build_container()` 仍保持原有外部调用方式兼容，但容器内部已显式区分：`project_root`、`resource_root`、`config_root`、`robot_root`、`plugin_manifest_path`、`export_root`。
- GUI 截图、导出服务、package export 统一写入 `export_root`。可通过环境变量 `ROBOT_SIM_EXPORT_DIR` 覆盖默认导出目录。
- wheel / 安装态运行优先使用包内 `robot_sim.resources.configs` 资源；源码态运行继续优先使用仓库 `configs/`。
>>>>>>> 3ed78e647985c6d680c085e4480d898855278db3

## Playback cache contract

- `JointTrajectory` 现在会依据真实缓存数组状态规范化 `cache_status`，不再把 metadata 声明无条件视为真。
- live playback 主链要求轨迹满足 `trajectory.is_playback_ready`；GUI 不再在播放帧应用时做 UI 线程 FK fallback。
- 当轨迹已生成但缓存未就绪时，界面会明确提示缓存状态，而不是静默同步重算整条轨迹。
<<<<<<< HEAD

- render runtime / telemetry projection 现已支持显式 segment 订阅：diagnostics render telemetry 通过 `segment="render"` 绑定到 render 分段，而全局状态订阅仍保留给兼容路径与跨段 UI 投影。
- compatibility matrix：显式保留的兼容旁路现在集中登记在 `docs/compatibility_matrix.md` 与 `robot_sim.app.compatibility_matrix.COMPATIBILITY_MATRIX`（代码中为 `COMPATIBILITY_MATRIX`）中，便于版本化清退；运行期使用会通过 `robot_sim.infra.compatibility_usage.record_compatibility_usage(...)` 进行去重日志与计数。
- render telemetry now flows through bounded structured streams (`StateStore.patch_render_runtime(...) -> RenderTelemetryEvent`, `StateStore.record_render_operation_span(...)`, `StateStore.record_render_sampling_counter(...)`) and backend performance aggregates, all projected into DiagnosticsPanel / diagnostics snapshot / session export; batched screenshot telemetry flushes now use `StateStore.notify_render()` instead of global notify fan-out.
- render selector subscriptions now keep the historical defensive `deepcopy` default, but render-only telemetry/projection paths explicitly use immutable `identity` snapshots so high-frequency telemetry flushes no longer pay unnecessary deep-copy cost on the hot path.


## Local validation shortcuts

- `nox -s quick_quality`：本地 headless 质量门禁
- `nox -s gui_smoke`：安装 GUI 依赖后的轻量界面冒烟

- importer fidelity baseline：`tests/regression/baselines/importer_fidelity_baseline.json` 由 `python scripts/regenerate_importer_fidelity_baseline.py` 维护，用于锁定 native YAML 与 structured URDF 导入摘要。
=======
>>>>>>> 3ed78e647985c6d680c085e4480d898855278db3
