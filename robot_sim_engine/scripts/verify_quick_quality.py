from __future__ import annotations

import argparse
import importlib.util
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / 'src'
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))


def _run(command: list[str]) -> int:
    print('RUN:', ' '.join(command))
    completed = subprocess.run(command, cwd=REPO_ROOT, check=False)
    return int(completed.returncode)


def _module_available(module_name: str) -> bool:
    return importlib.util.find_spec(module_name) is not None


def main() -> int:
    parser = argparse.ArgumentParser(description='Run the quick-quality gate with tool-aware fallbacks so the gate remains executable in constrained CI/audit environments.')
    parser.add_argument('--skip-mypy-fallback-tests', action='store_true', help='Skip the typed-surface fallback tests used when mypy is unavailable.')
    args = parser.parse_args()

    # ruff or fallback compileall
    if _module_available('ruff'):
        if _run([sys.executable, '-m', 'ruff', 'check', 'src', 'tests']) != 0:
            return 1
    else:
        if _run([sys.executable, '-m', 'compileall', '-q', 'src', 'tests', 'scripts']) != 0:
            return 1

    # mypy or fallback typed-surface smoke tests
    if _module_available('mypy'):
        if _run([sys.executable, '-m', 'mypy']) != 0:
            return 1
    elif not bool(args.skip_mypy_fallback_tests):
        fallback_targets = [
            'tests/unit/test_qt_boundary_contracts.py',
            'tests/unit/test_quality_evidence_scripts.py',
            'tests/unit/test_collision_fidelity_surface.py',
            'tests/unit/test_perf_budget_environment_overrides.py',
        ]
        if _run([sys.executable, '-m', 'pytest', '-q', *fallback_targets]) != 0:
            return 1

    if _run([sys.executable, 'scripts/verify_quality_contracts.py']) != 0:
        return 1

    print('quick quality verified')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
