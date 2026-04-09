from __future__ import annotations

from robot_sim.domain.module_governance import governance_for_module
from robot_sim.domain.runtime_contracts import MODULE_STATUSES, render_module_status_markdown


class ModuleStatusService:
    """Provide module-status snapshots for presentation and diagnostics."""

    MODULE_STATUSES: dict[str, str] = MODULE_STATUSES

    def __init__(self, runtime_feature_policy=None, *, quality_gate_results: dict[str, bool] | None = None) -> None:
        self._runtime_feature_policy = runtime_feature_policy
        self._quality_gate_results = {str(key): bool(value) for key, value in dict(quality_gate_results or {}).items()}

    def snapshot(self) -> dict[str, str]:
        """Return the current module-status snapshot.

        Returns:
            dict[str, str]: Module identifier to module-status mapping.

        Raises:
            None: The snapshot is static runtime metadata.
        """
        return dict(self.MODULE_STATUSES)

    def snapshot_details(self) -> dict[str, dict[str, object]]:
        """Return module statuses together with runtime enablement flags."""
        experimental_enabled = bool(getattr(self._runtime_feature_policy, 'experimental_modules_enabled', False))
        details: dict[str, dict[str, object]] = {}
        for module_id, status in self.snapshot().items():
            enabled = bool(status != 'experimental' or experimental_enabled)
            governance = governance_for_module(str(module_id))
            detail = {'status': str(status), 'enabled': enabled}
            if governance is not None:
                evaluation = governance.evaluate(self._quality_gate_results)
                detail['governance'] = evaluation
                detail['promotion_ready'] = bool(evaluation.get('promotion_ready', False))
            details[str(module_id)] = detail
        return details

    def render_markdown(self) -> str:
        """Render the module-status snapshot as deterministic markdown.

        Returns:
            str: Markdown bullet list grouped by status label.

        Raises:
            None: Rendering is a pure formatting operation.
        """
        return render_module_status_markdown(self.snapshot_details())
