from __future__ import annotations

from hashlib import sha256
from pathlib import Path

import numpy as np
import pytest

from robot_sim.domain.errors import ExportRobotError
from robot_sim.model.pose import Pose
from robot_sim.render.screenshot_service import ScreenshotService


class _DummyPlotter:
    def screenshot(self, path: str) -> None:
        Path(path).write_bytes(b'not-empty-image')


class _DummySceneWithPlotter:
    plotter = _DummyPlotter()


class _DummySceneWithoutBackend:
    plotter = None


class _DummySnapshotScene:
    plotter = None

    def scene_snapshot(self):
        return {
            'title': 'scene',
            'robot_points': np.array([[0.0, 0.0, 0.0], [0.4, 0.2, 0.3], [1.0, 0.0, 0.0]], dtype=float),
            'trajectory_points': np.array([[0.0, 0.0, 0.0], [0.3, 0.1, 0.2], [1.0, 0.2, 0.0]], dtype=float),
            'playback_marker': np.array([1.0, 0.0, 0.0], dtype=float),
            'target_pose': Pose(p=np.array([1.0, 0.0, 0.0]), R=np.eye(3)),
            'target_axes_visible': True,
        }


class _DummyEmptySnapshotScene:
    plotter = None

    def scene_snapshot(self):
        return {'title': 'empty'}


<<<<<<< HEAD
class _DummyOverlayOnlySnapshotScene:
    plotter = None

    def scene_snapshot(self):
        return {'title': 'overlay-only', 'overlay_text': 'Robot Sim Engine'}


=======
>>>>>>> 3ed78e647985c6d680c085e4480d898855278db3
def test_screenshot_service_uses_live_plotter_when_available(tmp_path):
    path = ScreenshotService().capture(_DummySceneWithPlotter(), tmp_path / 'shot.png')
    assert path.exists()
    assert path.read_bytes() == b'not-empty-image'


def test_screenshot_service_raises_instead_of_writing_empty_file(tmp_path):
    with pytest.raises(ExportRobotError) as exc_info:
        ScreenshotService().capture(_DummySceneWithoutBackend(), tmp_path / 'shot.png')
    assert exc_info.value.error_code == 'unsupported_capture_backend'
    assert not (tmp_path / 'shot.png').exists()


def test_screenshot_service_renders_snapshot_without_optional_gui_backend(tmp_path):
    path = ScreenshotService().capture(_DummySnapshotScene(), tmp_path / 'shot.png')
    assert path.exists()
    assert path.stat().st_size > 0
    assert path.read_bytes().startswith(b'\x89PNG\r\n\x1a\n')


def test_screenshot_service_snapshot_render_is_deterministic(tmp_path):
    path = ScreenshotService().capture(_DummySnapshotScene(), tmp_path / 'shot.png')
    digest = sha256(path.read_bytes()).hexdigest()
    assert digest == '0ff64738775ffb7a627c2837e8cb44d9e3c197eb1da59cf087bababe1ea5693d'


<<<<<<< HEAD
def test_screenshot_service_snapshot_sample_count_matches_drawable_samples():
    service = ScreenshotService()
    snapshot = _DummySnapshotScene().scene_snapshot()
    counters = service.snapshot_sampling_counters(snapshot, backend='snapshot_renderer', source='scene_capture_worker')
    by_name = {item['counter_name']: item['value'] for item in counters}
    assert service.snapshot_sample_count(snapshot) == int(by_name['drawable_samples'])




def test_screenshot_service_renders_overlay_only_snapshot(tmp_path):
    path = ScreenshotService().capture(_DummyOverlayOnlySnapshotScene(), tmp_path / 'overlay-shot.png')
    assert path.exists()
    assert path.stat().st_size > 0

=======
>>>>>>> 3ed78e647985c6d680c085e4480d898855278db3
def test_screenshot_service_rejects_empty_snapshot_payload(tmp_path):
    with pytest.raises(ExportRobotError) as exc_info:
        ScreenshotService().capture(_DummyEmptySnapshotScene(), tmp_path / 'shot.png')
    assert exc_info.value.error_code == 'render_unavailable'
<<<<<<< HEAD



def test_screenshot_service_reports_runtime_state_for_snapshot_fallback():
    state = ScreenshotService().runtime_state(_DummySnapshotScene())
    assert state.capability == 'screenshot'
    assert state.status == 'degraded'
    assert state.backend == 'snapshot_renderer'
    assert state.level == 'snapshot_capture'
    assert state.provenance['capture_source'] == 'scene_snapshot'



def test_screenshot_service_builds_sampling_counters_for_snapshot_path():
    service = ScreenshotService()
    counters = service.snapshot_sampling_counters(_DummySnapshotScene().scene_snapshot(), backend='snapshot_renderer', source='scene_capture_worker')
    assert len(counters) >= 4
    by_name = {item['counter_name']: item for item in counters}
    assert by_name['robot_points']['value'] == 3.0
    assert by_name['trajectory_points']['unit'] == 'points'
    assert by_name['drawable_samples']['value'] >= 8.0


def test_screenshot_service_capture_details_include_runtime_provenance(tmp_path):
    details = ScreenshotService().capture_details(_DummySnapshotScene(), tmp_path / 'shot-details.png')
    assert details['path'].exists()
    runtime_state = details['runtime_state']
    assert runtime_state.level == 'snapshot_capture'
    assert details['provenance']['render_path'] == 'snapshot_renderer'
=======
>>>>>>> 3ed78e647985c6d680c085e4480d898855278db3
