from __future__ import annotations

import ast
from dataclasses import dataclass
from pathlib import Path


IMPORT_GUARD_ALLOWLIST: dict[str, str] = {
<<<<<<< HEAD
=======
    'src/robot_sim/application/workers/base.py': 'Qt worker compatibility shim',
    'src/robot_sim/presentation/playback_render_scheduler.py': 'Qt timer compatibility shim',
    'src/robot_sim/presentation/thread_orchestrator.py': 'Qt thread compatibility shim',
>>>>>>> 3ed78e647985c6d680c085e4480d898855278db3
    'src/robot_sim/presentation/main_window.py': 'GUI entry import gate',
    'src/robot_sim/presentation/main_window_ui.py': 'GUI widget import gate',
    'src/robot_sim/presentation/widgets/benchmark_panel.py': 'optional Qt widgets',
    'src/robot_sim/presentation/widgets/collision_panel.py': 'optional Qt widgets',
<<<<<<< HEAD
    'src/robot_sim/presentation/experimental/widgets/collision_panel.py': 'optional Qt widgets',
    'src/robot_sim/presentation/widgets/diagnostics_panel.py': 'optional Qt widgets',
    'src/robot_sim/presentation/widgets/export_panel.py': 'optional Qt widgets',
    'src/robot_sim/presentation/experimental/widgets/export_panel.py': 'optional Qt widgets',
=======
    'src/robot_sim/presentation/widgets/diagnostics_panel.py': 'optional Qt widgets',
    'src/robot_sim/presentation/widgets/export_panel.py': 'optional Qt widgets',
>>>>>>> 3ed78e647985c6d680c085e4480d898855278db3
    'src/robot_sim/presentation/widgets/playback_panel.py': 'optional Qt widgets',
    'src/robot_sim/presentation/widgets/plots_panel.py': 'optional Qt widgets',
    'src/robot_sim/presentation/widgets/robot_config_panel.py': 'optional Qt widgets',
    'src/robot_sim/presentation/widgets/scene_options_panel.py': 'optional Qt widgets',
<<<<<<< HEAD
    'src/robot_sim/presentation/experimental/widgets/scene_options_panel.py': 'optional Qt widgets',
=======
>>>>>>> 3ed78e647985c6d680c085e4480d898855278db3
    'src/robot_sim/presentation/widgets/scene_toolbar.py': 'optional Qt widgets',
    'src/robot_sim/presentation/widgets/solver_panel.py': 'optional Qt widgets',
    'src/robot_sim/presentation/widgets/status_panel.py': 'optional Qt widgets',
    'src/robot_sim/presentation/widgets/target_pose_panel.py': 'optional Qt widgets',
<<<<<<< HEAD
=======
    'src/robot_sim/presentation/models/dh_table_model.py': 'optional Qt model classes',
    'src/robot_sim/presentation/models/joint_limit_table_model.py': 'optional Qt model classes',
    'src/robot_sim/presentation/models/robot_library_model.py': 'optional Qt model classes',
>>>>>>> 3ed78e647985c6d680c085e4480d898855278db3
    'src/robot_sim/render/plots_manager.py': 'optional plotting backend',
    'src/robot_sim/render/scene_3d_widget.py': 'optional 3D backend',
}

