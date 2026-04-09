# Plugin Development

## IK solver plugin

新 solver 应实现：

- `solve(spec, target, q0, config, *, cancel_flag=None, progress_cb=None, attempt_idx=0)`

并通过 `solver_registry.register('<solver_id>', solver)` 接入。

## Trajectory planner plugin

新 planner 应实现：

- `plan(req)`

并通过 `planner_registry.register('<planner_id>', planner)` 接入。

## Robot importer plugin

新 importer 应实现：

- `load(source, **kwargs)`

并通过 `importer_registry.register('<importer_id>', importer)` 接入。

## Rule

不要把新能力直接写进主窗体或总控制器。先定义 contract，再通过 registry 装配。


## P1 additions

- IK solvers now include `lm` (Levenberg–Marquardt).
- Trajectory validation can consume a lightweight `PlanningScene` with ACM filtering.


## Factory invocation contract

- 通过装配层工厂注册的插件工厂现在在调用前进行签名判定：
  - 若签名可接受上下文字段，则以 `factory(**context)` 调用。
  - 若签名不接受上下文且无必需参数，则以 `factory()` 调用。
- 工厂内部抛出的 `TypeError` 不再被解释为“签名不兼容”；这类错误会按真实执行失败向上抛出。
- 不建议依赖模糊签名或可变位置参数来兼容不同装配环境，推荐显式声明所需上下文字段或使用无参工厂。

## Public SDK examples

- `examples/plugins/minimal_solver_plugin.py` 展示最小 solver plugin 工厂。
- `examples/plugins/minimal_importer_plugin.py` 展示最小 importer plugin 工厂。
- 这两个样板都受 `tests/unit/test_plugin_sdk_examples.py` 约束，保证文档示例不是失效伪代码。

## Packaging notes

- 外部插件推荐通过 `configs/plugins.yaml` 白名单声明后，再由 `PluginLoader` 受控装配；manifest 需显式声明 `api_version: v1`，并建议同时声明 `sdk_contract_version: v1` 与 `min_host_version`。
- manifest 现在要求显式 `status`，允许值为 `stable / beta / experimental / internal / deprecated`。
- profile 通过 `features.plugin_status_allowlist` 控制可装配插件等级：
  - `default / gui / release / ci`: `stable`, `deprecated`
  - `dev`: `stable`, `beta`, `deprecated`
  - `research`: `stable`, `beta`, `experimental`, `internal`, `deprecated`
- capability matrix 会把 plugin status 投影到 UI/runtime diagnostics，不再把所有插件都伪装成 stable。
- 示例工厂同时兼容直接 `factory:` 引用与 entry-point 包装载荷。


## Repository-shipped fixtures

- `configs/plugins.yaml` 现在内置 `research_demo_dls`、`research_demo_cartesian_planner`、`research_demo_yaml_importer` 三个 shipped fixtures。
- 三者都只在 `research` profile 启用，用来持续验证 solver / planner / importer 三条插件装配链。
- shipped plugin 在 `plugin_discovery_enabled=false` 时仍允许通过 allowlist 装配；外部 plugin 仍必须显式开启 discovery。

## SDK governance

- `sdk_contract_version` 表示插件遵循的宿主 SDK 契约版本；当前仅支持 `v1`。
- `min_host_version` 表示插件要求的最小宿主版本；当前不仅会进入 audit / diagnostics / registration metadata，还会在 `PluginLoader` 决策阶段阻止低于 `min_host_version` 的宿主继续加载该插件。

## Host capability negotiation

- manifest 现在可选声明 `required_host_capabilities` 与 `optional_host_capabilities`。
- `required_host_capabilities` 中任一 capability 缺失时，`PluginLoader` 会在 audit 阶段直接拒载，并返回 `required_host_capability_missing`。
- 宿主 capability 由 profile、experimental feature switch、允许的 plugin status 等 runtime feature 组合生成，当前会投影到 runtime diagnostics。
