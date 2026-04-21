from __future__ import annotations

import ast
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
import tomllib

GENERATED_DOC_NAMES: tuple[str, ...] = (
    'quality_gates.md',
    'module_status.md',
    'capability_matrix.md',
    'exception_catch_matrix.md',
    'quality_evidence.md',
)


from robot_sim.application.services.capability_service import CapabilityService
from robot_sim.application.services.module_status_service import ModuleStatusService
from robot_sim.application.services.runtime_feature_service import RuntimeFeaturePolicy
from robot_sim.infra.exception_policy import render_exception_catch_matrix_markdown, verify_exception_catch_matrix
from robot_sim.infra.docs_information_architecture import verify_docs_information_architecture
from robot_sim.infra.docs_manifest import render_entry_pages


def _build_runtime_truth_quality_service(project_root: Path) -> "QualityContractService":
    """Build the quality-contract renderer from the active runtime truth sources.

    Args:
        project_root: Repository root containing the checked-in source layout.

    Returns:
        QualityContractService: Contract renderer wired to the default-profile runtime
            registries, plugin loader, and capability service.

    Raises:
        FileNotFoundError: If runtime resources cannot be resolved from the repository root.
        Exception: Propagates registry/config construction failures so verification fails loud.
    """
    from robot_sim.app.plugin_loader import PluginLoader
    from robot_sim.app.registry_factory import build_importer_registry, build_planner_registry, build_solver_registry
    from robot_sim.app.runtime_paths import resolve_runtime_paths
    from robot_sim.application.services.config_service import ConfigService
    from robot_sim.application.services.module_status_service import ModuleStatusService
    from robot_sim.application.services.robot_registry import RobotRegistry
    from robot_sim.application.services.runtime_feature_service import RuntimeFeatureService
    from robot_sim.application.use_cases.run_ik import RunIKUseCase

    runtime_paths = resolve_runtime_paths(project_root, create_dirs=False)
    config_service = ConfigService(
        runtime_paths.config_root,
        profile=ConfigService.DEFAULT_PROFILE,
    )
    runtime_feature_policy = RuntimeFeatureService(config_service).load_policy()
    plugin_loader = PluginLoader(config_service.plugin_manifest_paths(), policy=runtime_feature_policy)
    capability_service = CapabilityService(
        runtime_feature_policy=runtime_feature_policy,
        plugin_loader=plugin_loader,
    )
    solver_registry = build_solver_registry(plugin_loader=plugin_loader)
    shared_ik_uc = RunIKUseCase(solver_registry)
    planner_registry = build_planner_registry(shared_ik_uc, plugin_loader=plugin_loader)
    robot_registry = RobotRegistry(
        runtime_paths.robot_root,
        readonly_roots=(runtime_paths.bundled_robot_root,),
    )
    importer_registry = build_importer_registry(robot_registry, plugin_loader=plugin_loader)
    module_status_service = ModuleStatusService(runtime_feature_policy=runtime_feature_policy)

    return QualityContractService(
        runtime_feature_policy=runtime_feature_policy,
        capability_matrix_renderer=lambda: capability_service.render_markdown(
            solver_registry=solver_registry,
            planner_registry=planner_registry,
            importer_registry=importer_registry,
        ),
        module_status_renderer=module_status_service.render_markdown,
    )


