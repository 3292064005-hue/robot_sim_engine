---
owner: quality
audience: contributor
status: canonical
source_of_truth: manual
last_reviewed: 2026-04-18
---
# Testing and Quality

## 快速入口

- 单元 / 回归：`pytest tests/unit tests/regression -q`
- 全量：`pytest --cov=src/robot_sim --cov-report=term-missing --cov-report=json:coverage.json -q`
- 文档/契约再生成：`python scripts/regenerate_quality_contracts.py`
- 质量契约核对：`python scripts/verify_quality_contracts.py`
- clean source bundle：`python scripts/package_release.py --output dist/source-release.zip --top-level-dir robot_sim_engine`
- 文档治理与语义契约核对：`python scripts/verify_docs_information_architecture.py`

## 质量门禁

当前项目将质量门禁拆成三层：

- release blockers：`python scripts/verify_release_blockers.py`
- runtime contracts：`python scripts/verify_runtime_gate_layer.py`
- governance evidence：`python scripts/verify_governance_gate_layer.py`

分层内部仍保留细分 gate：

- 运行时/环境契约：`scripts/verify_runtime_contracts.py`、compatibility/perf/release 相关校验
- 单元/回归：`tests/unit`、`tests/regression`
- GUI smoke：`scripts/verify_gui_smoke.py`
- 生成物/文档契约：`scripts/regenerate_quality_contracts.py`、`scripts/verify_quality_contracts.py`
- 文档治理门禁：`scripts/verify_docs_information_architecture.py`

文档治理门禁现在不只检查 front matter 与入口页映射，还会对**全量说明文档**执行 semantic coverage：先按文档类别执行基础语义策略，再对已登记高风险主题执行 **semantic contracts** 校验：

- 基础语义策略：全量说明文档 semantic coverage，保证 canonical / entry-page / generated 都维持正确文档形态
- required markers：当前文档必须显式出现的契约语句
- forbidden markers：已废弃或会误导主链理解的旧语义

因此，“结构完整但语义已过期”的文档，也会被 docs gate 拦截。

## 维护顺序

1. 修改运行时真源或 canonical 文档。
2. 重新生成 `docs/generated/*.md`：`python scripts/regenerate_quality_contracts.py`
3. 执行 `python scripts/verify_docs_information_architecture.py`
4. 执行 `python scripts/verify_quality_contracts.py`
5. 运行相关 unit/regression 或全量验证

## 生成型文档

当前生成型真源集中在：

- `docs/generated/quality_gates.md`
- `docs/generated/module_status.md`
- `docs/generated/capability_matrix.md`
- `docs/generated/exception_catch_matrix.md`
- `docs/generated/quality_evidence.md`

根目录同名 `docs/*.md` 文件仅作为稳定入口页保留，不应直接手写生成内容。
