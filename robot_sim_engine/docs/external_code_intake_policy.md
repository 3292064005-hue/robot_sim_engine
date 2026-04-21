---
owner: docs
audience: all
status: entry-page
source_of_truth: entry-point
canonical_target: docs/governance/external-code-intake-policy.md
last_reviewed: 2026-04-18
---
# External code intake policy

> Legacy entry page. Canonical governance policy now lives in `docs/governance/external-code-intake-policy.md`.

本入口页只保留 intake 范围摘要与跳转，不再重复维护完整白名单/黑盒重实现规则。
当前治理结论：
- 允许的 intake 方式仍分为 **white-list migration** 与 **black-box reimplementation**。
- 许可证、第三方声明、变更记录、回滚路径与同步测试/文档更新的强约束，以 canonical policy 为准。
- 任何需要字段级要求、许可证边界或 intake checklist 的场景，都应直接阅读 canonical 文档。

- regeneration source: `python scripts/regenerate_quality_contracts.py`
- editing policy: 请优先修改 canonical doc / 运行时真源，再执行 regeneration；不要在入口页维护长篇副本。

请跳转阅读：[`docs/governance/external-code-intake-policy.md`](governance/external-code-intake-policy.md)
