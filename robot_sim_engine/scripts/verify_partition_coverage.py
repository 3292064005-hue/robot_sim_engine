#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

import yaml


def _covered_fraction(summary: dict[str, object], file_payload: dict[str, object]) -> tuple[int, int]:
    covered = int(summary.get('covered_lines', 0) or 0)
    missing = int(summary.get('missing_lines', 0) or 0)
    total = covered + missing
    if total > 0:
        return covered, total
    executed = len(file_payload.get('executed_lines', []) or [])
    missing_lines = len(file_payload.get('missing_lines', []) or [])
    total = executed + missing_lines
    return executed, total


def main() -> int:
    parser = argparse.ArgumentParser(description='Verify partition coverage against checked-in minima.')
    parser.add_argument('--coverage-json', required=True, help='coverage.py JSON report path')
    parser.add_argument('--project-root', default='.', help='Repository root containing configs/coverage_partitions.yaml')
    args = parser.parse_args()

    project_root = Path(args.project_root)
    coverage_payload = json.loads(Path(args.coverage_json).read_text(encoding='utf-8'))
    config = yaml.safe_load((project_root / 'configs' / 'coverage_partitions.yaml').read_text(encoding='utf-8')) or {}
    partitions = dict(config.get('partitions', {}) or {})
    files = dict(coverage_payload.get('files', {}) or {})

    errors: list[str] = []
    for name, detail in partitions.items():
        roots = [str(item) for item in detail.get('roots', [])]
        minimum = float(detail.get('minimum', 0) or 0)
        covered_total = 0
        statement_total = 0
        for rel_path, payload in files.items():
            if not any(rel_path.startswith(root) for root in roots):
                continue
            summary = dict(payload.get('summary', {}) or {})
            covered, total = _covered_fraction(summary, payload)
            covered_total += covered
            statement_total += total
        if statement_total <= 0:
            errors.append(f'coverage partition has no measured statements: {name}')
            continue
        percent = (covered_total / statement_total) * 100.0
        if percent < minimum:
            errors.append(f'coverage partition below minimum: {name} observed={percent:.2f} minimum={minimum:.2f}')
    if errors:
        for item in errors:
            print(item)
        return 1
    print('partition coverage verified')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
