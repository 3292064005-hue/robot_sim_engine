from __future__ import annotations


class ActorManager:  # pragma: no cover - GUI shell
    def __init__(self) -> None:
        self._actors: dict[str, object] = {}

    def get(self, name: str):
        return self._actors.get(name)

    def set(self, name: str, actor) -> None:
        self._actors[name] = actor

    def names(self) -> list[str]:
        return sorted(self._actors)

    def remove(self, plotter, name: str) -> None:
        actor = self._actors.pop(name, None)
        if actor is not None and plotter is not None:
            try:
                plotter.remove_actor(actor)
            except Exception:
                pass

    def clear(self, plotter) -> None:
        for name in list(self._actors):
            self.remove(plotter, name)
