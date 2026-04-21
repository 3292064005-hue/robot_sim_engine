---
owner: docs
audience: maintainer
status: canonical
source_of_truth: manual
last_reviewed: 2026-04-18
---

# Documentation Governance

## 文档类型

- **canonical**：当前主题的讲解真源，应优先修改这里。
- **entry-page**：稳定入口页，只负责摘要、适用范围与跳转，不重复维护完整说明。
- **generated**：由脚本再生成的契约/清单文档，不应手工改写生成内容。

## 维护规则

1. 一个主题只保留一个 canonical 文档。
2. `docs/` 根目录的 legacy entry pages 只保留摘要、边界提示和 canonical 链接；不要再维护整页字段表、完整规则副本或次级讲解页。
3. 生成型文档统一由 `python scripts/regenerate_quality_contracts.py` 维护到 `docs/generated/`；legacy entry pages 也由同一 regeneration 流程结合 `src/robot_sim/infra/docs_manifest.py` 生成，避免 canonical / entry-page / semantic contract 列表在多个脚本中重复维护。
4. 修改运行时真源后，必须同步检查：README、`docs/index.md`、相关 canonical 文档、生成型入口页与回归守卫。
5. 不要在 entry page 与 canonical 文档中复制整段字段表；字段真源应集中在 reference/generated 文档。
6. 所有说明文档都必须进入 docs gate 的语义覆盖范围：`python scripts/verify_docs_information_architecture.py` 先按文档类别执行基础语义策略（canonical / entry-page / generated），再对高漂移主题追加文件级 required / forbidden markers。

## Front matter 约定

所有分层文档与入口页都应携带 front matter：

- `owner`
- `audience`
- `status`
- `source_of_truth`
- `last_reviewed`
- entry page 额外要求：`canonical_target`

## Docs gate 范围

`python scripts/verify_docs_information_architecture.py` 当前覆盖：

- front matter 完整性
- canonical / entry-page / generated 分层关系
- entry-page 到 canonical target 的稳定映射
- README / `docs/index.md` 的文档治理导航锚点
- 全量说明文档的基础语义策略（按文档类别）
  - canonical：必须保持解释性真源形态，不能泄露 entry-page 标记
  - entry-page：必须保持瘦身摘要与跳转形态，禁止重新写胖
  - generated：必须保持 generated metadata 与 contract surface 形态
- 高漂移文档的文件级 required / forbidden markers

当某个文档已经成为主链契约或易漂移说明时，应追加文件级 required / forbidden markers，而不是只依赖人工 review。

## 审核触发条件

以下改动必须同步做文档审查：

- 运行入口、profile、packaging 变更
- planning scene / importer / render runtime 主链变更
- schema/export/session/task event contract 变更
- compatibility / retirement / migration policy 变更
- quality gates / generated docs contract 变更
- docs gate 自身的 semantic contract 范围变更
