from __future__ import annotations

import subprocess
import sys


def test_verify_compatibility_budget_clean_bootstrap(project_root):
    result = subprocess.run(
        [sys.executable, str(project_root / 'scripts' / 'verify_compatibility_budget.py'), '--scenario', 'clean_bootstrap'],
        cwd=project_root,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert 'compatibility budget verified for clean_bootstrap' in result.stdout
