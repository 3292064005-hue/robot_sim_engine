from __future__ import annotations

import argparse
import json
from pathlib import Path

from robot_sim.app.bootstrap import bootstrap
from robot_sim.app.headless_api import HeadlessError, HeadlessExecutionError, HeadlessRequestError, HeadlessWorkflowService, load_request_payload
from robot_sim.app.main import main as gui_main
from robot_sim.app.runtime_paths import resolve_runtime_paths


def _add_output_argument(parser: argparse.ArgumentParser) -> None:
    parser.add_argument('--output', type=Path, default=None, help='optional JSON output path')


def _add_request_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument('--request-file', type=Path, default=None, help='JSON/YAML request payload path')
    parser.add_argument('--request-json', default=None, help='inline JSON request payload')
    _add_output_argument(parser)


def _emit_payload(payload: dict[str, object], *, output: Path | None) -> None:
    body = json.dumps(payload, ensure_ascii=False, indent=2)
    if output is None:
        print(body)
        return
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(body + '\n', encoding='utf-8')


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog='robot-sim', description='Robot Sim Engine command-line entrypoint')
    sub = parser.add_subparsers(dest='command', required=False)

    sub.add_parser('gui', help='launch the Qt GUI')
    sub.add_parser('runtime-summary', help='print the startup/runtime summary as JSON')
    sub.add_parser('source-layout-smoke', help='print source-layout discovery/runtime-path diagnostics as JSON')

    config = sub.add_parser('config-snapshot', help='print the resolved app/solver config snapshot as JSON')
    _add_output_argument(config)

    batch = sub.add_parser('batch', help='run one headless workflow command using a machine-readable contract')
    batch_sub = batch.add_subparsers(dest='batch_command', required=True)
    for name in ('import', 'fk', 'ik', 'plan', 'validate', 'benchmark', 'export-session', 'export-package'):
        cmd = batch_sub.add_parser(name, help=f'run the {name} headless workflow contract')
        _add_request_arguments(cmd)
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
            'entrypoint_mode': 'python robot_sim_cli.py',
            'cwd': str(Path.cwd()),
            'side_effect_free_probe': True,
        }
        _emit_payload(payload, output=None)
        return 0
    if command == 'batch':
        try:
            request = load_request_payload(request_file=args.request_file, request_json=args.request_json)
            context = bootstrap(startup_mode='headless')
            result = HeadlessWorkflowService(context.container).execute(str(args.batch_command), request)
            _emit_payload({'ok': True, 'command': str(args.batch_command), 'result': result}, output=args.output)
            return 0
        except (HeadlessError, OSError, ValueError) as exc:
            error = exc if isinstance(exc, HeadlessError) else HeadlessExecutionError(f'failed to write output payload: {exc}')
            _emit_payload(
                {
                    'ok': False,
                    'command': str(args.batch_command),
                    'error_type': error.__class__.__name__,
                    'message': str(error),
                },
                output=None,
            )
            return 1
    context = bootstrap(startup_mode='headless')
    if command == 'runtime-summary':
        _emit_payload(dict(context.container.startup_summary or {}), output=None)
        return 0
    if command == 'config-snapshot':
        snapshot = context.container.bootstrap_bundle.services.config_service.describe_effective_snapshot()
        _emit_payload(snapshot, output=args.output)
        return 0
    parser.error(f'unsupported command: {command}')
    return 2


if __name__ == '__main__':  # pragma: no cover
    raise SystemExit(main())
