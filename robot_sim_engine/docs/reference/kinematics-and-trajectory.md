---
owner: architecture
audience: contributor
status: canonical
source_of_truth: manual
last_reviewed: 2026-04-17
---
# Kinematics and Trajectory Reference

## Frame conventions

- `world`：全局可视化 / scene frame
- `base`：机器人 base frame（`RobotSpec.base_T`）
- `tool`：tool flange transform（`RobotSpec.tool_T`）

`Pose` 是稳定应用/运行时 pose surface，`Transform` 是 compose / inverse / rigid validation 使用的 homogeneous-matrix contract。

## FK / IK conventions

- FK 结果解释为基于配置串行链生成的 homogeneous transforms
- GUI 输入可使用 Euler / rotation-vector 形式
- solver internals 使用 matrix / rotation-vector / quaternion，不直接依赖 Euler

## Trajectory semantics

- `goal_position_error` / `goal_orientation_error`：最终状态对目标的误差
- `start_to_end_position_delta` / `start_to_end_orientation_delta`：轨迹首末样本之间的实际位移，不等价于目标误差
- path generation、retiming、validation 是分离阶段

## Playback/cache integrity

- `JointTrajectory.cache_status` 由缓存数组完整性归一化得出
- `ready` / `recomputed` 仅在缓存完整时成立
- validation 可为诊断目的做 FK fallback，但不等价于“trajectory 已具备 playback cache”
- presentation/playback 主链必须以 `trajectory.is_playback_ready` 为硬门槛

## Importer-related notes

- `urdf_model` 保留 serial URDF joint/link 语义，并通过 source/runtime/articulated/geometry summaries 暴露 fidelity
- `urdf_skeleton` 是有意近似的 bounded-fidelity importer，不是通用 URDF tree 实现
