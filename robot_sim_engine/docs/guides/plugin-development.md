---
owner: docs
audience: contributor
status: canonical
source_of_truth: manual
last_reviewed: 2026-04-18
---
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
- `examples/plugins/minimal_planner_plugin.py` 展示最小 planner plugin 工厂。
- 三个样板都通过 `robot_sim.plugin_sdk.plugin_payload(...)` 生成稳定 payload，并受 `tests/unit/test_plugin_sdk_examples.py` 约束，保证文档示例不是失效伪代码。

## Packaging notes

- 外部插件推荐通过共享清单 `configs/plugins.yaml` 白名单声明后，再由 `PluginLoader` 受控装配；profile 专属 shipped plugin 建议放到 `configs/profiles/<profile>.plugins.yaml`。manifest 需显式声明 `api_version: v1`，并建议同时声明 `sdk_contract_version: v1` 与 `min_host_version`。当前保留的正式 kind 为 `solver / planner / importer / scene_backend / collision_backend`。
- manifest 现在要求显式 `status`，允许值为 `stable / beta / experimental / internal / deprecated`。
- profile 通过 `features.plugin_status_allowlist` 控制可装配插件等级：
  - `default / gui / release / ci`: `stable`, `deprecated`
  - `dev`: `stable`, `beta`, `deprecated`
  - `research`: `stable`, `beta`, `experimental`, `internal`, `deprecated`
- capability matrix 会把 plugin status 投影到 UI/runtime diagnostics，不再把所有插件都伪装成 stable。
- 示例工厂同时兼容直接 `factory:` 引用与 entry-point 包装载荷。


## Repository-shipped fixtures

- `configs/plugins.yaml` 现在承载 stable/default shipped plugin 主干清单；除 solver / planner / importer 外，还保留 `scene_backend` 与 `collision_backend` 两个正式预留 kind 的 stable shipped fixtures。
- `research_dls_solver`、`research_cartesian_planner`、`research_yaml_importer` 仍只在 `configs/profiles/research.plugins.yaml` 启用，用来持续验证 research profile 的扩展链。

兼容 alias-only shipped plugin：
- 当 shipped plugin 只是稳定兼容入口，而实现真源仍是 builtin canonical capability 时，manifest 可声明 `metadata.canonical_target`。
- 这类 plugin 仍会保留自己的 `plugin_id` 和 profile / policy / audit surface，但 registry 内只注册 alias，不再复制第二份实现真源。
- `metadata.canonical_target` 只应用于 alias-only surface；若要引入新的真实实现，必须提供独立 factory/instance、质量门禁与治理登记，不能借 alias 名义复制另一套 runtime 真源。
- shipped plugin 在 `plugin_discovery_enabled=false` 时仍允许通过 allowlist 装配；外部 plugin 仍必须显式开启 discovery。

## SDK governance

- `sdk_contract_version` 表示插件遵循的宿主 SDK 契约版本；当前仅支持 `v1`。
- `min_host_version` 表示插件要求的最小宿主版本；当前不仅会进入 audit / diagnostics / registration metadata，还会在 `PluginLoader` 决策阶段阻止低于 `min_host_version` 的宿主继续加载该插件。

## Host capability negotiation

- manifest 现在可选声明 `required_host_capabilities` 与 `optional_host_capabilities`。
- `required_host_capabilities` 中任一 capability 缺失时，`PluginLoader` 会在 audit 阶段直接拒载，并返回 `required_host_capability_missing`。
- 宿主 capability 由 profile、experimental feature switch、允许的 plugin status 等 runtime feature 组合生成，当前会投影到 runtime diagnostics。


## Entry-point packaging

- `PluginLoader` 仍支持 `entry_point: <group>:<name>` 的受控装配路径，供外部插件或安装态插件使用。
- 仓库内 research demo plugins 不再通过 `pyproject.toml` 暴露 repository 级 `robot_sim.plugins` entry points；它们只通过 `configs/profiles/research.plugins.yaml` 的 shipped-plugin manifest 进入 research profile，避免污染 stable/default 主干心智模型。


## Deployment tiers

- `deployment_tier: production`：默认 profile 会直接挂载的 shipped plugin。
- `deployment_tier: experimental`：仅在 research/实验 profile 暴露的 shipped plugin。
- `deployment_tier: fixture`：仅用于 contract/loader smoke 的 fixture surface，不应作为主叙事能力面。
- `deployment_tier: compatibility`：仅用于未来经审计批准的过渡适配面；当前 shipped mainline 不保留此类 surface。


## Plugin marketplace summary

运行时 capability matrix 现额外投影 `plugin_marketplace`，按 kind 聚合：

- `declared_plugin_ids`
- `enabled_plugin_ids`
- `production_plugin_ids`
- `experimental_plugin_ids`
- `status_counts`
- `deployment_tier_counts`

该 summary 不是新的装配入口，而是主链诊断与治理面：用于回答“某类插件是否真的被 runtime 消费”“实验插件是否只停留在 manifest 暴露层”。

贡献新 plugin 时，除单插件 metadata 外，应确认它会正确进入对应 marketplace kind；否则往往意味着只注册了插件描述，却没有进入实际 capability consumption surface。

## Governance vs runtime providers

- Plugin governance surface 与 runtime provider surface 现已显式分离。
- registry 只消费 capability providers；仅用于兼容/治理的 alias-only manifest 会留在 audit/catalog 中，不再伪装成一份真实 runtime provider。
- 当 manifest 声明 `metadata.canonical_target` 时，主链只建立 compatibility alias，不会复制第二份 provider identity。
- 诊断/导出面会同时保留 governance registrations 与 capability registrations，便于区分“被治理声明过”和“真的进入运行时能力面”的差异。

## Trajectory stage providers

- `trajectory.stage_catalog` 已升级为受治理的 stage-provider surface。
- stage provider 可声明 `provider_id`、`enabled_profiles`、`status`、`deployment_tier`、`required_host_capabilities`、`optional_host_capabilities`、`fallback_stage_id` 与 `replace`。
- pipeline registry 会按 active profile / plugin status allowlist / host capabilities 决策 stage 是否可用，并把 resolution/fallback 结果写入 pipeline metadata。
