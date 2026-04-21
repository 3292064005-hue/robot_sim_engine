from __future__ import annotations

"""Canonical documentation manifest for entry pages, canonical docs, and semantic contracts.

This module is the single maintained source for docs topology so the docs gate, generated entry
pages, and contributor tooling read one manifest rather than copying page inventories across
multiple scripts.
"""

from dataclasses import dataclass
from pathlib import PurePosixPath

DOCS_FRONT_MATTER_REQUIRED_KEYS: tuple[str, ...] = (
    'owner',
    'audience',
    'status',
    'source_of_truth',
    'last_reviewed',
)

ENTRY_PAGE_REQUIRED_KEYS: tuple[str, ...] = DOCS_FRONT_MATTER_REQUIRED_KEYS + ('canonical_target',)
GENERATED_DOC_REQUIRED_KEYS: tuple[str, ...] = DOCS_FRONT_MATTER_REQUIRED_KEYS + ('generated_by',)

CANONICAL_DOCS: tuple[str, ...] = (
    'docs/index.md',
    'docs/getting-started/quickstart.md',
    'docs/getting-started/repository-layout.md',
    'docs/architecture/overview.md',
    'docs/architecture/execution-model.md',
    'docs/architecture/planning-scene.md',
    'docs/architecture/importer-model.md',
    'docs/architecture/render-runtime.md',
    'docs/guides/configuration-profiles.md',
    'docs/guides/plugin-development.md',
    'docs/guides/export-and-session.md',
    'docs/guides/packaging-and-release.md',
    'docs/guides/testing-and-quality.md',
    'docs/reference/schema-and-contracts.md',
    'docs/reference/benchmark-suite.md',
    'docs/reference/kinematics-and-trajectory.md',
    'docs/reference/generated-contracts.md',
    'docs/governance/compatibility-policy.md',
    'docs/governance/documentation-governance.md',
    'docs/governance/technical-debt.md',
    'docs/governance/roadmap.md',
    'docs/governance/external-code-intake-policy.md',
    'docs/generated/README.md',
)

GENERATED_DOCS: tuple[str, ...] = (
    'docs/generated/quality_gates.md',
    'docs/generated/module_status.md',
    'docs/generated/capability_matrix.md',
    'docs/generated/exception_catch_matrix.md',
    'docs/generated/quality_evidence.md',
)

ENTRY_PAGES: dict[str, str] = {
    'docs/architecture.md': 'docs/architecture/overview.md',
    'docs/benchmark_suite.md': 'docs/reference/benchmark-suite.md',
    'docs/capability_matrix.md': 'docs/generated/capability_matrix.md',
    'docs/compatibility_downstream_inventory.md': 'docs/governance/compatibility-policy.md',
    'docs/compatibility_matrix.md': 'docs/governance/compatibility-policy.md',
    'docs/compatibility_support_boundary.md': 'docs/governance/compatibility-policy.md',
    'docs/error_taxonomy.md': 'docs/reference/schema-and-contracts.md',
    'docs/exception_catch_matrix.md': 'docs/generated/exception_catch_matrix.md',
    'docs/export_formats.md': 'docs/reference/schema-and-contracts.md',
    'docs/external_code_intake_policy.md': 'docs/governance/external-code-intake-policy.md',
    'docs/importer_fidelity.md': 'docs/architecture/importer-model.md',
    'docs/kinematics_conventions.md': 'docs/reference/kinematics-and-trajectory.md',
    'docs/module_status.md': 'docs/generated/module_status.md',
    'docs/packaging.md': 'docs/guides/packaging-and-release.md',
    'docs/planning_scene.md': 'docs/architecture/planning-scene.md',
    'docs/plugin_development.md': 'docs/guides/plugin-development.md',
    'docs/quality_evidence.md': 'docs/generated/quality_evidence.md',
    'docs/quality_gates.md': 'docs/generated/quality_gates.md',
    'docs/roadmap.md': 'docs/governance/roadmap.md',
    'docs/schema_versions.md': 'docs/reference/schema-and-contracts.md',
    'docs/stable_surface_migration.md': 'docs/governance/compatibility-policy.md',
    'docs/task_event_schema.md': 'docs/reference/schema-and-contracts.md',
    'docs/task_threading_model.md': 'docs/architecture/execution-model.md',
    'docs/technical_debt_register.md': 'docs/governance/technical-debt.md',
    'docs/test_plan.md': 'docs/guides/testing-and-quality.md',
    'docs/trajectory_semantics.md': 'docs/reference/kinematics-and-trajectory.md',
    'docs/v7_blueprint.md': 'docs/governance/roadmap.md',
}

