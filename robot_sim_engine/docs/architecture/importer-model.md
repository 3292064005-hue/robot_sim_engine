---
owner: architecture
audience: contributor
status: canonical
source_of_truth: manual
last_reviewed: 2026-04-20
---
# Importer Model

## 目标

importer 主线的目标不是“把所有运行时语义塞回一份 YAML metadata”，而是把：

- source model
- runtime model
- articulated model
- geometry model

拆成明确的 typed object，并以 `ImportedRobotPackage` 作为跨 registry / runtime / export / session 的统一包裹对象。

## Fidelity 分层

- `yaml` importer：native / high-fidelity
- `urdf_model` importer：保留 serial URDF link/joint 模型、joint axes/limits、visual/collision availability
- `urdf_skeleton` importer：bounded-fidelity approximate importer，用于 demo / tests / constrained serial benchmarks

## 运行时执行面

- FK / Jacobian / 数值 IK 统一优先消费 `ArticulatedRobotModel`
- `RuntimeRobotModel.execution_summary` 只保留运行态摘要，不再充当求解真执行面
- `RobotSpec` 运行语义已收口到 articulated transforms + canonical serial projection summary

## Geometry 与 downgrade records

- visual / collision geometry 优先存放于 `ImportedRobotPackage.geometry_model`
- metadata 只保留轻量引用与摘要，不再承载重型 geometry payload
- `urdf_model` 会显式生成 `runtime_fidelity_contract` 与 `downgrade_records`
- `ImportedRobotPackage.summary()` 会暴露 `fidelity_breakdown`

## 基线与回归

- importer fidelity 黄金基线：`tests/regression/baselines/importer_fidelity_baseline.json`
- 再生成脚本：`python scripts/regenerate_importer_fidelity_baseline.py`

更多细节见 legacy entry page：`docs/importer_fidelity.md`。


## Execution layer contract

`RuntimeRobotModel` 现在不再只是一份“可执行 DH 行表”，而是显式暴露三层执行契约：

- `source_model`：导入面或 canonical source 的来源、格式与 fidelity
- `articulated_graph`：当前主语义面，承载 joint/link topology 与 articulated execution truth
- `execution_adapter`：当前 FK/Jacobian/IK/benchmark 主链统一消费的 execution adapter，可在 serial tree 与 branched tree active path 之间切换

对应 summary / contract 字段：

- `primary_execution_surface: articulated_model`
- `execution_contract_version`
- `execution_layers`
- `articulated_topology`
- `execution_capability_matrix`

## URDF runtime fidelity contract

`urdf_model` importer 现在会在 `runtime_fidelity_contract` 中显式区分：

- `source_model_layer`
- `articulated_graph_layer`
- `execution_adapter_layer`

并稳定声明当前能力边界：

```yaml
primary_execution_surface: articulated_model
branched_tree_supported: true
branched_tree_projection_supported: true
branched_tree_execution_supported: active-path-over-tree
closed_loop_supported: false
mobile_base_supported: false
```

解释：

- `branched_tree_supported: true` 表示 importer/runtime 会保留 branched tree 的 source graph，并把它投影到 `ImportedRobotPackage.articulated_model` 与 runtime scene graph metadata。
- `branched_tree_projection_supported: true` 表示 graph preservation / projection 已落地，不再把 branched tree 裁成唯一 serial 主链真相。
- `branched_tree_execution_supported: active-path-over-tree` 表示执行适配层仍受当前 serial execution adapter 约束：**线性 serial-tree** 仍可执行，但**真正 branched topology** 不被宣称为已支持的 solver execution 主能力。
- `closed_loop_supported: false` 与 `mobile_base_supported: false` 仍是当前真实边界。

这组字段用于防止 import summary 看起来像“完整 URDF runtime”，但实际执行面仍然只是 bounded execution adapter；同时也避免把“graph preservation 已支持”“active-path execution 已支持”和“full branched execution 已支持”混为一谈。

## Execution graph roadmap

当前 `execution_graph` 在稳定发布线中的职责是：

- 显式描述 active-path-over-tree 的执行范围
- 让 GUI / headless / benchmark 在同一 contract 下携带 execution scope 元数据
- 同步输出 `execution_capability_matrix`，把 import fidelity / scene fidelity / collision fidelity / runtime execution support 分开表达
- 作为后续 execution-scope 升级的稳定字段，而不是提前宣称 full branched execution 已落地

计划中的升级顺序是：

1. `metadata contract` → `selectable execution scope`：允许多末端 / branch subset / task-frame binding 进入同一 contract 面
2. `selectable execution scope` → `broader articulated execution`：在不破坏现有 stable path 的前提下扩展 solver/runtime 消费面
3. 仅在独立 capability track 中讨论 closed-loop / floating-base / contact；这些能力当前**仍未进入稳定主线承诺**
