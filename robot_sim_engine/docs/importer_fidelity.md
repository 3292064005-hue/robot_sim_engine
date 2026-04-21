---
owner: docs
audience: all
status: entry-page
source_of_truth: entry-point
canonical_target: docs/architecture/importer-model.md
last_reviewed: 2026-04-18
---
# Importer Fidelity

> Legacy entry page. Canonical architecture doc now lives in `docs/architecture/importer-model.md`.

本入口页只保留 importer fidelity 摘要与跳转，不再重复维护完整 runtime contract 字段。
当前主结论：
- `yaml` importer 仍是本项目的 native / high-fidelity 路径。
- `urdf_model` 现在以 `articulated_model` 作为主语义面，并保留 branched-tree graph projection。
- 当前 execution adapter 已升级为 `active-path-over-tree`；graph preservation 已支持，branched tree 可沿活动执行链进入求解主线，但这仍不等于 full-tree simultaneous execution 已支持。
- `urdf_skeleton` 仍是 bounded-fidelity approximate importer，用于 demo / tests / constrained serial benchmarks。

- regeneration source: `python scripts/regenerate_quality_contracts.py`
- editing policy: 请优先修改 canonical doc / 运行时真源，再执行 regeneration；不要在入口页维护长篇副本。

请跳转阅读：[`docs/architecture/importer-model.md`](architecture/importer-model.md)