RUNTIME_CATCH_ALLOWLIST: dict[str, tuple[int, str]] = {
    'src/robot_sim/app/bootstrap.py': (1, 'process bootstrap defensive logging boundary'),
    'src/robot_sim/app/main.py': (1, 'process entry defensive logging boundary'),
    'src/robot_sim/application/workers/benchmark_worker.py': (1, 'worker error projection boundary'),
    'src/robot_sim/application/workers/export_worker.py': (1, 'worker error projection boundary'),
    'src/robot_sim/application/workers/fk_worker.py': (1, 'worker error projection boundary'),
    'src/robot_sim/application/workers/ik_worker.py': (1, 'worker error projection boundary'),
    'src/robot_sim/application/workers/playback_worker.py': (1, 'worker error projection boundary'),
    'src/robot_sim/application/workers/screenshot_worker.py': (1, 'worker error projection boundary'),
    'src/robot_sim/application/workers/trajectory_worker.py': (1, 'worker error projection boundary'),
    'src/robot_sim/presentation/coordinators/_helpers.py': (1, 'centralized coordinator presentation boundary'),
    'src/robot_sim/presentation/error_boundary.py': (2, 'centralized GUI presentation boundary'),
<<<<<<< HEAD
    'src/robot_sim/presentation/threading/worker_binding.py': (1, 'worker thread cleanup defensive boundary'),
}

SPECIFIC_CATCH_ALLOWLIST: dict[str, tuple[tuple[str, ...], ...]] = {
    'src/robot_sim/render/scene_3d_widget.py': (
        ('ImportError',),
        ('AttributeError', 'RuntimeError', 'TypeError', 'ValueError', 'OSError'),
        ('TypeError',),
        ('AttributeError', 'RuntimeError', 'ValueError'),
        ('TypeError', 'ValueError'),
    ),
    'src/robot_sim/render/plots_manager.py': (
        ('ImportError',),
        ('AttributeError', 'RuntimeError', 'TypeError', 'ValueError'),
        ('AttributeError', 'RuntimeError', 'TypeError', 'ValueError'),
        ('AttributeError', 'RuntimeError', 'TypeError', 'ValueError'),
        ('AttributeError', 'RuntimeError', 'TypeError', 'ValueError'),
        ('AttributeError', 'RuntimeError', 'TypeError', 'ValueError'),
    ),
    'src/robot_sim/render/actor_manager.py': (
        ('AttributeError', 'RuntimeError', 'TypeError', 'ValueError'),
    ),
=======
    'src/robot_sim/render/actor_manager.py': (1, 'render actor cleanup compatibility boundary'),
    'src/robot_sim/render/plots_manager.py': (3, 'plot backend compatibility boundary'),
    'src/robot_sim/render/scene_3d_widget.py': (3, '3D backend compatibility boundary'),
>>>>>>> 3ed78e647985c6d680c085e4480d898855278db3
}


@dataclass(frozen=True)
class ExceptionCatchSite:
<<<<<<< HEAD
    """Structured record describing an exception-catching site."""
=======
    """Structured record describing a broad ``except Exception`` site."""
>>>>>>> 3ed78e647985c6d680c085e4480d898855278db3

    path: str
    line: int
    category: str
    context: str
<<<<<<< HEAD
    exception_types: tuple[str, ...]
=======
>>>>>>> 3ed78e647985c6d680c085e4480d898855278db3


class _ExceptionCatchVisitor(ast.NodeVisitor):
    def __init__(self) -> None:
        self.sites: list[ExceptionCatchSite] = []
        self._context_stack: list[str] = []

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:  # noqa: N802
        self._context_stack.append(node.name)
        self.generic_visit(node)
        self._context_stack.pop()

    visit_AsyncFunctionDef = visit_FunctionDef

    def visit_ClassDef(self, node: ast.ClassDef) -> None:  # noqa: N802
        self._context_stack.append(node.name)
        self.generic_visit(node)
        self._context_stack.pop()

    def visit_ExceptHandler(self, node: ast.ExceptHandler) -> None:  # noqa: N802
<<<<<<< HEAD
        category = 'runtime' if self._context_stack else 'import_guard'
        context = '.'.join(self._context_stack) if self._context_stack else '<module>'
        exception_types = self._normalize_exception_types(node.type)
        self.sites.append(
            ExceptionCatchSite(
                path='',
                line=int(node.lineno),
                category=category,
                context=context,
                exception_types=exception_types,
            )
        )
        self.generic_visit(node)

    @staticmethod
    def _normalize_exception_types(node: ast.expr | None) -> tuple[str, ...]:
        if node is None:
            return ('<bare>',)
        if isinstance(node, ast.Name):
            return (node.id,)
        if isinstance(node, ast.Tuple):
            items: list[str] = []
            for element in node.elts:
                if isinstance(element, ast.Name):
                    items.append(element.id)
                else:
                    items.append(ast.unparse(element))
            return tuple(items)
        return (ast.unparse(node),)

