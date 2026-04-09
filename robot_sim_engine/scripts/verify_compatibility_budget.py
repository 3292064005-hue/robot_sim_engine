from __future__ import annotations

import argparse
import sys
from pathlib import Path


def _configure_path() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    src_root = repo_root / 'src'
    if str(src_root) not in sys.path:
        sys.path.insert(0, str(src_root))


_configure_path()

from robot_sim.app.bootstrap import bootstrap  # noqa: E402
from robot_sim.infra.compatibility_budget import evaluate_compatibility_budget, load_compatibility_budgets  # noqa: E402
from robot_sim.infra.compatibility_usage import compatibility_usage_counts, reset_compatibility_usage_counts  # noqa: E402
from robot_sim.presentation.controllers.robot_controller import RobotController  # noqa: E402
from robot_sim.presentation.state_store import StateStore  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[1]


def _run_clean_bootstrap() -> None:
    context = bootstrap(startup_mode='headless')
    assert context.container.runtime_context['config_root']
    assert context.container.runtime_context['robot_root']


def _run_clean_headless_mainline() -> None:
    context = bootstrap(startup_mode='headless')
    container = context.container
    store = StateStore()
    controller = RobotController(
        store,
        container.robot_registry,
        container.fk_uc,
        import_robot_uc=container.import_robot_uc,
    )
    controller.load_robot('planar_2dof')
    assert store.state.robot_spec is not None
    assert store.state.robot_spec.name == 'planar_2dof'


_SCENARIOS = {
    'clean_bootstrap': _run_clean_bootstrap,
    'clean_headless_mainline': _run_clean_headless_mainline,
}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description='Verify runtime compatibility usage stays within the configured budget.')
    parser.add_argument('--root', type=Path, default=REPO_ROOT, help='Repository root containing configs/compatibility_budget.yaml')
    parser.add_argument('--scenario', choices=tuple(_SCENARIOS), default='clean_headless_mainline')
    args = parser.parse_args(argv)

    budgets = load_compatibility_budgets(args.root / 'configs' / 'compatibility_budget.yaml')
    budget = budgets[args.scenario]
    reset_compatibility_usage_counts()
    _SCENARIOS[args.scenario]()
    report = evaluate_compatibility_budget(
        scenario=args.scenario,
        observed_counts=compatibility_usage_counts(),
        budget=budget,
    )
    if report.ok:
        print(f'compatibility budget verified for {args.scenario}')
        return 0
    for item in report.violations:
        print(item)
    return 1


if __name__ == '__main__':
    raise SystemExit(main())