QUALITY_GATE_LINES: tuple[str, ...] = (
    '- release blockers: `python scripts/verify_release_blockers.py` => quick_quality + compatibility_budget + unit_and_regression + gui_smoke',
    '- runtime contracts: `python scripts/verify_runtime_gate_layer.py` => runtime_contracts + performance_smoke + headless_runtime_baseline + planning_scene_regression + collision_validation_matrix + scene_capture_baseline',
    '- runtime contract gate: `python scripts/verify_runtime_contracts.py --mode headless --check-packaged-configs` + `python scripts/verify_compatibility_retirement.py` + `python scripts/verify_perf_budget_config.py`',
    '- runtime baseline/details: `python scripts/verify_runtime_baseline.py --mode headless` + `pytest tests/unit/test_planning_scene_v2.py tests/unit/test_scene_authority_service.py -q` + `pytest tests/unit/test_planning_scene_validation.py tests/unit/test_scene_capability_surface.py -q` + `pytest tests/unit/test_scene_capture_support.py tests/unit/test_scene_render_contracts.py -q` + `pytest tests/performance/test_ik_smoke.py -q`',
    '- governance evidence: `python scripts/verify_governance_gate_layer.py` => governance_evidence + docs_sync',
    '- governance evidence detail: `python scripts/verify_module_governance.py --execute-gates --evidence-out artifacts/module_governance_evidence.json` + `python scripts/verify_benchmark_matrix.py --execute-gates --execute --evidence-out artifacts/benchmark_matrix_evidence.json` + `python scripts/collect_quality_evidence.py --out artifacts/quality_evidence.json --markdown-out artifacts/quality_evidence.md --release-manifest-out artifacts/release_manifest.json --merge artifacts/module_governance_evidence.json artifacts/benchmark_matrix_evidence.json runtime_contracts compatibility_budget performance_smoke`; the aggregated manifest now derives `artifact_ready`, `environment_ready`, and `release_ready` separately and always evaluates the checked-in release/gui environment contracts',
    '- aggregated quality evidence rejects governance/benchmark artifacts that were not generated with their required `--execute-gates` execution contract.',
    '- aggregated quality evidence rejects artifacts whose source-tree fingerprint or tracked release-file count does not match the current repository checkout; the original repo_root is retained as provenance metadata but is not treated as a transport-stability requirement.',
    '- unit/regression: `pytest tests/unit tests/regression -q`',
    '- shipped behavior contracts: repo profiles must remain differentiable, coordinators must stay on explicit dependency injection paths, export/screenshot coordinators must stay on worker lifecycle routes, render degradation state must stay projected in SessionState.render_runtime through a typed status-panel subscription flow, clean bootstrap/headless mainline paths must stay within the configured compatibility budget, public plugin SDK examples must remain loader-compatible, render telemetry must remain recorded as bounded structured state transitions + operation spans + sampling counters + backend-specific performance telemetry, diagnostics widgets must consume structured telemetry log sections, scene authority summaries must expose declaration/validation/render geometry layers, and screenshot/importer fidelity baselines must stay reproducible from checked-in fixtures',
    '- full validation: `pytest --cov=src/robot_sim --cov-report=term-missing --cov-report=json:coverage.json -q` with `fail_under = 80` + `python scripts/verify_partition_coverage.py --coverage-json coverage.json`',
    '- gui smoke: `python scripts/verify_gui_smoke.py`; the gate prefers real `PySide6` and falls back to the repository-local Qt test shim only inside the verification process so deterministic offscreen smoke remains executable in constrained environments. Evidence must retain `runtime_kind`, `gui_real_runtime_ok`, and `gui_shim_runtime_ok` so release review can distinguish shim smoke from a real GUI baseline',
    '- clean source bundle: `python scripts/package_release.py --output dist/source-release.zip --top-level-dir robot_sim_engine`; packaging now stages a writable clean-source mirror, regenerates checked-in contract docs inside the stage, re-verifies the staged tree, and refuses to ship stale contract surfaces from the caller working copy.',
    '- contract regeneration: `python scripts/regenerate_quality_contracts.py` + `python scripts/verify_docs_information_architecture.py` + `git diff --exit-code -- docs`; docs gate now enforces full explanatory-doc semantic coverage through doc-class policies plus file-specific semantic contracts',
)


def _front_matter(**values: str) -> str:
    lines = ['---']
    lines.extend(f'{key}: {value}' for key, value in values.items())
    lines.append('---')
    lines.append('')
    return '\n'.join(lines)


