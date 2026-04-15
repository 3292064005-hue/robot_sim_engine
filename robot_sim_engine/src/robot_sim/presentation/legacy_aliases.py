from __future__ import annotations

from robot_sim.infra.compatibility_usage import record_compatibility_usage


class MainWindowLegacyAliasMixin:
    """Compatibility shim exposing removed private MainWindow aliases.

    The project no longer implements legacy ``*_impl`` methods as first-class code paths,
    but some out-of-repo automation may still reach for those private names. The shim now
    exposes an explicit deprecated method surface instead of a broad ``__getattr__`` trap,
    which keeps introspection and missing-attribute behavior predictable while continuing
    to redirect supported aliases to the canonical public ``on_*`` entry points.
    """

    def _dispatch_legacy_alias(self, alias_name: str, target_name: str, /, *args, **kwargs):
        """Dispatch a deprecated alias to the canonical public handler.

        Args:
            alias_name: Historical private alias being invoked.
            target_name: Canonical public method implementing the behavior.
            *args: Positional arguments forwarded to the public handler.
            **kwargs: Keyword arguments forwarded to the public handler.

        Returns:
            object: Return value from the canonical public handler.

        Raises:
            AttributeError: If the canonical handler is missing on the concrete window.

        Boundary behavior:
            The shim remains read-only. It preserves the historical alias names only as
            thin dispatch wrappers and does not recreate separate private implementations.
        """
        record_compatibility_usage('main window private alias shim', detail=f'{alias_name}->{target_name}')
        try:
            handler = getattr(self, target_name)
        except AttributeError as exc:
            raise AttributeError(
                f"{type(self).__name__!s} cannot resolve legacy alias {alias_name!r} because "
                f"the canonical handler {target_name!r} is unavailable"
            ) from exc
        return handler(*args, **kwargs)

    def _load_robot_impl(self, *args, **kwargs):
        return self._dispatch_legacy_alias('_load_robot_impl', 'on_load_robot', *args, **kwargs)

    def _save_robot_impl(self, *args, **kwargs):
        return self._dispatch_legacy_alias('_save_robot_impl', 'on_save_robot', *args, **kwargs)

    def _play_impl(self, *args, **kwargs):
        return self._dispatch_legacy_alias('_play_impl', 'on_play', *args, **kwargs)

    def _pause_impl(self, *args, **kwargs):
        return self._dispatch_legacy_alias('_pause_impl', 'on_pause', *args, **kwargs)

    def _stop_playback_impl(self, *args, **kwargs):
        return self._dispatch_legacy_alias('_stop_playback_impl', 'on_stop_playback', *args, **kwargs)

    def _fit_scene_impl(self, *args, **kwargs):
        return self._dispatch_legacy_alias('_fit_scene_impl', 'on_fit_scene', *args, **kwargs)

    def _clear_scene_path_impl(self, *args, **kwargs):
        return self._dispatch_legacy_alias('_clear_scene_path_impl', 'on_clear_scene_path', *args, **kwargs)

    def _capture_scene_impl(self, *args, **kwargs):
        return self._dispatch_legacy_alias('_capture_scene_impl', 'on_capture_scene', *args, **kwargs)

    def _export_trajectory_impl(self, *args, **kwargs):
        return self._dispatch_legacy_alias('_export_trajectory_impl', 'on_export_trajectory', *args, **kwargs)

    def _export_session_impl(self, *args, **kwargs):
        return self._dispatch_legacy_alias('_export_session_impl', 'on_export_session', *args, **kwargs)

    def _export_package_impl(self, *args, **kwargs):
        return self._dispatch_legacy_alias('_export_package_impl', 'on_export_package', *args, **kwargs)

    def _export_benchmark_impl(self, *args, **kwargs):
        return self._dispatch_legacy_alias('_export_benchmark_impl', 'on_export_benchmark', *args, **kwargs)

    def _run_ik_impl(self, *args, **kwargs):
        return self._dispatch_legacy_alias('_run_ik_impl', 'on_run_ik', *args, **kwargs)

    def _run_traj_impl(self, *args, **kwargs):
        return self._dispatch_legacy_alias('_run_traj_impl', 'on_plan', *args, **kwargs)

    def _run_benchmark_impl(self, *args, **kwargs):
        return self._dispatch_legacy_alias('_run_benchmark_impl', 'on_run_benchmark', *args, **kwargs)
