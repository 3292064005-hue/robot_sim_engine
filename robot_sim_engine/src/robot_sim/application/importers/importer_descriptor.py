from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class ImporterDescriptor:
    """Registry descriptor for a robot importer plugin or builtin importer."""

    importer_id: str
    aliases: tuple[str, ...] = ()
    metadata: dict[str, object] = field(default_factory=dict)