def _generated_doc(text: str, *, title: str) -> str:
    metadata = _front_matter(
        owner='quality',
        audience='maintainer',
        status='generated',
        source_of_truth='regenerated',
        generated_by='scripts/regenerate_quality_contracts.py',
        last_reviewed='2026-04-18',
    )
    return metadata + text


def _generated_entry_page(name: str) -> str:
    title = name[:-3].replace('_', ' ').title()
    canonical = f'docs/generated/{name}'
    metadata = _front_matter(
        owner='docs',
        audience='all',
        status='entry-page',
        source_of_truth='entry-point',
        canonical_target=canonical,
        last_reviewed='2026-04-18',
    )
    body = '\n'.join((
        f'# {title}',
        '',
        '本文件是稳定入口页。',
        '',
        f'- canonical generated doc: `{canonical}`',
        '- regeneration source: `python scripts/regenerate_quality_contracts.py`',
        '- editing policy: 请优先修改运行时真源，再执行 regeneration；不要直接把契约内容手写回入口页。',
        '',
        f'请跳转阅读：[`{canonical}`](generated/{name})',
        '',
    ))
    return metadata + body


@dataclass(frozen=True)
class QualityContractSnapshot:
    """Deterministic markdown/doc snapshot used by docs and regression checks."""

    quality_gates_markdown: str
    module_status_markdown: str
    capability_matrix_markdown: str
    exception_catch_matrix_markdown: str
    quality_evidence_markdown: str


class QualityContractService:
    """Render the doc snippets that define the project quality contract."""

    def __init__(
        self,
        *,
        runtime_feature_policy: RuntimeFeaturePolicy | None = None,
        capability_matrix_renderer: Callable[[], str] | None = None,
        module_status_renderer: Callable[[], str] | None = None,
        exception_catch_matrix_renderer: Callable[[], str] | None = None,
    ) -> None:
        self._runtime_feature_policy = runtime_feature_policy or RuntimeFeaturePolicy()
        self._capability_matrix_renderer = capability_matrix_renderer or CapabilityService(
            runtime_feature_policy=self._runtime_feature_policy,
        ).render_markdown
        self._module_status_renderer = module_status_renderer or ModuleStatusService(
            runtime_feature_policy=self._runtime_feature_policy,
        ).render_markdown
        self._exception_catch_matrix_renderer = exception_catch_matrix_renderer or render_exception_catch_matrix_markdown

    def snapshot(self) -> QualityContractSnapshot:
        """Return the current rendered documentation snapshot."""
        return QualityContractSnapshot(
            quality_gates_markdown=self.render_quality_gates_markdown(),
            module_status_markdown=self._module_status_renderer(),
            capability_matrix_markdown=self._capability_matrix_renderer(),
            exception_catch_matrix_markdown=self._exception_catch_matrix_renderer(),
            quality_evidence_markdown=self.render_quality_evidence_markdown(),
        )


    def render_quality_evidence_markdown(self) -> str:
        """Render the quality-evidence contract document.

        Returns:
            str: Markdown describing how executed quality evidence is collected and where
                CI writes reproducible evidence artifacts.
        """
        lines = [
            '# Quality Evidence',
            '',
            '- generated contract docs now live under `docs/generated/*.md`; root-level `docs/*.md` files remain stable entry pages.',
            '- executed quality evidence is written as JSON artifacts through `scripts/collect_quality_evidence.py`, `scripts/verify_module_governance.py --evidence-out`, and `scripts/verify_benchmark_matrix.py --evidence-out`.',
            '- `artifacts/release_manifest.json` is the canonical aggregated release-readiness summary; release review must evaluate `artifact_ready`, `environment_ready`, and `release_ready` together rather than treating executed artifacts alone as a sufficient release signal.',
            '- evidence artifacts must include a runtime fingerprint (python / platform / machine) so perf and governance results stay attributable to the environment that produced them.',
            '- evidence artifacts must also include a transportable source-tree fingerprint (`repo_root`, `source_tree_fingerprint`, `source_tree_file_count`, `generated_at_utc`); aggregation rejects mixed-source evidence by comparing the source-tree fingerprint + file count, while tolerating repository relocation after packaging.',
            '- GUI smoke evidence must preserve whether the verified runtime was real `PySide6` or the repository-local test shim; shim success is acceptable for constrained smoke coverage but does not satisfy the checked-in GUI release environment contract.',
            '- promotion and benchmark decisions should prefer executed evidence artifacts over static governance summaries whenever both are available.',
            '',
        ]
        return _generated_doc('\n'.join(lines), title='Quality Evidence')

    def render_quality_gates_markdown(self) -> str:
        """Render the quality-gates markdown document."""
        lines = ['# Quality Gates', '']
        lines.extend(QUALITY_GATE_LINES)
        lines.append('')
        return _generated_doc('\n'.join(lines), title='Quality Gates')




