from __future__ import annotations

from typing import Any

from robot_sim.presentation.qt_runtime import QApplication, require_qt_runtime

_HEADLESS_QT_APP: Any | None = None


def normalize_import_extensions(raw_extensions: object) -> tuple[str, ...]:
    """Normalize importer extension metadata into deterministic wildcard suffixes."""
    values: list[str] = []
    if isinstance(raw_extensions, (list, tuple, set)):
        source = raw_extensions
    elif raw_extensions in (None, ''):
        source = ()
    else:
        source = (raw_extensions,)
    for item in source:
        suffix = str(item).strip().lstrip('.').lower()
        if suffix and suffix not in values:
            values.append(suffix)
    return tuple(values)


def build_import_dialog_filters(importer_entries) -> str:
    """Build a deterministic Qt file-dialog filter string from importer descriptors."""
    normalized: list[tuple[str, tuple[str, ...]]] = []
    aggregate_patterns: list[str] = []
    for entry in importer_entries:
        metadata = dict(getattr(entry, 'metadata', {}) or {})
        extensions = normalize_import_extensions(metadata.get('extensions'))
        if not extensions:
            extensions = normalize_import_extensions((metadata.get('source_format', ''), getattr(entry, 'importer_id', '')))
        patterns = tuple(f'*.{suffix}' for suffix in extensions if suffix)
        if not patterns:
            continue
        label = str(metadata.get('display_name', '') or getattr(entry, 'importer_id', 'importer'))
        normalized.append((label, patterns))
        for pattern in patterns:
            if pattern not in aggregate_patterns:
                aggregate_patterns.append(pattern)
    filters: list[str] = []
    if aggregate_patterns:
        filters.append(f"支持的机器人配置 ({' '.join(aggregate_patterns)})")
    for label, patterns in normalized:
        filters.append(f"{label} ({' '.join(patterns)})")
    filters.append('所有文件 (*)')
    return ';;'.join(filters)


def ensure_qt_application() -> None:
    """Ensure widget construction has an active QApplication instance.

    Raises:
        RuntimeError: If no Qt runtime is available for stable widget construction.
    """
    require_qt_runtime('MainWindow UI')
    instance_fn = getattr(QApplication, 'instance', None)
    if not callable(instance_fn):
        return
    if instance_fn() is not None:
        return
    global _HEADLESS_QT_APP
    if _HEADLESS_QT_APP is None:
        _HEADLESS_QT_APP = QApplication([])
        setattr(_HEADLESS_QT_APP, '_robot_sim_headless_helper', True)
