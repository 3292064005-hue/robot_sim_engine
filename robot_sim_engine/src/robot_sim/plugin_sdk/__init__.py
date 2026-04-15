from __future__ import annotations

from typing import Iterable


def plugin_payload(
    instance: object,
    *,
    aliases: Iterable[str] = (),
    metadata: dict[str, object] | None = None,
) -> dict[str, object]:
    """Build a manifest-compatible plugin payload.

    Args:
        instance: Concrete plugin instance exposed to the host registry.
        aliases: Optional registry aliases.
        metadata: Optional plugin metadata projected into loader registration summaries.

    Returns:
        dict[str, object]: Stable payload consumed by ``PluginLoader`` factories.

    Raises:
        ValueError: If ``instance`` is ``None``.

    Boundary behavior:
        Metadata and aliases are normalized into deterministic host-facing containers so
        direct factory imports and entry-point based factories produce the same loader shape.
    """
    if instance is None:
        raise ValueError('plugin payload requires a concrete instance')
    return {
        'instance': instance,
        'aliases': tuple(str(alias) for alias in aliases),
        'metadata': dict(metadata or {}),
    }


__all__ = ['plugin_payload']