ENTRY_PAGE_TITLES: dict[str, str] = {
    'docs/architecture.md': 'Architecture Overview',
    'docs/benchmark_suite.md': 'Benchmark Suite',
    'docs/capability_matrix.md': 'Capability Matrix',
    'docs/compatibility_downstream_inventory.md': 'Compatibility Downstream Inventory',
    'docs/compatibility_matrix.md': 'Compatibility Matrix',
    'docs/compatibility_support_boundary.md': 'Compatibility Support Boundary',
    'docs/error_taxonomy.md': 'Error Taxonomy',
    'docs/exception_catch_matrix.md': 'Exception Catch Matrix',
    'docs/export_formats.md': 'Export Formats',
    'docs/external_code_intake_policy.md': 'External code intake policy',
    'docs/importer_fidelity.md': 'Importer Fidelity',
    'docs/kinematics_conventions.md': 'Kinematics Conventions',
    'docs/module_status.md': 'Module Status',
    'docs/packaging.md': 'Packaging & Release',
    'docs/planning_scene.md': 'Planning Scene / ACM',
    'docs/plugin_development.md': 'Plugin Development',
    'docs/quality_evidence.md': 'Quality Evidence',
    'docs/quality_gates.md': 'Quality Gates',
    'docs/roadmap.md': 'Roadmap',
    'docs/schema_versions.md': 'Schema Versions',
    'docs/stable_surface_migration.md': 'Stable Surface Migration',
    'docs/task_event_schema.md': 'Task Event Schema',
    'docs/task_threading_model.md': 'Task Threading Model',
    'docs/technical_debt_register.md': 'Technical Debt Register',
    'docs/test_plan.md': 'Test Plan',
    'docs/trajectory_semantics.md': 'Trajectory Semantics',
    'docs/v7_blueprint.md': 'V7 Blueprint',
}

ENTRY_PAGE_SUMMARY_LINES: dict[str, tuple[str, ...]] = {
    'docs/importer_fidelity.md': (
        '本入口页只保留 importer fidelity 摘要与跳转，不再重复维护完整 runtime contract 字段。',
        '当前主结论：',
        '- `yaml` importer 仍是本项目的 native / high-fidelity 路径。',
        '- `urdf_model` 现在以 `articulated_model` 作为主语义面，并保留 branched-tree graph projection。',
        '- 当前 execution adapter 已升级为 `active-path-over-tree`；graph preservation 已支持，branched tree 可沿活动执行链进入求解主线，但这仍不等于 full-tree simultaneous execution 已支持。',
        '- `urdf_skeleton` 仍是 bounded-fidelity approximate importer，用于 demo / tests / constrained serial benchmarks。',
    ),
    'docs/planning_scene.md': (
        '本入口页只保留 stable scene surface 的摘要与跳转，不再重复维护完整字段表、authority 细节或 fidelity roadmap 说明。',
        '当前主结论：',
        '- `PlanningScene` 是当前环境障碍物、ACM、scene revision 与 scene authority 的稳定主入口。',
        '- stable surface 当前覆盖 canonical `planning_scene` 输入、scene summary / export / session 摘要，以及 scene command / diff authority 的闭环暴露。',
        '- collision fidelity 已区分 declaration / validation / render geometry 与 backend roadmap；字段级 contract 与边界说明以 canonical 架构文档为准。',
        '- scene editor、runtime projection、session/export 与 diagnostics 的详细 contract，请不要在本入口页重复维护。',
    ),
    'docs/external_code_intake_policy.md': (
        '本入口页只保留 intake 范围摘要与跳转，不再重复维护完整白名单/黑盒重实现规则。',
        '当前治理结论：',
        '- 允许的 intake 方式仍分为 **white-list migration** 与 **black-box reimplementation**。',
        '- 许可证、第三方声明、变更记录、回滚路径与同步测试/文档更新的强约束，以 canonical policy 为准。',
        '- 任何需要字段级要求、许可证边界或 intake checklist 的场景，都应直接阅读 canonical 文档。',
    ),
    'docs/roadmap.md': (
        '本入口页只保留 roadmap 摘要与跳转，不再重复维护完整阶段说明。',
        '- 当前发布口径仍以 `V7` 为主版本边界；详情与增量计划以 canonical roadmap 为准。',
        '- 任何需要阶段拆分、稳定面边界或后续 capability 规划的场景，都应直接阅读 canonical 文档。',
    ),
    'docs/schema_versions.md': (
        '本入口页只保留 schema/version 摘要与跳转，不再重复维护完整字段表。',
        '- 当前导出 schema 主版本为 `v7`，session schema 为 `session-v7`；字段级 contract 以 canonical schema 文档为准。',
        '- 任何需要版本迁移、兼容面或 payload 说明的场景，都应直接阅读 canonical 文档。',
    ),
    'docs/technical_debt_register.md': (
        '本入口页只保留技术债摘要与跳转，不再重复维护完整治理表。',
        '- 稳定 GUI/worker/thread/model 主链已移除本地 Qt fallback/dummy shim；遗留注入范围只允许保留在 tests/regression 等受控验证层。',
        '- 任何需要 debt 条目、处置状态或历史背景的场景，都应直接阅读 canonical 文档。',
    ),
}

