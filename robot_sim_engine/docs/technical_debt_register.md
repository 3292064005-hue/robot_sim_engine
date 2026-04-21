---
owner: docs
audience: all
status: entry-page
source_of_truth: entry-point
canonical_target: docs/governance/technical-debt.md
last_reviewed: 2026-04-18
---
# Technical Debt Register

> Legacy entry page. Canonical governance policy now lives in `docs/governance/technical-debt.md`.

本入口页只保留技术债摘要与跳转，不再重复维护完整治理表。
- 稳定 GUI/worker/thread/model 主链已移除本地 Qt fallback/dummy shim；遗留注入范围只允许保留在 tests/regression 等受控验证层。
- 任何需要 debt 条目、处置状态或历史背景的场景，都应直接阅读 canonical 文档。

- regeneration source: `python scripts/regenerate_quality_contracts.py`
- editing policy: 请优先修改 canonical doc / 运行时真源，再执行 regeneration；不要在入口页维护长篇副本。

请跳转阅读：[`docs/governance/technical-debt.md`](governance/technical-debt.md)
