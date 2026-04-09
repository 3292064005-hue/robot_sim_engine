from __future__ import annotations

import nox


@nox.session(reuse_venv=True)
def quick_quality(session: nox.Session) -> None:
    """Run the fast headless quality gate used during local iteration."""
    session.install('-e', '.[dev]')
    session.run('python', 'scripts/verify_quality_contracts.py')
    session.run('python', 'scripts/verify_runtime_baseline.py', '--mode', 'headless')
    session.run('pytest', 'tests/unit', 'tests/regression', '-q')


@nox.session(reuse_venv=True)
def gui_smoke(session: nox.Session) -> None:
    """Run the lightweight GUI smoke gate on environments with Qt dependencies."""
    session.install('-e', '.[dev,gui]')
    session.run('pytest', 'tests/gui', '-q')