def _module_ast(path: Path) -> ast.AST:
    """Parse a module for structural contract verification."""
    return ast.parse(path.read_text(encoding='utf-8'))


def _class_function_names(module_ast: ast.AST, class_name: str) -> set[str]:
    names: set[str] = set()
    for node in ast.walk(module_ast):
        if isinstance(node, ast.ClassDef) and node.name == class_name:
            for item in node.body:
                if isinstance(item, ast.FunctionDef):
                    names.add(item.name)
    return names

def _generated_doc_paths(root: Path) -> dict[str, Path]:
    docs_generated_dir = root / 'docs' / 'generated'
    return {name: docs_generated_dir / name for name in GENERATED_DOC_NAMES}


def _generated_docs(snapshot: QualityContractSnapshot) -> dict[str, str]:
    return {
        'quality_gates.md': snapshot.quality_gates_markdown,
        'module_status.md': _generated_doc(snapshot.module_status_markdown, title='Module Status'),
        'capability_matrix.md': _generated_doc(snapshot.capability_matrix_markdown, title='Capability Matrix'),
        'exception_catch_matrix.md': _generated_doc(snapshot.exception_catch_matrix_markdown, title='Exception Catch Matrix'),
        'quality_evidence.md': snapshot.quality_evidence_markdown,
    }


def _legacy_entry_docs(root: Path) -> dict[Path, str]:
    return {root / rel_path: content for rel_path, content in render_entry_pages().items()}


def _expected_docs(root: Path, snapshot: QualityContractSnapshot) -> dict[Path, str]:
    generated_paths = _generated_doc_paths(root)
    expected = {generated_paths[name]: content for name, content in _generated_docs(snapshot).items()}
    expected.update(_legacy_entry_docs(root))
    return expected



