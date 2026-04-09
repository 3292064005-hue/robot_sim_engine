from __future__ import annotations

from collections.abc import MutableMapping
import os


def configure_qt_platform_for_pytest(
    env: MutableMapping[str, str] | None = None,
    *,
    default_platform: str = 'offscreen',
    force_display_env: str = 'ROBOT_SIM_PYTEST_FORCE_GUI_DISPLAY',
) -> str | None:
    """Configure a deterministic Qt platform for pytest-driven GUI smoke.

    Args:
        env: Mutable environment mapping to mutate. Defaults to ``os.environ``.
        default_platform: Platform plugin enforced for pytest GUI smoke when the
            caller did not explicitly choose a Qt platform plugin.
        force_display_env: Environment variable name that, when set to ``1``,
            preserves the desktop display selection and disables auto-offscreen.

    Returns:
        str | None: The effective ``QT_QPA_PLATFORM`` after normalization.

    Raises:
        None: Environment normalization is best-effort and side-effect free beyond
            updating the supplied mapping.

    Boundary behavior:
        pytest GUI smoke defaults to ``offscreen`` so direct ``pytest`` runs do not
        depend on a valid X11/Wayland session. Callers can keep the desktop display
        by exporting ``ROBOT_SIM_PYTEST_FORCE_GUI_DISPLAY=1`` or by explicitly
        setting ``QT_QPA_PLATFORM`` before pytest starts.
    """
    target_env = os.environ if env is None else env
    explicit_platform = str(target_env.get('QT_QPA_PLATFORM', '') or '').strip()
    if explicit_platform:
        return explicit_platform
    if str(target_env.get(force_display_env, '') or '').strip() == '1':
        return None
    target_env['QT_QPA_PLATFORM'] = default_platform
    return default_platform