DOC_SPECIFIC_SEMANTIC_CONTRACTS: dict[str, dict[str, tuple[str, ...]]] = {
    'docs/architecture/importer-model.md': {
        'required': (
            'primary_execution_surface: articulated_model',
            'branched_tree_supported: true',
            'branched_tree_projection_supported: true',
            'branched_tree_execution_supported: active-path-over-tree',
            'closed_loop_supported: false',
            'mobile_base_supported: false',
        ),
        'forbidden': (
            'branched_tree_supported: false',
            'branched_tree_execution_supported: serial-tree-only',
        ),
    },
    'docs/importer_fidelity.md': {
        'required': (
            'Canonical architecture doc now lives in `docs/architecture/importer-model.md`.',
            'articulated_model',
            'branched-tree graph projection',
            'active-path-over-tree',
        ),
        'forbidden': (
            'structured serial semantics',
            'serial-tree-only',
        ),
    },
    'docs/planning_scene.md': {
        'required': (
            'Canonical architecture doc now lives in `docs/architecture/planning-scene.md`.',
            'stable scene surface 的摘要与跳转',
            'scene command / diff authority',
            'collision fidelity',
        ),
        'forbidden': (
            '## Scene command / diff authority',
            '## Collision fidelity roadmap contract',
        ),
    },
    'docs/external_code_intake_policy.md': {
        'required': (
            'Canonical governance policy now lives in `docs/governance/external-code-intake-policy.md`.',
            '本入口页只保留 intake 范围摘要与跳转',
            'white-list migration',
            'black-box reimplementation',
        ),
        'forbidden': (
            '## Allowed intake modes',
            '## Intake checklist',
        ),
    },
    'docs/governance/documentation-governance.md': {
        'required': (
            '所有说明文档都必须进入 docs gate 的语义覆盖范围',
            '基础语义策略（按文档类别）',
            '文件级 required / forbidden markers',
            '不要再维护整页字段表、完整规则副本或次级讲解页',
        ),
        'forbidden': (),
    },
    'docs/guides/testing-and-quality.md': {
        'required': (
            '文档治理与语义契约核对',
            '全量说明文档 semantic coverage',
            'semantic contracts',
            '结构完整但语义已过期',
        ),
        'forbidden': (),
    },
    'docs/generated/README.md': {
        'required': (
            '全量说明文档 semantic coverage',
            'front matter 和分层映射',
            '基础语义策略',
            '过期字段、旧边界或误导性语句',
        ),
        'forbidden': (),
    },
    'docs/index.md': {
        'required': (
            'legacy entry pages',
            '摘要与跳转',
            '全量说明文档 semantic coverage',
            'semantic contracts',
        ),
        'forbidden': (),
    },
}


