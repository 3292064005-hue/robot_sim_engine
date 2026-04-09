#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path
import sys


def _repo_src_root() -> Path:
    return Path(__file__).resolve().parents[1] / 'src'


sys.path.insert(0, str(_repo_src_root()))

from robot_sim.application.services.perf_budget_service import PerfBudgetService


_REQUIRED_KEYS = {
    'ci': ('ik_planar_smoke', 'ik_planar_default_suite', 'trajectory_plan_smoke', 'render_snapshot_capture'),
    'release': ('ik_planar_smoke', 'ik_planar_default_suite', 'trajectory_plan_smoke', 'render_snapshot_capture'),
}


def main() -> int:
    parser = argparse.ArgumentParser(description='Verify checked-in performance budget config structure.')
    parser.add_argument('--project-root', default='.', help='Repository root containing configs/perf_budgets.yaml')
    args = parser.parse_args()

    service = PerfBudgetService.from_repo_root(Path(args.project_root))
    errors: list[str] = []
    for profile, keys in _REQUIRED_KEYS.items():
        for key in keys:
            try:
                budget = service.budget(key, profile=profile)
            except Exception as exc:  # pragma: no cover - script entrypoint
                errors.append(f'missing budget profile={profile} key={key}: {exc}')
                continue
            if not budget:
                errors.append(f'empty budget profile={profile} key={key}')
    if errors:
        for item in errors:
            print(item)
        return 1
    print('performance budget config verified')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
