from __future__ import annotations

import json
import zlib
from pathlib import Path
from types import SimpleNamespace

import numpy as np

from robot_sim.render.screenshot_service import ScreenshotService


BASELINE_PATH = Path(__file__).resolve().parent / 'baselines' / 'scene_capture_snapshot_baseline.json'


def _baseline_snapshot() -> dict[str, object]:
    return {
        'title': 'Render Baseline',
        'robot_points': np.array([[0.0, 0.0, 0.0], [0.1, 0.0, 0.0], [0.2, 0.05, 0.1]], dtype=float),
        'trajectory_points': np.array([[0.0, 0.0, 0.0], [0.05, 0.02, 0.03], [0.2, 0.04, 0.05], [0.25, 0.08, 0.07]], dtype=float),
        'playback_marker': np.array([0.1, 0.02, 0.03], dtype=float),
        'target_pose': SimpleNamespace(p=np.array([0.25, 0.1, 0.08], dtype=float), R=np.eye(3)),
        'target_axes_visible': True,
    }


def test_snapshot_renderer_matches_checked_in_baseline(tmp_path: Path) -> None:
    baseline = json.loads(BASELINE_PATH.read_text(encoding='utf-8'))
    service = ScreenshotService()
    target = tmp_path / 'scene_capture_baseline.png'
    service.capture_from_snapshot(_baseline_snapshot(), target)
    payload = target.read_bytes()
    counters = {
        entry['counter_name']: entry['value']
        for entry in service.snapshot_sampling_counters(
            _baseline_snapshot(),
            backend='snapshot_renderer',
            source='baseline_regression',
        )
    }
    assert len(payload) == int(baseline['bytes'])
    assert zlib.crc32(payload) & 0xFFFFFFFF == int(baseline['crc32'])
    assert int(counters['drawable_samples']) == int(baseline['drawable_samples'])
    assert int(counters['drawable_entities']) == int(baseline['drawable_entities'])
    assert int(counters['canvas_pixels']) == int(baseline['canvas_pixels'])
