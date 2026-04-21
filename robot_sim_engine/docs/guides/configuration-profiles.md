---
owner: docs
audience: contributor
status: canonical
source_of_truth: manual
last_reviewed: 2026-04-17
---
# Configuration Profiles

## 合并顺序

`ConfigService` 默认采用：

1. 代码保底默认值（typed dataclass defaults，单真源）
2. `configs/profiles/default.yaml`（默认应保持最小 override diff；当前主干为空 profile）
3. 指定 profile
4. 可选本地 override

仓库级 `configs/app.yaml` 与 `configs/solver.yaml` 现在仅保留为非运行时兼容壳文件，不再作为 profile 覆盖层。

## 内置 profile

- `default`：共享默认基线
- `dev`：本地开发
- `ci`：CI 回归
- `gui`：GUI 运行
- `release`：发布打包
- `research`：研究/实验能力面

## 本地 override

可选本地 override 路径：

- `configs/local/app.local.yaml`
- `configs/local/solver.local.yaml`
- `ROBOT_SIM_APP_CONFIG_OVERRIDE`
- `ROBOT_SIM_SOLVER_CONFIG_OVERRIDE`

## Runtime feature policy

默认 / GUI / CI / release profile：

- 关闭 experimental modules
- 关闭 experimental backends
- 关闭 plugin discovery

`research.yaml` 显式开启：

- `experimental_modules_enabled`
- `experimental_backends_enabled`
- `plugin_discovery_enabled`

## 配置真源与打包

- `configs/` 是人工维护真源
- build / CI 会 staging 到 `build/packaged_config_staging/robot_sim/resources/configs/`
- wheel 打包时安装到 `robot_sim.resources`
- 启动期不会再隐式触发 staging 修复

## Default profile hygiene

- `configs/profiles/default.yaml` 不再重复抄写代码默认值。
- 只有当仓库必须显式覆盖 typed defaults 时，才允许在 default profile 中保留字段。
- profile 差异审查应以 `typed_code_defaults -> profiles/default.yaml -> active profile -> local override` 为准，不再把默认 profile 视为另一份人工维护真源。
