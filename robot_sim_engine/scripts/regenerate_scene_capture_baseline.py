#!/usr/bin/env python3
from __future__ import annotations

import json
import zlib
from pathlib import Path
from types import SimpleNamespace

import numpy as np

from robot_sim.render.screenshot_service import ScreenshotService


ROOT = Path(__file__).resolve().parents[1]
BASELINE_PATH = ROOT / 'tests' / 'regression' / 'baselines' / 'scene_capture_snapshot_baseline.json'


def build_snapshot() -> dict[str, object]:
    return {
        'title': 'Render Baseline',
        'robot_points': np.array([[0.0, 0.0, 0.0], [0.1, 0.0, 0.0], [0.2, 0.05, 0.1]], dtype=float),
        'trajectory_points': np.array([[0.0, 0.0, 0.0], [0.05, 0.02, 0.03], [0.2, 0.04, 0.05], [0.25, 0.08, 0.07]], dtype=float),
        'playback_marker': np.array([0.1, 0.02, 0.03], dtype=float),
        'target_pose': SimpleNamespace(p=np.array([0.25, 0.1, 0.08], dtype=float), R=np.eye(3)),
        'target_axes_visible': True,
    }


def main() -> int:
    snapshot = build_snapshot()
    service = ScreenshotService()
    temp_path = ROOT / 'exports' / '_scene_capture_baseline.png'
    temp_path.parent.mkdir(parents=True, exist_ok=True)
    service.capture_from_snapshot(snapshot, temp_path)
    payload = temp_path.read_bytes()
    counters = {
        entry['counter_name']: entry['value']
        for entry in service.snapshot_sampling_counters(snapshot, backend='snapshot_renderer', source='baseline_regen')
    }
    baseline = {
        'bytes': len(payload),
        'crc32': zlib.crc32(payload) & 0xFFFFFFFF,
        'drawable_samples': int(counters['drawable_samples']),
        'drawable_entities': int(counters['drawable_entities']),
        'canvas_pixels': int(counters['canvas_pixels']),
    }
    BASELINE_PATH.parent.mkdir(parents=True, exist_ok=True)
    BASELINE_PATH.write_text(json.dumps(baseline, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    temp_path.unlink(missing_ok=True)
    print(f'updated {BASELINE_PATH.relative_to(ROOT)}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