def verify_behavior_contracts(project_root: str | Path) -> list[str]:
    """Verify runtime-facing behavior contracts that docs and CI promise.

    Args:
        project_root: Repository root containing checked-in configs and source files.

    Returns:
        list[str]: Human-readable contract violations. Empty when contracts hold.
    """
    root = Path(project_root)
    errors: list[str] = []

    from robot_sim.application.services.config_service import ConfigService

    checks = {
        'default': {'title': 'Robot Sim Engine', 'max_points': 5000, 'retry_count': 1, 'dt': 0.02},
        'dev': {'title': 'Robot Sim Engine [dev]', 'max_points': 7000, 'retry_count': 2, 'dt': 0.02},
        'ci': {'title': 'Robot Sim Engine [ci]', 'max_points': 2500, 'retry_count': 1, 'dt': 0.05},
        'research': {'title': 'Robot Sim Engine [research]', 'max_points': 8000, 'retry_count': 3, 'dt': 0.01},
    }
    for profile, expected in checks.items():
        service = ConfigService(root / 'configs', profile=profile)
        app_cfg = service.load_app_config()
        solver_cfg = service.load_solver_config()
        observed = {
            'title': app_cfg['window']['title'],
            'max_points': app_cfg['plots']['max_points'],
            'retry_count': solver_cfg['ik']['retry_count'],
            'dt': solver_cfg['trajectory']['dt'],
        }
        if observed != expected:
            errors.append(f'shipped profile drift for {profile}: expected {expected}, got {observed}')

    baseline_path = root / 'tests' / 'regression' / 'baselines' / 'scene_capture_snapshot_baseline.json'
    if not baseline_path.exists():
        errors.append('missing screenshot snapshot baseline fixture')

    importer_baseline_path = root / 'tests' / 'regression' / 'baselines' / 'importer_fidelity_baseline.json'
    if not importer_baseline_path.exists():
        errors.append('missing importer fidelity baseline fixture')

    compatibility_budget_path = root / 'configs' / 'compatibility_budget.yaml'
    if not compatibility_budget_path.exists():
        errors.append('missing compatibility budget config')

    compatibility_retirement_path = root / 'configs' / 'compatibility_retirement.yaml'
    if not compatibility_retirement_path.exists():
        errors.append('missing compatibility retirement config')

    compatibility_downstream_inventory_path = root / 'configs' / 'compatibility_downstream_inventory.yaml'
    if not compatibility_downstream_inventory_path.exists():
        errors.append('missing compatibility downstream inventory config')

    compatibility_support_boundary_path = root / 'docs' / 'compatibility_support_boundary.md'
    if not compatibility_support_boundary_path.exists():
        errors.append('missing compatibility support boundary doc')

    compatibility_downstream_inventory_doc_path = root / 'docs' / 'compatibility_downstream_inventory.md'
    if not compatibility_downstream_inventory_doc_path.exists():
        errors.append('missing compatibility downstream inventory doc')

    plugin_example_solver = root / 'examples' / 'plugins' / 'minimal_solver_plugin.py'
    plugin_example_importer = root / 'examples' / 'plugins' / 'minimal_importer_plugin.py'
    if not plugin_example_solver.exists() or not plugin_example_importer.exists():
        errors.append('public plugin SDK examples are missing')

    coordinator_dependency_markers = {
        'benchmark_task_coordinator.py': ('require_dependency(runtime,', 'require_dependency(benchmark,', 'require_dependency(threader,'),
        'export_task_coordinator.py': ('require_dependency(runtime,', 'require_dependency(export,', 'require_dependency(threader,', 'require_dependency(metrics_service,'),
        'ik_task_coordinator.py': ('require_dependency(solver,', 'require_dependency(threader,'),
        'playback_task_coordinator.py': ('require_dependency(runtime,', 'require_dependency(playback,', 'require_dependency(playback_threader,'),
        'robot_coordinator.py': ('require_dependency(robot,' ,),
        'scene_coordinator.py': ('require_dependency(runtime,', 'require_dependency(threader,'),
        'status_coordinator.py': ('require_dependency(runtime,',),
        'trajectory_task_coordinator.py': ('require_dependency(trajectory,', 'require_dependency(threader,'),
    }
    for filename, markers in coordinator_dependency_markers.items():
        coordinator_text = (root / 'src/robot_sim/presentation/coordinators' / filename).read_text(encoding='utf-8')
        for marker in markers:
            if marker not in coordinator_text:
                errors.append(f'coordinator explicit dependency contract missing in {filename}: {marker}')
        forbidden = ("getattr(window, 'runtime_facade'", "getattr(window, 'robot_facade'", "getattr(window, 'solver_facade'", "getattr(window, 'trajectory_facade'", "getattr(window, 'benchmark_facade'", "getattr(window, 'export_facade'", "getattr(window, 'playback_facade'", "getattr(window, 'threader'", "getattr(window, 'playback_threader'")
        for marker in forbidden:
            if marker in coordinator_text:
                errors.append(f'coordinator constructor still guesses dependencies in {filename}: {marker}')

    export_text = (root / 'src/robot_sim/presentation/coordinators/export_task_coordinator.py').read_text(encoding='utf-8')
    if 'ExportWorker(' not in export_text or "task_kind='export'" not in export_text:
        errors.append('export coordinator drifted away from background export worker lifecycle')

    scene_text = (root / 'src/robot_sim/presentation/coordinators/scene_coordinator.py').read_text(encoding='utf-8')
    if 'ScreenshotWorker(' not in scene_text or "task_kind='screenshot'" not in scene_text:
        errors.append('scene coordinator drifted away from background screenshot worker lifecycle')
    if 'capture_from_snapshot' not in scene_text or 'record_render_operation_span' not in scene_text:
        errors.append('scene coordinator no longer records screenshot render spans on the projection path')

    main_window_path = root / 'src/robot_sim/presentation/main_window.py'
    main_window_text = main_window_path.read_text(encoding='utf-8')
    if 'build_presentation_assembly(' not in main_window_text:
        errors.append('main window no longer builds through presentation assembly composition root')
    main_window_ast = _module_ast(main_window_path)
    main_window_functions = _class_function_names(main_window_ast, 'MainWindow')
    for required_property in ('runtime_services', 'workflow_services', 'task_orchestration'):
        if required_property not in main_window_functions:
            errors.append(f'main window runtime bundle contract missing property: {required_property}')
    if '_install_window_runtime_aliases' in main_window_functions:
        errors.append('main window still installs peer runtime aliases instead of grouped bundle properties')

    session_state_text = (root / 'src/robot_sim/model/session_state.py').read_text(encoding='utf-8')
    required_session_markers = (
        'render_runtime: RenderRuntimeState',
        'render_telemetry: tuple[RenderTelemetryEvent, ...]',
        'render_operation_spans: tuple[RenderOperationSpan, ...]',
        'render_sampling_counters: tuple[RenderSamplingCounter, ...]',
        'render_backend_performance: tuple[RenderBackendPerformanceTelemetry, ...]',
    )
    for marker, message in (
        (required_session_markers[0], 'session state no longer carries structured render runtime capability state'),
        (required_session_markers[1], 'session state no longer carries structured render telemetry event history'),
        (required_session_markers[2], 'session state no longer carries render operation spans'),
        (required_session_markers[3], 'session state no longer carries render sampling counters'),
        (required_session_markers[4], 'session state no longer carries backend-specific render performance telemetry'),
    ):
        if marker not in session_state_text:
            errors.append(message)

    telemetry_model_text = (root / 'src/robot_sim/model/render_telemetry_backend_record.py').read_text(encoding='utf-8')
    telemetry_wrapper_text = (root / 'src/robot_sim/model/render_telemetry.py').read_text(encoding='utf-8')
    backend_perf_text = (root / 'src/robot_sim/model/render_telemetry_backend_performance.py').read_text(encoding='utf-8')
    for marker, haystack, message in (
        ('latency_buckets: dict[str, int]', telemetry_model_text, 'render backend telemetry no longer tracks latency buckets'),
        ('duration_percentiles_ms: dict[str, float]', telemetry_model_text, 'render backend telemetry no longer tracks duration percentiles'),
        ('rolling_span_rate_per_sec: float', telemetry_model_text, 'render backend telemetry no longer tracks rolling-window span rate'),
        ('rolling_counter_throughput: dict[str, float]', telemetry_model_text, 'render backend telemetry no longer tracks backend-specific throughput'),
        ('live_counters: dict[str, float]', telemetry_model_text, 'render backend telemetry no longer tracks live counter values'),
        ('rebuild_backend_performance(', telemetry_wrapper_text, 'render backend telemetry no longer rebuilds rolling-window backend aggregates'),
        ("latency_bucket_label(", backend_perf_text, 'render backend telemetry no longer classifies span latency buckets'),
    ):
        if marker not in haystack:
            errors.append(message)

    state_store_text = (root / 'src/robot_sim/presentation/state_store.py').read_text(encoding='utf-8')
    state_store_api_text = (root / 'src/robot_sim/presentation/state_store_api.py').read_text(encoding='utf-8')
    state_segments_path = root / 'src/robot_sim/presentation/state_segments.py'
    state_segments_text = state_segments_path.read_text(encoding='utf-8')
    state_segments_ast = _module_ast(state_segments_path)
    render_state_functions = _class_function_names(state_segments_ast, 'RenderStateSegmentStore')
    if 'RenderTelemetryService' not in state_segments_text:
        errors.append('render state segment no longer delegates through RenderTelemetryService')
    if 'telemetry_service' not in render_state_functions:
        errors.append('render state segment no longer exposes the canonical telemetry_service property')
    required_state_store_markers = (
        'def patch_render_runtime(',
        'def patch_render_capability(',
        'def subscribe_render_telemetry(',
        'def subscribe_render_operation_spans(',
        'def subscribe_render_sampling_counters(',
        'def subscribe_render_backend_performance(',
        'def record_render_operation_span(',
        'def record_render_sampling_counter(',
        'def record_render_sampling_counters(',
    )
    for marker in required_state_store_markers:
        if marker not in state_store_text and marker not in state_store_api_text:
            errors.append(f'state store missing render telemetry contract marker: {marker}')

    ui_text = (root / 'src/robot_sim/presentation/main_window_ui.py').read_text(encoding='utf-8')
    if 'project_render_runtime_state(' not in ui_text or '_collect_render_runtime_state(' not in ui_text:
        errors.append('main window UI no longer projects render runtime capability state into the shared state store')
    if '_ensure_status_panel_projection_subscription(' not in ui_text or 'build_status_panel_projection' not in ui_text:
        errors.append('main window UI no longer binds the typed status-panel subscription flow for render runtime state')
    if '_ensure_render_telemetry_subscription(' not in ui_text or 'build_render_telemetry_panel_state' not in ui_text:
        errors.append('main window UI no longer binds the render telemetry stream into diagnostics projection')
    telemetry_state_text = (root / 'src/robot_sim/presentation/render_telemetry_state.py').read_text(encoding='utf-8')
    if 'backend_latency_summary' not in telemetry_state_text:
        errors.append('render telemetry projection no longer exposes backend latency summaries')
    if 'backend_percentile_summary' not in telemetry_state_text:
        errors.append('render telemetry projection no longer exposes backend percentile summaries')
    if 'backend_rolling_summary' not in telemetry_state_text:
        errors.append('render telemetry projection no longer exposes rolling-window summaries')
    if 'timeline_summary' not in telemetry_state_text or 'RenderTimelineEntryView' not in telemetry_state_text:
        errors.append('render telemetry projection no longer exposes the diagnostics timeline view')
    if 'backend_live_counter_summary' not in telemetry_state_text:
        errors.append('render telemetry projection no longer exposes backend live counter summaries')
    if 'runtime_probe' not in ui_text or 'record_render_operation_span(' not in ui_text:
        errors.append('main window UI no longer emits runtime probe spans for render capability scans')

    return errors


