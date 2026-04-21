from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

import numpy as np

from robot_sim.domain.enums import AppExecutionState
from robot_sim.model.playback_state import PlaybackState

if TYPE_CHECKING:  # pragma: no cover
    from robot_sim.domain.error_projection import ErrorPresentation
    from robot_sim.model.benchmark_report import BenchmarkReport
    from robot_sim.model.fk_result import FKResult
    from robot_sim.model.ik_result import IKResult
    from robot_sim.model.pose import Pose
    from robot_sim.model.robot_spec import RobotSpec
    from robot_sim.model.session_state import SessionState
    from robot_sim.model.task_snapshot import TaskSnapshot
    from robot_sim.model.trajectory import JointTrajectory


StateSegments = tuple[str, ...]
_PLANNING_SCENE_UNCHANGED = object()


@dataclass(frozen=True)
class RobotRuntimeLoadedEvent:
    """Install one canonical robot/runtime projection into the session state."""

    spec: 'RobotSpec'
    q_current: np.ndarray
    fk_result: 'FKResult'
    scene_revision: int
    robot_geometry: object | None = None
    collision_geometry: object | None = None
    planning_scene: object | None = None
    scene_summary: dict[str, object] = field(default_factory=dict)
    app_state: AppExecutionState = AppExecutionState.ROBOT_READY


@dataclass(frozen=True)
class FKProjectedEvent:
    """Project a fresh FK result into runtime state."""

    q_current: np.ndarray
    fk_result: 'FKResult'
    scene_revision: int


@dataclass(frozen=True)
class IKResultAppliedEvent:
    """Project one IK request/result pair into runtime state."""

    target_pose: 'Pose'
    ik_result: 'IKResult'
    q_current: np.ndarray
    fk_result: 'FKResult'
    scene_revision: int


@dataclass(frozen=True)
class TrajectoryAppliedEvent:
    """Install a planned trajectory plus playback seed into runtime state."""

    trajectory: 'JointTrajectory'
    playback: PlaybackState
    scene_revision: int
    scene_summary: dict[str, object]
    app_state: AppExecutionState = AppExecutionState.ROBOT_READY


@dataclass(frozen=True)
class PlaybackStateChangedEvent:
    """Update playback state without mutating unrelated runtime projections."""

    playback: PlaybackState
    app_state: AppExecutionState | None = None
    active_task_kind: str = ''
    active_task_id: str = ''


@dataclass(frozen=True)
class PlaybackFrameProjectedEvent:
    """Project one playback frame cursor into runtime state."""

    q_current: np.ndarray


@dataclass(frozen=True)
class BusyStateChangedEvent:
    """Update busy/task execution flags through the reducer surface."""

    is_busy: bool
    busy_reason: str = ''
    app_state: AppExecutionState | None = None
    active_task_kind: str = ''
    active_task_id: str = ''


@dataclass(frozen=True)
class BenchmarkReportProjectedEvent:
    """Store the latest benchmark report."""

    benchmark_report: 'BenchmarkReport'


@dataclass(frozen=True)
class WarningProjectedEvent:
    """Store one warning while preserving warning history."""

    message: str
    code: str = ''


@dataclass(frozen=True)
class SceneRuntimeProjectedEvent:
    """Project planning-scene summary/runtime state through the reducer surface."""

    scene_summary: dict[str, object]
    planning_scene: object = _PLANNING_SCENE_UNCHANGED
    scene_revision: int | None = None


@dataclass(frozen=True)
class CapabilityMatrixProjectedEvent:
    """Store the capability matrix through the reducer surface."""

    capability_matrix: dict[str, object]


@dataclass(frozen=True)
class ModuleStatusesProjectedEvent:
    """Store module governance status details through the reducer surface."""

    module_statuses: dict[str, str]


@dataclass(frozen=True)
class TaskSnapshotProjectedEvent:
    """Project the active task snapshot into the task segment."""

    snapshot: 'TaskSnapshot | None'


@dataclass(frozen=True)
class ErrorPresentationProjectedEvent:
    """Project the last structured error presentation."""

    presentation: 'ErrorPresentation'


