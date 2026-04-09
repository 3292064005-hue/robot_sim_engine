from __future__ import annotations

from time import perf_counter

from robot_sim.domain.errors import (
    ExportRobotError,
    PlotBackendUnavailableError,
    RenderBackendUnavailableError,
    RenderInitializationError,
    RenderOperationError,
)
from robot_sim.model.render_runtime import RenderCapabilityState, RenderRuntimeState
from robot_sim.presentation.status_panel_state import format_playback_metric


class MainWindowRenderRuntimeUIMixin:
    """Render-runtime probes and projection helpers for the stable main-window UI shell."""

    def _playback_status_text(self):
        return format_playback_metric(self._runtime_ops().state.playback)

    def _format_render_runtime_metric(self, capability: RenderCapabilityState) -> str:
        """Format a compact UI label for a render runtime capability state."""
        status_map = {'available': '可用', 'degraded': '降级', 'unsupported': '不可用'}
        prefix = status_map.get(capability.status, capability.status)
        detail = capability.backend or capability.reason or capability.error_code
        return prefix if detail == '' else f"{prefix} ({detail})"

    def _render_runtime_metric_payload(self) -> dict[str, str]:
        """Return status-strip metric fields derived from the shared render runtime state."""
        render_runtime = RenderRuntimeState.from_mapping(self._runtime_ops().state.render_runtime)
        return {
            'scene_3d': self._format_render_runtime_metric(render_runtime.scene_3d),
            'plots': self._format_render_runtime_metric(render_runtime.plots),
            'screenshot': self._format_render_runtime_metric(render_runtime.screenshot),
        }

    def _collect_render_runtime_state(self) -> RenderRuntimeState:
        """Collect render/runtime capability state from the live UI shell dependencies.

        Returns:
            RenderRuntimeState: Structured capability snapshot gathered from the
                live UI shell.

        Raises:
            None: Missing render dependencies are normalized into structured
                unsupported/degraded capability states.

        Boundary behavior:
            The method records fine-grained render telemetry for the probe itself:
            one runtime-probe span and one probe counter per capability/backend.
            Telemetry writes are batched with ``notify=False`` because the caller
            immediately projects the resulting runtime state into the shared store.
        """
        scene_widget = getattr(self, 'scene_widget', None)
        plots_manager = getattr(self, 'plots_manager', None)
        screenshot_service = getattr(getattr(scene_widget, 'screenshot_service', None), 'runtime_state', None)
        runtime = self._runtime_ops()

        def _probe(capability: str, callback, fallback: RenderCapabilityState):
            started = perf_counter()
            try:
                state = callback() if callable(callback) else fallback
            except (AttributeError, RuntimeError, TypeError, ValueError, OSError) as exc:  # pragma: no cover - defensive projection path
                state = RenderCapabilityState(
                    capability=capability,
                    status='degraded',
                    backend='probe',
                    reason='runtime_probe_failed',
                    error_code='runtime_probe_failed',
                    message=f'{capability} runtime probe failed.',
                    metadata={'exception_type': exc.__class__.__name__, 'message': str(exc)},
                )
            duration_ms = (perf_counter() - started) * 1000.0
            normalized = RenderCapabilityState.from_mapping(capability, state)
            runtime.state_store.record_render_operation_span(
                capability,
                'runtime_probe',
                backend=normalized.backend,
                status='succeeded',
                duration_ms=duration_ms,
                sample_count=1,
                source='ui_runtime_probe',
                message=normalized.message or f'{capability} runtime probe completed.',
                metadata={'capability_status': normalized.status, 'reason': normalized.reason},
                notify=False,
            )
            runtime.state_store.record_render_sampling_counter(
                capability,
                'probe_count',
                backend=normalized.backend,
                value=1.0,
                unit='probes',
                source='ui_runtime_probe',
                metadata={'capability_status': normalized.status},
                notify=False,
            )
            return normalized

        scene_state = _probe(
            'scene_3d',
            getattr(scene_widget, 'scene_runtime_state', None),
            RenderCapabilityState(capability='scene_3d', status='unsupported', backend='none', reason='scene_widget_missing', error_code='scene_widget_missing', message='3D scene widget is unavailable.'),
        )
        plots_state = _probe(
            'plots',
            getattr(plots_manager, 'runtime_state', None),
            RenderCapabilityState(capability='plots', status='unsupported', backend='none', reason='plots_manager_missing', error_code='plots_manager_missing', message='Plot runtime manager is unavailable.'),
        )
        screenshot_state = _probe(
            'screenshot',
            getattr(scene_widget, 'screenshot_runtime_state', None) if scene_widget is not None and callable(getattr(scene_widget, 'screenshot_runtime_state', None)) else (lambda: screenshot_service(scene_widget)) if scene_widget is not None and callable(screenshot_service) else None,
            RenderCapabilityState(capability='screenshot', status='unsupported', backend='none', reason='capture_backend_missing', error_code='unsupported_capture_backend', message='Scene screenshot capture backend is unavailable.'),
        )
        return RenderRuntimeState(scene_3d=scene_state, plots=plots_state, screenshot=screenshot_state)

    def _patch_render_runtime_from_exception(self, exc: Exception | str) -> None:
        """Project render-specific degradation causes into the shared runtime state."""
        if not isinstance(exc, Exception):
            return
        runtime = self._runtime_ops()
        if isinstance(exc, PlotBackendUnavailableError):
            runtime.state_store.patch_render_capability('plots', RenderCapabilityState(capability='plots', status='unsupported', backend='pyqtgraph', reason='backend_dependency_missing', error_code=exc.error_code, message=exc.message or 'Plot backend is unavailable.', metadata=getattr(exc, 'metadata', {})), source='presentation_exception', metadata={'exception_type': exc.__class__.__name__})
            return
        if isinstance(exc, RenderBackendUnavailableError):
            runtime.state_store.patch_render_capability('scene_3d', RenderCapabilityState(capability='scene_3d', status='unsupported', backend='pyvistaqt', reason='backend_dependency_missing', error_code=exc.error_code, message=exc.message or '3D scene backend is unavailable.', metadata=getattr(exc, 'metadata', {})), source='presentation_exception', metadata={'exception_type': exc.__class__.__name__})
            return
        if isinstance(exc, RenderInitializationError):
            runtime.state_store.patch_render_capability('scene_3d', RenderCapabilityState(capability='scene_3d', status='degraded', backend='pyvistaqt', reason='backend_initialization_failed', error_code=exc.error_code, message=exc.message or '3D scene backend initialization failed.', metadata=getattr(exc, 'metadata', {})), source='presentation_exception', metadata={'exception_type': exc.__class__.__name__})
            runtime.state_store.patch_render_capability('screenshot', RenderCapabilityState(capability='screenshot', status='degraded', backend='snapshot_renderer', reason='snapshot_renderer_fallback', message='Scene screenshots are running through the snapshot fallback renderer.', metadata=getattr(exc, 'metadata', {})), source='presentation_exception', metadata={'exception_type': exc.__class__.__name__})
            return
        if isinstance(exc, RenderOperationError):
            metadata = dict(getattr(exc, 'metadata', {}) or {})
            target = 'plots' if ('plot_key' in metadata or 'curve_name' in metadata) else 'scene_3d'
            runtime.state_store.patch_render_capability(target, RenderCapabilityState(capability=target, status='degraded', backend='pyqtgraph' if target == 'plots' else 'pyvistaqt', reason='operation_failed', error_code=exc.error_code, message=exc.message or 'Render operation failed.', metadata=metadata), source='presentation_exception', metadata={'exception_type': exc.__class__.__name__})
            return
        if isinstance(exc, ExportRobotError) and str(getattr(exc, 'error_code', '')) == 'unsupported_capture_backend':
            runtime.state_store.patch_render_capability('screenshot', RenderCapabilityState(capability='screenshot', status='unsupported', backend='none', reason='capture_backend_missing', error_code=exc.error_code, message=exc.message or 'Scene screenshot capture backend is unavailable.', metadata=getattr(exc, 'metadata', {})), source='presentation_exception', metadata={'exception_type': exc.__class__.__name__})

    def _patch_render_runtime_from_presentation(self, presentation) -> None:
        """Project mapped worker-failure envelopes back into render runtime state."""
        runtime = self._runtime_ops()
        error_code = str(getattr(presentation, 'error_code', '') or '')
        metadata = dict(getattr(presentation, 'log_payload', {}) or {}).get('metadata', {}) or {}
        if error_code == 'plot_backend_unavailable':
            runtime.state_store.patch_render_capability('plots', RenderCapabilityState(capability='plots', status='unsupported', backend='pyqtgraph', reason='backend_dependency_missing', error_code=error_code, message=str(getattr(presentation, 'user_message', '') or 'Plot backend is unavailable.'), metadata=dict(metadata)), source='worker_failure_projection', metadata={'presentation_error_code': error_code})
        elif error_code == 'render_backend_unavailable':
            runtime.state_store.patch_render_capability('scene_3d', RenderCapabilityState(capability='scene_3d', status='unsupported', backend='pyvistaqt', reason='backend_dependency_missing', error_code=error_code, message=str(getattr(presentation, 'user_message', '') or '3D scene backend is unavailable.'), metadata=dict(metadata)), source='worker_failure_projection', metadata={'presentation_error_code': error_code})
        elif error_code == 'render_initialization_failed':
            runtime.state_store.patch_render_capability('scene_3d', RenderCapabilityState(capability='scene_3d', status='degraded', backend='pyvistaqt', reason='backend_initialization_failed', error_code=error_code, message=str(getattr(presentation, 'user_message', '') or '3D scene backend initialization failed.'), metadata=dict(metadata)), source='worker_failure_projection', metadata={'presentation_error_code': error_code})
            runtime.state_store.patch_render_capability('screenshot', RenderCapabilityState(capability='screenshot', status='degraded', backend='snapshot_renderer', reason='snapshot_renderer_fallback', message='Scene screenshots are running through the snapshot fallback renderer.', metadata=dict(metadata)), source='worker_failure_projection', metadata={'presentation_error_code': error_code})
        elif error_code == 'unsupported_capture_backend':
            runtime.state_store.patch_render_capability('screenshot', RenderCapabilityState(capability='screenshot', status='unsupported', backend='none', reason='capture_backend_missing', error_code=error_code, message=str(getattr(presentation, 'user_message', '') or 'Scene screenshot capture backend is unavailable.'), metadata=dict(metadata)), source='worker_failure_projection', metadata={'presentation_error_code': error_code})
        elif error_code == 'render_operation_failed':
            target = 'plots' if ('plot_key' in metadata or 'curve_name' in metadata) else 'scene_3d'
            runtime.state_store.patch_render_capability(target, RenderCapabilityState(capability=target, status='degraded', backend='pyqtgraph' if target == 'plots' else 'pyvistaqt', reason='operation_failed', error_code=error_code, message=str(getattr(presentation, 'user_message', '') or 'Render operation failed.'), metadata=dict(metadata)), source='worker_failure_projection', metadata={'presentation_error_code': error_code})

    def project_render_runtime_state(self, render_runtime: RenderRuntimeState | dict[str, object], *, source: str = 'runtime_projection') -> None:
        """Project aggregate render runtime state into the shared state store and status strip."""
        self._ensure_status_panel_projection_subscription()
        self._ensure_render_telemetry_subscription()
        self._runtime_ops().state_store.patch_render_runtime(render_runtime, source=source)
