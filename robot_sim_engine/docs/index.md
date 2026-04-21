---
owner: docs
audience: all
status: canonical
source_of_truth: manual
last_reviewed: 2026-04-18
---
# Documentation Index

## 结构分层

文档按如下分层组织：

| layer | 说明 | 典型位置 |
| --- | --- | --- |
| getting-started | 新读者入门、仓库结构、快速运行 | `getting-started/quickstart.md`, `getting-started/repository-layout.md` |
| architecture | 主链架构、执行模型、planning scene、importer、render/runtime | `architecture/overview.md`, `architecture/execution-model.md`, `architecture/planning-scene.md`, `architecture/importer-model.md`, `architecture/render-runtime.md` |
| guides | 配置、插件、导出、打包、测试与质量 | `guides/configuration-profiles.md`, `guides/plugin-development.md`, `guides/export-and-session.md`, `guides/packaging-and-release.md`, `guides/testing-and-quality.md` |
| reference | schema / contracts / benchmark / kinematics 等长期参考 | `reference/schema-and-contracts.md`, `reference/benchmark-suite.md`, `reference/kinematics-and-trajectory.md`, `reference/generated-contracts.md` |
| governance | 兼容治理、技术债、路线图、文档治理、外部代码引入规则 | `governance/compatibility-policy.md`, `governance/documentation-governance.md`, `governance/technical-debt.md`, `governance/roadmap.md`, `governance/external-code-intake-policy.md` |
| generated | 生成型/契约型文档的集中入口 | `generated/README.md` |

## Legacy entry pages

根目录下仍保留一批 legacy entry pages，例如：

- `docs/planning_scene.md`
- `docs/importer_fidelity.md`
- `docs/quality_gates.md`
- `docs/module_status.md`

这些文件只保留摘要与跳转，不再承担完整讲解；如需字段级说明，请跳转到各主题 canonical 文档或 `docs/generated/` 中的生成型真源。

## 维护规则摘要

- 先改 canonical / runtime truth，再改 entry pages。
- 生成型文档统一由 `python scripts/regenerate_quality_contracts.py` 回写到 `docs/generated/`。
- `python scripts/verify_docs_information_architecture.py` 负责校验文档架构、入口页映射、全量说明文档 semantic coverage，以及高漂移主题的 semantic contracts。
- `python scripts/verify_quality_contracts.py` 负责校验 checked-in generated docs 与运行时真源一致。

更多治理细节见：`docs/governance/documentation-governance.md`。