def reduce_state_event(state: 'SessionState', event: object) -> StateSegments:
    """Apply a canonical presentation-state event and return affected segments.

    Args:
        state: Mutable shared session state.
        event: One supported event dataclass.

    Returns:
        tuple[str, ...]: State segments that must be flushed after reduction.

    Raises:
        TypeError: If ``event`` is unsupported.
    """
    if isinstance(event, RobotRuntimeLoadedEvent):
        state.robot_spec = event.spec
        state.q_current = np.asarray(event.q_current, dtype=float).copy()
        state.fk_result = event.fk_result
        state.target_pose = None
        state.ik_result = None
        state.trajectory = None
        state.benchmark_report = None
        state.playback = PlaybackState()
        state.last_error = ''
        state.last_warning = ''
        state.app_state = event.app_state
        state.scene_revision = int(event.scene_revision)
        state.robot_geometry = event.robot_geometry
        state.collision_geometry = event.collision_geometry
        state.planning_scene = event.planning_scene
        state.scene_summary = dict(event.scene_summary or {})
        return ('session', 'task')
    if isinstance(event, FKProjectedEvent):
        state.q_current = np.asarray(event.q_current, dtype=float).copy()
        state.fk_result = event.fk_result
        state.scene_revision = int(event.scene_revision)
        return ('session',)
    if isinstance(event, IKResultAppliedEvent):
        state.target_pose = event.target_pose
        state.ik_result = event.ik_result
        state.q_current = np.asarray(event.q_current, dtype=float).copy()
        state.fk_result = event.fk_result
        state.scene_revision = int(event.scene_revision)
        succeeded = bool(event.ik_result.success)
        state.last_error = '' if succeeded else str(event.ik_result.message)
        state.last_warning = '' if succeeded else str(event.ik_result.message)
        state.app_state = AppExecutionState.ROBOT_READY if succeeded else AppExecutionState.ERROR
        return ('session', 'task')
    if isinstance(event, TrajectoryAppliedEvent):
        state.trajectory = event.trajectory
        state.playback = event.playback
        state.app_state = event.app_state
        state.scene_revision = int(event.scene_revision)
        state.scene_summary = dict(event.scene_summary or {})
        return ('session',)
    if isinstance(event, PlaybackStateChangedEvent):
        state.playback = event.playback
        if event.app_state is not None:
            state.app_state = event.app_state
        state.active_task_kind = str(event.active_task_kind)
        state.active_task_id = str(event.active_task_id)
        return ('session', 'task')
    if isinstance(event, PlaybackFrameProjectedEvent):
        state.q_current = np.asarray(event.q_current, dtype=float).copy()
        return ('session',)
    if isinstance(event, BusyStateChangedEvent):
        state.is_busy = bool(event.is_busy)
        state.busy_reason = str(event.busy_reason)
        if event.app_state is not None:
            state.app_state = event.app_state
        state.active_task_kind = str(event.active_task_kind)
        state.active_task_id = str(event.active_task_id)
        return ('session', 'task')
    if isinstance(event, BenchmarkReportProjectedEvent):
        state.benchmark_report = event.benchmark_report
        return ('session',)
    if isinstance(event, WarningProjectedEvent):
        state.last_warning = str(event.message)
        if event.code:
            codes = tuple(dict.fromkeys((*state.active_warning_codes, str(event.code))))
            state.active_warning_codes = codes
        if event.message:
            warnings = tuple(dict.fromkeys((*state.warnings, str(event.message))))
            state.warnings = warnings
        return ('task',)
    if isinstance(event, SceneRuntimeProjectedEvent):
        state.scene_summary = dict(event.scene_summary or {})
        if event.planning_scene is not _PLANNING_SCENE_UNCHANGED:
            state.planning_scene = event.planning_scene
        if event.scene_revision is not None:
            state.scene_revision = int(event.scene_revision)
        return ('session',)
    if isinstance(event, CapabilityMatrixProjectedEvent):
        state.capability_matrix = dict(event.capability_matrix or {})
        return ('session',)
    if isinstance(event, ModuleStatusesProjectedEvent):
        state.module_statuses = {str(key): str(value) for key, value in dict(event.module_statuses or {}).items()}
        return ('session',)
    if isinstance(event, TaskSnapshotProjectedEvent):
        snapshot = event.snapshot
        state.active_task_snapshot = snapshot
        if snapshot is None:
            state.active_task_id = ''
            state.active_task_kind = ''
            state.task_state = ''
            state.task_stop_reason = ''
            state.task_correlation_id = ''
        else:
            state.active_task_id = getattr(snapshot, 'task_id', '')
            state.active_task_kind = getattr(snapshot, 'task_kind', '')
            state.task_state = getattr(snapshot, 'state', '')
            state.task_stop_reason = getattr(snapshot, 'stop_reason', '')
            state.task_correlation_id = getattr(snapshot, 'correlation_id', '')
        return ('task',)
    if isinstance(event, ErrorPresentationProjectedEvent):
        presentation = event.presentation
        state.last_error = str(getattr(presentation, 'user_message', '') or '')
        state.last_error_payload = dict(getattr(presentation, 'log_payload', {}) or {})
        state.last_error_code = str(getattr(presentation, 'error_code', '') or '')
        state.last_error_title = str(getattr(presentation, 'title', '') or '')
        state.last_error_severity = str(getattr(presentation, 'severity', '') or '')
        state.last_error_hint = str(getattr(presentation, 'remediation_hint', '') or '')
        return ('task',)
    raise TypeError(f'unsupported state event: {type(event).__name__}')
