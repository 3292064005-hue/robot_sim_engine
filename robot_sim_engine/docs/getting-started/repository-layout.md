---
owner: docs
audience: contributor
status: canonical
source_of_truth: manual
last_reviewed: 2026-04-18
---
# Repository Layout

## 顶层目录

- `src/robot_sim/`：主代码
- `tests/`：单元 / 回归 / GUI / 集成 / 性能测试
- `configs/`：配置真源
- `docs/`：分层说明文档
- `scripts/`：验证、打包、生成脚本
- `examples/`：插件与示例代码

## 配置真源

当前关键配置包括：

- `configs/profiles/*.yaml`
- `configs/plugins.yaml`
- `configs/compatibility_budget.yaml`
- `configs/compatibility_retirement.yaml`
- `configs/perf_budgets.yaml`
- `configs/benchmark_matrix.yaml`
- `configs/release_environment.yaml`
- `configs/collision_fidelity.yaml`

其中 `configs/collision_fidelity.yaml` 是 planning-scene / validation backend fidelity roadmap 的外置真源；源码态、staging 态与 packaged resource 态都应解析同一语义配置。

## 文档与生成物

- canonical docs：`docs/architecture/`, `docs/guides/`, `docs/reference/`, `docs/governance/`
- generated docs：`docs/generated/*.md`
- legacy entry pages：根目录 `docs/*.md` 同名入口页

## 常用脚本

- `python scripts/regenerate_quality_contracts.py`
- `python scripts/verify_quality_contracts.py`
- `python scripts/verify_docs_information_architecture.py`
- `python scripts/verify_runtime_contracts.py --mode headless --check-packaged-configs`