def write_quality_contract_files(project_root: str | Path) -> None:
    """Regenerate checked-in contract docs from runtime truth sources."""
    root = Path(project_root)
    snapshot = _build_runtime_truth_quality_service(root).snapshot()
    for path, content in _expected_docs(root, snapshot).items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding='utf-8')


def verify_quality_contract_files(project_root: str | Path) -> list[str]:
    """Verify generated contract documents against checked-in copies."""
    root = Path(project_root)
    snapshot = _build_runtime_truth_quality_service(root).snapshot()
    errors: list[str] = []

    for path, expected in _expected_docs(root, snapshot).items():
        if not path.exists():
            errors.append(f'missing contract doc: {path.relative_to(root)}')
            continue
        actual = path.read_text(encoding='utf-8')
        if actual.strip() != expected.strip():
            errors.append(f'contract doc out of date: {path.relative_to(root)}')

    errors.extend(verify_exception_catch_matrix(root))
    errors.extend(verify_behavior_contracts(root))
    errors.extend(verify_docs_information_architecture(root))

    workflow_path = root / '.github' / 'workflows' / 'ci.yml'
    workflow = ''
    if workflow_path.exists():
        workflow = workflow_path.read_text(encoding='utf-8')
        required_markers = (
            'runtime_contracts:',
            'governance_evidence:',
            'unit_regression:',
            'full_validation:',
            'gui_smoke:',
            'python scripts/verify_runtime_contracts.py --mode headless --check-packaged-configs',
            'python scripts/verify_compatibility_budget.py --scenario clean_headless_mainline',
            'python scripts/verify_perf_budget_config.py',
            'python scripts/verify_gui_smoke.py',
            'python scripts/verify_runtime_baseline.py --mode release',
            'python scripts/regenerate_quality_contracts.py',
            'git diff --exit-code -- docs',
            'pytest tests/unit tests/regression -q',
            'python scripts/verify_module_governance.py --execute-gates --evidence-out artifacts/module_governance_evidence.json',
            'python scripts/verify_benchmark_matrix.py --execute-gates --execute --evidence-out artifacts/benchmark_matrix_evidence.json',
            'python scripts/regenerate_importer_fidelity_baseline.py',
            'pytest --cov=src/robot_sim --cov-report=term-missing --cov-report=json:coverage.json -q',
            'python scripts/verify_partition_coverage.py --coverage-json coverage.json',
            'pytest tests/gui -q',
            'python scripts/package_release.py --output dist/source-release.zip --top-level-dir robot_sim_engine',
        )
        for marker in required_markers:
            if marker not in workflow:
                errors.append(f'workflow missing marker: {marker}')
    else:
        errors.append('missing workflow: .github/workflows/ci.yml')

    readme_path = root / 'README.md'
    readme = ''
    if readme_path.exists():
        readme = readme_path.read_text(encoding='utf-8')
        readme_markers = (
            '当前测试基线：**以 CI / pytest 实际收集结果为准**',
            'release blockers',
            'release blockers',
            'runtime contracts',
            'governance evidence',
            'unit/regression',
            'full validation',
            'gui smoke',
            'shipped behavior contracts',
            'python scripts/regenerate_importer_fidelity_baseline.py',
            'verify_release_blockers.py',
            'verify_runtime_gate_layer.py',
            'verify_governance_gate_layer.py',
            'verify_runtime_contracts.py --mode headless --check-packaged-configs',
            'verify_compatibility_budget.py --scenario clean_headless_mainline',
            'verify_gui_smoke.py',
            'regenerate_quality_contracts.py',
            'package_release.py --output dist/source-release.zip --top-level-dir robot_sim_engine',
            'research.yaml',
        )
        for marker in readme_markers:
            if marker not in readme:
                errors.append(f'README missing marker: {marker}')
    else:
        errors.append('missing README.md')

    pyproject = root / 'pyproject.toml'
    if pyproject.exists():
        data = tomllib.loads(pyproject.read_text(encoding='utf-8'))
        pytest_fail_under = data.get('tool', {}).get('pytest', {}).get('ini_options', {}).get('cov_fail_under')
        coverage_fail_under = data.get('tool', {}).get('coverage', {}).get('report', {}).get('fail_under')
        fail_under = coverage_fail_under if coverage_fail_under is not None else pytest_fail_under
        if fail_under is None:
            errors.append('coverage floor is missing from pyproject.toml')
        elif int(fail_under) < 80:
            errors.append('coverage floor drifted below 80')
    else:
        errors.append('missing pyproject.toml')

    return errors
