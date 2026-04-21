---
owner: docs
audience: newcomer
status: canonical
source_of_truth: manual
last_reviewed: 2026-04-17
---
# Quickstart

## 适用对象

- 第一次拉起项目的人
- 需要确认源码态 / 安装态如何运行的人
- 需要快速跑一轮最小验证的人

## 安装

```bash
pip install -e .[dev]
```

可选：若要运行 GUI 或 3D/2D 渲染链，请确保环境具备：

- `PySide6 >= 6.5`
- `PyVista >= 0.43`
- `pyvistaqt >= 0.11`
- `pyqtgraph >= 0.13`

## 运行入口

源码态：

```bash
python robot_sim_cli.py source-layout-smoke
python robot_sim_cli.py gui
```

安装态：

```bash
robot-sim
robot-sim-gui
```

说明：源码态和安装态共享同一运行真源 `src/robot_sim`。仓库根目录不再保留 `robot_sim` 包 shim。

## 最小验证链

```bash
python scripts/run_tests.py
python -m pytest -q
python scripts/verify_runtime_baseline.py --mode headless
python scripts/verify_runtime_contracts.py --mode headless --check-packaged-configs
python scripts/verify_compatibility_budget.py --scenario clean_headless_mainline
```

## 常用 profile

- `default`：共享默认基线
- `dev`：本地开发
- `ci`：回归与门禁
- `gui`：GUI 运行
- `release`：打包发布
- `research`：研究/实验能力面

具体说明见 `docs/guides/configuration-profiles.md`。

## 下一步建议

- 想看系统怎么组织：读 `docs/architecture/overview.md`
- 想理解任务与线程编排：读 `docs/architecture/execution-model.md`
- 想理解 scene / collision 主线：读 `docs/architecture/planning-scene.md`
- 想开发插件：读 `docs/guides/plugin-development.md`
- 想做验证与打包：读 `docs/guides/testing-and-quality.md` 与 `docs/guides/packaging-and-release.md`
