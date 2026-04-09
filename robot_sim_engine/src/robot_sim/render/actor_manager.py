from __future__ import annotations

import logging

from robot_sim.domain.errors import RenderOperationError

logger = logging.getLogger(__name__)


class ActorManager:  # pragma: no cover - GUI shell
    """Track named render actors attached to a scene plotter."""

    def __init__(self) -> None:
        self._actors: dict[str, object] = {}

    def get(self, name: str):
        return self._actors.get(name)

    def set(self, name: str, actor) -> None:
        self._actors[name] = actor

    def names(self) -> list[str]:
        return sorted(self._actors)

    def remove(self, plotter, name: str) -> None:
        """Remove a tracked actor from the supplied plotter.

        Args:
            plotter: Plotter/backend shell owning the actor.
            name: Stable actor name tracked by this manager.

        Returns:
            None: Mutates the tracked actor registry in place.

        Raises:
            RenderOperationError: If the backend rejects actor removal after the actor was tracked.
        """
        actor = self._actors.pop(name, None)
        if actor is not None and plotter is not None:
            try:
                plotter.remove_actor(actor)
            except (AttributeError, RuntimeError, TypeError, ValueError) as exc:
                self._actors[name] = actor
                logger.warning('failed to remove actor %s: %s', name, exc)
                raise RenderOperationError(
                    'failed to remove scene actor',
                    metadata={'actor_name': name, 'exception_type': exc.__class__.__name__},
                ) from exc

    def clear(self, plotter) -> None:
        """Remove all tracked actors from the supplied plotter.

        Args:
            plotter: Plotter/backend shell owning the tracked actors.

        Returns:
            None: Removes all actors that can be successfully detached.

        Raises:
            RenderOperationError: Propagates the first actor-removal failure.
        """
        for name in list(self._actors):
            self.remove(plotter, name)
