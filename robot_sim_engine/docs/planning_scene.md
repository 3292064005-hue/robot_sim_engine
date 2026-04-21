---
owner: docs
audience: all
status: entry-page
source_of_truth: entry-point
canonical_target: docs/architecture/planning-scene.md
last_reviewed: 2026-04-18
---
# Planning Scene / ACM

> Legacy entry page. Canonical architecture doc now lives in `docs/architecture/planning-scene.md`.

本入口页只保留 stable scene surface 的摘要与跳转，不再重复维护完整字段表、authority 细节或 fidelity roadmap 说明。
当前主结论：
- `PlanningScene` 是当前环境障碍物、ACM、scene revision 与 scene authority 的稳定主入口。
- stable surface 当前覆盖 canonical `planning_scene` 输入、scene summary / export / session 摘要，以及 scene command / diff authority 的闭环暴露。
- collision fidelity 已区分 declaration / validation / render geometry 与 backend roadmap；字段级 contract 与边界说明以 canonical 架构文档为准。
- scene editor、runtime projection、session/export 与 diagnostics 的详细 contract，请不要在本入口页重复维护。

- regeneration source: `python scripts/regenerate_quality_contracts.py`
- editing policy: 请优先修改 canonical doc / 运行时真源，再执行 regeneration；不要在入口页维护长篇副本。

请跳转阅读：[`docs/architecture/planning-scene.md`](architecture/planning-scene.md)
