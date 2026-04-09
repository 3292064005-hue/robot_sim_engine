from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path


def _load_baseline_builder(project_root: Path):
    module_path = project_root / 'scripts' / 'regenerate_importer_fidelity_baseline.py'
    spec = importlib.util.spec_from_file_location('regenerate_importer_fidelity_baseline', module_path)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None and spec.loader is not None
    sys.modules.setdefault('regenerate_importer_fidelity_baseline', module)
    spec.loader.exec_module(module)
    return module.build_baseline


def test_importer_fidelity_baseline_matches_checked_in_fixture(project_root):
    baseline_path = project_root / 'tests' / 'regression' / 'baselines' / 'importer_fidelity_baseline.json'
    expected = json.loads(baseline_path.read_text(encoding='utf-8'))
    build_baseline = _load_baseline_builder(project_root)
    observed = build_baseline(project_root)
    assert observed == expected
