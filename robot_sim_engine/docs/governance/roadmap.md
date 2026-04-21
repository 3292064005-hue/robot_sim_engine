---
owner: governance
audience: contributor
status: canonical
source_of_truth: manual
last_reviewed: 2026-04-18
---
# Roadmap

## Current release line: V7

当前 V7 主线已经完成：

- typed session/export contract 收敛
- importer/runtime 的 articulated execution contract 落地
- planning scene authority / scene command / diff summary 收敛
- generated contracts、quality gates 与 docs governance 收敛
- MainController bootstrap narrowed behind `PresentationBootstrapBundle`
- Packaged config staging from single-source `configs/`

### Blueprint note

V7 的核心目标是工程硬化，不是继续堆无界新功能。蓝图重心集中在：

- 统一版本真源
- 正式任务生命周期
- importer fidelity
- trajectory validator 拆分
- MainWindow 协调层下沉

## Stable product line (next candidate: V8)

V8 候选仍沿稳定主线推进，重点是把现有 deterministic planning/runtime validation surface 做厚，而不是跨越到物理仿真叙事：

- redundant solver plugin 治理与 alias 收口
- richer waypoint graph editor
- scene picking to target pose
- URDF geometry + simple mesh visualization
- broader collision backend implementations beyond current AABB + capsule stable baseline
- execution_graph 从 metadata contract 升级为更明确的 selectable execution scope（例如 branch subset / multi-tip selector），但仍不宣称 full branched execution 已进入 stable line

## Separate future capability track (not in stable line)

以下方向仅作为未来独立 capability track 评估，不会在当前稳定线中以“局部补丁已支持”的方式对外表述：

- rigid-body dynamics
- contact / friction simulation
- closed-loop mechanisms
- floating-base / mobile base execution
- high-fidelity physics simulation

## Explicitly out of scope now

- closed-loop control
- industrial controller SDK integration
- continuous collision detection
- marketing or documentation language that implies the stable line is already a full dynamics simulator
