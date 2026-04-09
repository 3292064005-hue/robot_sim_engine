from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class ImporterDescriptor:
<<<<<<< HEAD
    """Registry descriptor for a robot importer plugin or builtin importer."""

=======
>>>>>>> 3ed78e647985c6d680c085e4480d898855278db3
    importer_id: str
    aliases: tuple[str, ...] = ()
    metadata: dict[str, object] = field(default_factory=dict)
