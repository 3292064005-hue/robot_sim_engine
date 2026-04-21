---
owner: docs
audience: all
status: entry-page
source_of_truth: entry-point
canonical_target: docs/reference/schema-and-contracts.md
last_reviewed: 2026-04-18
---
# Schema Versions

> Legacy entry page. Canonical architecture doc now lives in `docs/reference/schema-and-contracts.md`.

本入口页只保留 schema/version 摘要与跳转，不再重复维护完整字段表。
- 当前导出 schema 主版本为 `v7`，session schema 为 `session-v7`；字段级 contract 以 canonical schema 文档为准。
- 任何需要版本迁移、兼容面或 payload 说明的场景，都应直接阅读 canonical 文档。

- regeneration source: `python scripts/regenerate_quality_contracts.py`
- editing policy: 请优先修改 canonical doc / 运行时真源，再执行 regeneration；不要在入口页维护长篇副本。

请跳转阅读：[`docs/reference/schema-and-contracts.md`](reference/schema-and-contracts.md)
