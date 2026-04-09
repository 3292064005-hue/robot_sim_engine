# Importer fidelity

- `yaml` importer is native/high-fidelity for this project.
<<<<<<< HEAD
- `urdf_model` preserves a serial URDF link/joint model, joint axes/limits, and visual/collision availability；运行时现通过 `runtime_fidelity_contract.runtime_dispatch` 真正分发到 `ArticulatedRobotModel` 作为 FK/Jacobian/数值 IK 的主执行面，`RuntimeRobotModel.execution_rows` 仅保留给 bounded DH compatibility adapter。
- `urdf_skeleton` remains available as a compatibility fallback that collapses URDF joint origins into an approximate DH-like serial chain.
- 运行时 FK / IK / trajectory / benchmark 现在统一优先消费 `RobotSpec.runtime_model`；`runtime_model.execution_rows` 仍保留 serial execution adapter 兼容面，但求解内核不再直接绑定 `RobotSpec.runtime_model` / `spec.dh_rows`。

- 导入后的 visual/collision geometry 现在优先保存在 `ImportedRobotPackage.geometry_model` typed object 中，并在后续 load/save/runtime scene 流程中保持可恢复；metadata 仅保留轻量引用，不再承载重型 geometry payload。
- live 3D scene 现在会消费 `RobotGeometry`，对 box / cylinder / sphere / capsule primitive 做稳定渲染；mesh primitive 会优先读取可恢复文件，失败时退化为 capsule proxy。
- 若用户在编辑器中改写导入模型的 DH 行，系统会显式降级为 `edited_runtime_dh` 语义，并清理原 structured/source-model fidelity 声明。
- `tests/regression/baselines/importer_fidelity_baseline.json` + `scripts/regenerate_importer_fidelity_baseline.py` 现在作为 importer fidelity 黄金基线；YAML 原生模型与 structured URDF 导入摘要必须保持稳定。

- `runtime_model_summary` / `articulated_model_summary` 仍会进入 runtime planning-scene metadata 与 session export，但 importer/registry 持久化主链现优先保存 typed object（`ImportedRobotPackage` / `CanonicalRobotModel` / `RobotGeometryModel`），不再把 metadata 当成唯一 authority。
- `urdf_model` 现在会显式生成 `runtime_fidelity_contract` 与 `downgrade_records`，把多 root、branch prune、fixed-joint collapse、visual/collision proxy 等降级点结构化写入 source summary / canonical metadata / imported package metadata。

- importer 主链现在会生成 `ImportedRobotPackage`，其中显式拆分 `source model / runtime model / articulated model / geometry model`。`RobotRegistry`、`RuntimeAssetService` 与 `ExportService` 优先消费这份 package typed object，再向 session/export/runtime scene 投影摘要。
=======
- `urdf_skeleton` approximates a DH-like serial chain from URDF joint origins. It is not a full URDF tree importer.
>>>>>>> 3ed78e647985c6d680c085e4480d898855278db3
