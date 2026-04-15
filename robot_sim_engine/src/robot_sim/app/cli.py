from __future__ import annotations

import argparse
import json
from pathlib import Path

from robot_sim.app.bootstrap import bootstrap
from robot_sim.app.main import main as gui_main
from robot_sim.app.runtime_paths import resolve_runtime_paths


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog='robot-sim', description='Robot Sim Engine command-line entrypoint')
    sub = parser.add_subparsers(dest='command', required=False)

    sub.add_parser('gui', help='launch the Qt GUI')
    sub.add_parser('runtime-summary', help='print the startup/runtime summary as JSON')
    sub.add_parser('source-layout-smoke', help='print source-layout discovery/runtime-path diagnostics as JSON')

    config = sub.add_parser('config-snapshot', help='print the resolved app/solver config snapshot as JSON')
    config.add_argument('--output', type=Path, default=None, help='optional JSON output path')
    return parser


def main(argv: list[str] | None = None) -> int:
    """Run the canonical robot-sim CLI.

    Args:
        argv: Optional explicit argv vector.

    Returns:
        int: Process exit code.

    Raises:
        None: Command failures are converted into exit codes by downstream entrypoints.
    """
    parser = _build_parser()
    args = parser.parse_args(argv)
    command = args.command or 'gui'
    if command == 'gui':
        return int(gui_main())
    if command == 'source-layout-smoke':
        runtime_paths = resolve_runtime_paths(create_dirs=False)
        payload = {
            'project_root': str(runtime_paths.project_root),
            'resource_root': str(runtime_paths.resource_root),
            'config_root': str(runtime_paths.config_root),
            'robot_root': str(runtime_paths.robot_root),
            'bundled_robot_root': str(runtime_paths.bundled_robot_root),
            'profiles_root': str(runtime_paths.profiles_root),
            'plugin_manifest_path': str(runtime_paths.plugin_manifest_path),
            'export_root': str(runtime_paths.export_root),
            'layout_mode': runtime_paths.layout_mode,
            'source_layout_available': bool(runtime_paths.source_layout_available),
            'entrypoint_mode': 'python -m robot_sim.app.cli',
            'cwd': str(Path.cwd()),
            'side_effect_free_probe': True,
        }
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0
    context = bootstrap(startup_mode='headless')
    if command == 'runtime-summary':
        print(json.dumps(dict(context.container.startup_summary or {}), ensure_ascii=False, indent=2))
        return 0
    if command == 'config-snapshot':
        snapshot = context.container.config_service.describe_effective_snapshot()
        payload = json.dumps(snapshot, ensure_ascii=False, indent=2)
        if args.output is not None:
            output_path = Path(args.output)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(payload + '\n', encoding='utf-8')
        else:
            print(payload)
        return 0
    parser.error(f'unsupported command: {command}')
    return 2


if __name__ == '__main__':  # pragma: no cover
    raise SystemExit(main())