@dataclass(frozen=True)
class EntryPageSpec:
    path: str
    canonical_target: str
    title: str
    summary_lines: tuple[str, ...] = ()
    owner: str = 'docs'
    audience: str = 'all'
    source_of_truth: str = 'entry-point'
    last_reviewed: str = '2026-04-18'

    @property
    def generated_target(self) -> bool:
        return self.canonical_target.startswith('docs/generated/')

    @property
    def relative_link(self) -> str:
        source_dir = PurePosixPath(self.path).parent
        target = PurePosixPath(self.canonical_target)
        return target.relative_to(source_dir) if str(source_dir) != '.' else target

    def render(self) -> str:
        metadata = _front_matter(
            owner=self.owner,
            audience=self.audience,
            status='entry-page',
            source_of_truth=self.source_of_truth,
            canonical_target=self.canonical_target,
            last_reviewed=self.last_reviewed,
        )
        lines = [f'# {self.title}', '']
        if self.generated_target:
            lines.extend(
                (
                    '本文件是稳定入口页。',
                    '',
                    f'- canonical generated doc: `{self.canonical_target}`',
                    '- regeneration source: `python scripts/regenerate_quality_contracts.py`',
                    '- editing policy: 请优先修改运行时真源，再执行 regeneration；不要直接把契约内容手写回入口页。',
                    '',
                    f'请跳转阅读：[`{self.canonical_target}`]({self.relative_link})',
                    '',
                )
            )
        else:
            lead = f'> Legacy entry page. Canonical architecture doc now lives in `{self.canonical_target}`.'
            if '/governance/' in self.canonical_target:
                lead = f'> Legacy entry page. Canonical governance policy now lives in `{self.canonical_target}`.'
            lines.extend((lead, ''))
            if self.summary_lines:
                lines.extend(self.summary_lines)
                lines.append('')
            else:
                lines.extend(
                    (
                        '本入口页只保留摘要与跳转，不再重复维护完整字段、规则副本或实现细节。',
                        '',
                        '- canonical doc 是当前唯一 source of truth。',
                        '- 需要字段级 contract、边界说明或演进策略时，请直接阅读 canonical 文档。',
                        '',
                    )
                )
            lines.extend(
                (
                    '- regeneration source: `python scripts/regenerate_quality_contracts.py`',
                    '- editing policy: 请优先修改 canonical doc / 运行时真源，再执行 regeneration；不要在入口页维护长篇副本。',
                    '',
                    f'请跳转阅读：[`{self.canonical_target}`]({self.relative_link})',
                    '',
                )
            )
        return metadata + '\n'.join(lines)


def _front_matter(**values: str) -> str:
    lines = ['---']
    lines.extend(f'{key}: {value}' for key, value in values.items())
    lines.append('---')
    lines.append('')
    return '\n'.join(lines)


def _default_entry_title(path: str) -> str:
    return PurePosixPath(path).stem.replace('_', ' ').replace('-', ' ').title()


def entry_page_specs() -> tuple[EntryPageSpec, ...]:
    specs: list[EntryPageSpec] = []
    for path, canonical_target in ENTRY_PAGES.items():
        specs.append(
            EntryPageSpec(
                path=path,
                canonical_target=canonical_target,
                title=ENTRY_PAGE_TITLES.get(path, _default_entry_title(path)),
                summary_lines=ENTRY_PAGE_SUMMARY_LINES.get(path, ()),
            )
        )
    return tuple(specs)


def render_entry_pages() -> dict[str, str]:
    return {spec.path: spec.render() for spec in entry_page_specs()}


def semantic_scope_docs() -> tuple[str, ...]:
    return tuple(sorted(set(CANONICAL_DOCS) | set(GENERATED_DOCS) | set(ENTRY_PAGES)))
