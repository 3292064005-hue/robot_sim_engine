---
owner: quality
audience: maintainer
status: canonical
source_of_truth: regenerated
last_reviewed: 2026-04-18
---
# Generated contract docs

本目录保存由运行时真源再生成的 contract 文档。根目录 `docs/*.md` 同名文件仅作为 entry page 存在；需要更新内容时，应优先修改运行时真源并执行 regeneration，而不是手写 generated 文档本身。

当前 generated canonical 文档包括：

- `docs/generated/quality_gates.md`
- `docs/generated/module_status.md`
- `docs/generated/capability_matrix.md`
- `docs/generated/exception_catch_matrix.md`
- `docs/generated/quality_evidence.md`

## 维护流程

1. 修改运行时真源 / capability / governance / exception policy 等源头。
2. 执行 `python scripts/regenerate_quality_contracts.py`。
3. 执行 `python scripts/verify_quality_contracts.py`，确认 checked-in generated docs 与运行时真源一致。
4. 执行 `python scripts/verify_docs_information_architecture.py`，确认 entry page / canonical mapping、全量说明文档 semantic coverage 以及高漂移文档的 semantic contracts 仍保持一致。

## Docs gate 说明

`verify_docs_information_architecture.py` 当前不只校验 front matter 和分层映射，还会对全量说明文档施加基础语义策略，并对高漂移文档校验 required / forbidden markers。若 canonical 或 entry-page 文档出现过期字段、旧边界或误导性语句，docs gate 会直接失败。