=======
        if isinstance(node.type, ast.Name) and node.type.id == 'Exception':
            category = 'runtime' if self._context_stack else 'import_guard'
            context = '.'.join(self._context_stack) if self._context_stack else '<module>'
            self.sites.append(ExceptionCatchSite(path='', line=int(node.lineno), category=category, context=context))
        self.generic_visit(node)

>>>>>>> 3ed78e647985c6d680c085e4480d898855278db3

def _project_root_from_here() -> Path:
    return Path(__file__).resolve().parents[3]


def iter_exception_catch_sites(project_root: str | Path | None = None) -> tuple[ExceptionCatchSite, ...]:
<<<<<<< HEAD
    """Return all exception-catching sites under ``src/robot_sim``."""
=======
    """Return all broad ``except Exception`` sites under ``src/robot_sim``."""
>>>>>>> 3ed78e647985c6d680c085e4480d898855278db3
    root = Path(project_root) if project_root is not None else _project_root_from_here()
    src_root = root / 'src' / 'robot_sim'
    sites: list[ExceptionCatchSite] = []
    for path in sorted(src_root.rglob('*.py')):
        tree = ast.parse(path.read_text(encoding='utf-8'))
        visitor = _ExceptionCatchVisitor()
        visitor.visit(tree)
        rel_path = str(path.relative_to(root))
        for site in visitor.sites:
<<<<<<< HEAD
            sites.append(
                ExceptionCatchSite(
                    path=rel_path,
                    line=site.line,
                    category=site.category,
                    context=site.context,
                    exception_types=site.exception_types,
                )
            )
=======
            sites.append(ExceptionCatchSite(path=rel_path, line=site.line, category=site.category, context=site.context))
>>>>>>> 3ed78e647985c6d680c085e4480d898855278db3
    return tuple(sites)


def verify_exception_catch_matrix(project_root: str | Path | None = None) -> list[str]:
<<<<<<< HEAD
    """Verify that exception catches stay within the approved matrix."""
    errors: list[str] = []
    runtime_counts: dict[str, int] = {}
    specific_by_path: dict[str, list[ExceptionCatchSite]] = {}
    for site in iter_exception_catch_sites(project_root):
        if site.exception_types == ('Exception',):
            if site.category == 'runtime':
                runtime_counts[site.path] = runtime_counts.get(site.path, 0) + 1
                if site.path not in RUNTIME_CATCH_ALLOWLIST:
                    errors.append(f'unapproved runtime except Exception: {site.path}:{site.line} ({site.context})')
            else:
                if site.path not in IMPORT_GUARD_ALLOWLIST:
                    errors.append(f'unapproved import-guard except Exception: {site.path}:{site.line}')
        if site.path in SPECIFIC_CATCH_ALLOWLIST:
            specific_by_path.setdefault(site.path, []).append(site)
=======
    """Verify that broad exception catches stay within the approved matrix."""
    errors: list[str] = []
    runtime_counts: dict[str, int] = {}
    import_guard_counts: dict[str, int] = {}
    for site in iter_exception_catch_sites(project_root):
        if site.category == 'runtime':
            runtime_counts[site.path] = runtime_counts.get(site.path, 0) + 1
            if site.path not in RUNTIME_CATCH_ALLOWLIST:
                errors.append(f'unapproved runtime except Exception: {site.path}:{site.line} ({site.context})')
        else:
            import_guard_counts[site.path] = import_guard_counts.get(site.path, 0) + 1
            if site.path not in IMPORT_GUARD_ALLOWLIST:
                errors.append(f'unapproved import-guard except Exception: {site.path}:{site.line}')
