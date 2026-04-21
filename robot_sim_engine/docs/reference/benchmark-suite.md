---
owner: quality
audience: maintainer
status: canonical
source_of_truth: manual
last_reviewed: 2026-04-17
---
# Benchmark Suite

每台样例机器人默认包含以下 case 类型：

- `home_pose`
- `mid_pose`
- `orientation_shifted`
- `position_only_hard`
- `near_limit_pose`
- `near_singular_pose`
- `unreachable_far`

## 输出指标

- `success_rate`
- `p50_elapsed_ms`
- `p95_elapsed_ms`
- `mean_final_pos_err`
- `mean_final_ori_err`
- `mean_restarts_used`
- `stop_reason_histogram`
- `comparison`（与 baseline 的差异）
- report metadata：`execution_graph`（canonical）/ `execution_scope`（compat alias）

## 用途

- 验证 solver 改动是否退化
- 对比不同 IK 参数组合
- 形成答辩或展示用的量化报告
- 作为回归治理工具，而不是只做展示

## 预算门禁

- 仓库真源：`configs/perf_budgets.yaml`（IK smoke 预算现已采用 warmup + measured samples + median/p95/max-single 统计门禁，而不是单次 elapsed 断言）
- CI profile 预算必须至少覆盖 `ik_planar_smoke`、`ik_planar_default_suite`、`trajectory_plan_smoke`、`render_snapshot_capture`
- `quick_quality` CI 主链现在显式执行 `tests/performance/test_ik_smoke.py`，不再只检查 perf 配置文件本身
- benchmark / performance 测试不再只验证字段存在，还必须通过预算校验


## 验证矩阵真源

- 仓库真源：`configs/benchmark_matrix.yaml`
- 结构校验：`python scripts/verify_benchmark_matrix.py --execute`
- 该矩阵明确约束 `runtime_surface × importer_variant × scene_variant × solver_suite × capture_mode` 的最小覆盖对，不允许 benchmark 只剩单一 happy path。

- `required_pairs` 现在必须声明 `execution_targets`，并由 `verify_benchmark_matrix.py --execute` 通过 `BenchmarkExecutionHarness` 实际执行对应 runtime case；矩阵不再只是 YAML 自洽校验，也不再退化为 test selector 间接层，矩阵执行目标只允许 runtime case。

## Harness 分层

- `BenchmarkService` 继续负责 IK case 级数据集与聚合统计。
- `BenchmarkExecutionHarness` 负责把 `runtime_surface × importer_variant × scene_variant × solver_suite × capture_mode` 的矩阵对映射成可执行 runtime target，并统一执行/回传 evidence。
- `benchmark_runtime_cases.py` 是 runtime harness case catalog：每个 case 直接驱动 importer / scene / planner / capture 主链，而不是转发到测试节点 selector。
- `BenchmarkMatrixService` 继续负责声明式矩阵加载、pair 校验与 target contract 校验。
