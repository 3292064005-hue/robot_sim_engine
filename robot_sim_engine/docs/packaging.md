# Packaging

## Local development

```bash
pip install -e .[dev]
```

## GUI development

```bash
pip install -e .[gui,dev]
```

## Package export

应用层支持一键导出 ZIP package，内含：

- trajectory bundle
- benchmark report
- benchmark cases csv
- session json
- manifest.json

后续如需 wheel / desktop bundle，可在现有 `PackageService` 基础上继续扩展。


## Installed runtime contract

- `configs/` 是唯一人工维护的配置真源。
- `build/packaged_config_staging/robot_sim/resources/configs/**` 是构建/CI 验证时使用的 staging 镜像，不再维护仓库内常驻 `src/robot_sim/resources/configs/**` 镜像目录。
- 构建阶段通过 `robot_sim.infra.packaged_config_sync.install_packaged_configs(...)` 将 `configs/` 直接复制到 `build_lib/robot_sim/resources/configs/**`，从而进入 wheel / sdist 产物。
- 安装态启动优先读取包内资源；源码态读取仓库 `configs/`，两者共享同一份源配置。除 `robots/` 外，其余配置保持只读资源语义。
- 安装态下 `robot_root` 不再指向 `site-packages` 内部资源目录，而是落到用户数据目录（优先 `XDG_DATA_HOME/robot-sim-engine/robots`，否则回退 `~/.local/share/robot-sim-engine/robots`）；`bundled_robot_root` 继续指向包内只读机器人资源，并由 `RobotRegistry` 以 overlay 方式联合暴露。
- `resolve_runtime_paths()` 只做发现，不再在启动期调用 staging/sync 逻辑；安装态优先读取包内资源，源码校验/CI 可只读复用已生成的 staging mirror；若两者都缺失，启动会显式失败并返回稳定错误码。
- CI 快速门禁验证 staging 是否可由单一真源生成；release validation 通过真实 wheel 重装 + `bootstrap()` / `build_container()` 烟测验证产物内资源完整性。
- CI `release_validation` 已增加 wheel 安装后的真实 `bootstrap()` / `build_container()` 烟测，以及安装态机器人导入/保存 overlay smoke，而不是仅做 import 验证。


## Release environment contract

- `configs/release_environment.yaml` 是发布环境真源，显式约束 `release` 与 `gui` 验证环境。
- `python scripts/verify_release_environment.py --mode release` 会校验发布构建环境是否对齐 `Ubuntu 22.04 + Python 3.10 + build tooling`。
- `python scripts/verify_release_environment.py --mode gui` 会校验 GUI 烟测环境是否对齐 `Ubuntu 22.04 + Python 3.10 + PySide6>=6.5`。
- 发布结论必须区分：`headless 验证通过`、`GUI 验证通过`、`release 环境契约通过`，禁止把其中任一项夸大成整体可交付。