>>>>>>> 3ed78e647985c6d680c085e4480d898855278db3

    for path, (expected_count, _reason) in RUNTIME_CATCH_ALLOWLIST.items():
        actual = runtime_counts.get(path, 0)
        if actual != expected_count:
            errors.append(f'runtime except Exception drift for {path}: expected {expected_count}, got {actual}')
<<<<<<< HEAD

    for path, expected_sequences in SPECIFIC_CATCH_ALLOWLIST.items():
        actual_sites = specific_by_path.get(path, [])
        actual_sequences = tuple(site.exception_types for site in actual_sites)
        if actual_sequences != expected_sequences:
            errors.append(
                'specific exception drift for '
                f'{path}: expected {expected_sequences}, got {actual_sequences}'
            )
=======
>>>>>>> 3ed78e647985c6d680c085e4480d898855278db3
    return errors


def render_exception_catch_matrix_markdown(project_root: str | Path | None = None) -> str:
<<<<<<< HEAD
    """Render deterministic markdown describing approved exception boundaries."""
    sites = iter_exception_catch_sites(project_root)
    runtime_by_path: dict[str, list[ExceptionCatchSite]] = {}
    import_guard_by_path: dict[str, list[ExceptionCatchSite]] = {}
    specific_by_path: dict[str, list[ExceptionCatchSite]] = {}
    for site in sites:
        if site.exception_types == ('Exception',):
            bucket = runtime_by_path if site.category == 'runtime' else import_guard_by_path
            bucket.setdefault(site.path, []).append(site)
        if site.path in SPECIFIC_CATCH_ALLOWLIST:
            specific_by_path.setdefault(site.path, []).append(site)
=======
    """Render deterministic markdown describing allowed broad exception boundaries."""
    sites = iter_exception_catch_sites(project_root)
    runtime_by_path: dict[str, list[ExceptionCatchSite]] = {}
    import_guard_by_path: dict[str, list[ExceptionCatchSite]] = {}
    for site in sites:
        bucket = runtime_by_path if site.category == 'runtime' else import_guard_by_path
        bucket.setdefault(site.path, []).append(site)
>>>>>>> 3ed78e647985c6d680c085e4480d898855278db3

    lines = ['# Exception Catch Matrix', '', '## runtime_boundaries']
    for path in sorted(RUNTIME_CATCH_ALLOWLIST):
        expected_count, reason = RUNTIME_CATCH_ALLOWLIST[path]
        site_lines = ', '.join(str(site.line) for site in runtime_by_path.get(path, ())) or '-'
        lines.append(f'- `{path}`')
        lines.append(f'  - allowed_count: `{expected_count}`')
        lines.append(f'  - lines: `{site_lines}`')
        lines.append(f'  - reason: `{reason}`')
    lines.extend(['', '## import_guards'])
    for path in sorted(IMPORT_GUARD_ALLOWLIST):
        site_lines = ', '.join(str(site.line) for site in import_guard_by_path.get(path, ())) or '-'
        lines.append(f'- `{path}`')
        lines.append(f'  - lines: `{site_lines}`')
        lines.append(f"  - reason: `{IMPORT_GUARD_ALLOWLIST[path]}`")
<<<<<<< HEAD
    lines.extend(['', '## specific_type_boundaries'])
    for path in sorted(SPECIFIC_CATCH_ALLOWLIST):
        lines.append(f'- `{path}`')
        path_sites = specific_by_path.get(path, ())
        if not path_sites:
            lines.append('  - line `-`: `-`')
            continue
        for site in path_sites:
            types = ', '.join(site.exception_types)
            lines.append(f'  - line `{site.line}`: `{types}` ({site.context})')
=======
>>>>>>> 3ed78e647985c6d680c085e4480d898855278db3
    lines.append('')
    return '\n'.join(lines)
