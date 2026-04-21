from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any


class CaptureSceneUseCase:
    """Own stable scene capture execution across widget and snapshot paths.

    The coordinator now depends on this use case instead of talking to the screenshot
    service directly, which keeps capture orchestration on one application-layer seam.
    """

    def __init__(self, screenshot_service) -> None:
        """Bind the stable capture service dependency.

        Args:
            screenshot_service: Service providing widget and snapshot capture operations.

        Raises:
            ValueError: If the capture service dependency is missing.
        """
        if screenshot_service is None:
            raise ValueError('capture scene use case requires a screenshot service')
        self._screenshot_service = screenshot_service

    def execute(self, scene_widget: Any, path: str | Path):
        """Capture a live scene widget to disk.

        Args:
            scene_widget: Live scene widget exposing a supported capture backend.
            path: Destination image path.

        Returns:
            Path | str: Saved screenshot path returned by the underlying service.

        Raises:
            ValueError: If the scene widget dependency is missing.
        """
        if scene_widget is None:
            raise ValueError('scene widget is required for live capture')
        return self._screenshot_service.capture(scene_widget, path)

    def execute_snapshot_details(
        self,
        snapshot: Mapping[str, object],
        path: str | Path,
        *,
        progress_cb=None,
        cancel_flag=None,
        correlation_id: str = '',
    ):
        """Capture a prebuilt scene snapshot and return structured provenance details."""
        if not isinstance(snapshot, Mapping):
            raise ValueError('scene snapshot payload must be a mapping')
        details_fn = getattr(self._screenshot_service, 'capture_from_snapshot_details', None)
        if callable(details_fn):
            return details_fn(
                dict(snapshot),
                path,
                progress_cb=progress_cb,
                cancel_flag=cancel_flag,
                correlation_id=correlation_id,
            )
        result = self.execute_snapshot(
            snapshot,
            path,
            progress_cb=progress_cb,
            cancel_flag=cancel_flag,
            correlation_id=correlation_id,
        )
        return {'path': result, 'runtime_state': None, 'provenance': {}}

    def snapshot_provenance(self, snapshot: Mapping[str, object], *, backend: str = 'snapshot_renderer') -> dict[str, object]:
        """Return structured capture provenance for a snapshot render path."""
        if not isinstance(snapshot, Mapping):
            raise ValueError('scene snapshot payload must be a mapping')
        provenance_fn = getattr(self._screenshot_service, 'snapshot_provenance', None)
        if callable(provenance_fn):
            return dict(provenance_fn(dict(snapshot), backend=backend))
        return {'capture_source': 'scene_snapshot', 'render_path': str(backend or 'snapshot_renderer')}

    def execute_snapshot(
        self,
        snapshot: Mapping[str, object],
        path: str | Path,
        *,
        progress_cb=None,
        cancel_flag=None,
        correlation_id: str = '',
    ):
        """Capture a prebuilt scene snapshot outside the UI thread.

        Args:
            snapshot: Serializable scene snapshot captured on the UI thread.
            path: Destination image path.
            progress_cb: Optional structured progress callback.
            cancel_flag: Optional cooperative cancellation probe.
            correlation_id: Stable task correlation identifier for diagnostics.

        Returns:
            Path | str: Saved screenshot path returned by the underlying service.

        Raises:
            ValueError: If the snapshot payload is not mapping-like.
        """
        if not isinstance(snapshot, Mapping):
            raise ValueError('scene snapshot payload must be a mapping')
        return self._screenshot_service.capture_from_snapshot(
            dict(snapshot),
            path,
            progress_cb=progress_cb,
            cancel_flag=cancel_flag,
            correlation_id=correlation_id,
        )

    def snapshot_sampling_counters(self, snapshot: Mapping[str, object], *, backend: str, source: str):
        """Return structured sampling counters for snapshot telemetry.

        Raises:
            ValueError: If the snapshot payload is not mapping-like.
        """
        if not isinstance(snapshot, Mapping):
            raise ValueError('scene snapshot payload must be a mapping')
        return self._screenshot_service.snapshot_sampling_counters(dict(snapshot), backend=backend, source=source)

    def snapshot_sample_count(self, snapshot: Mapping[str, object]) -> int:
        """Return a bounded sample count for snapshot telemetry.

        Raises:
            ValueError: If the snapshot payload is not mapping-like.
        """
        if not isinstance(snapshot, Mapping):
            raise ValueError('scene snapshot payload must be a mapping')
        return int(self._screenshot_service.snapshot_sample_count(dict(snapshot)))
