from __future__ import annotations

from collections.abc import Mapping

from robot_sim.domain.module_governance import governance_for_module
from robot_sim.domain.runtime_contracts import MODULE_STATUSES, render_module_status_markdown


class ModuleStatusService:
    """Provide module-status snapshots for presentation and diagnostics."""

    MODULE_STATUSES: dict[str, object] = MODULE_STATUSES

    def __init__(self, runtime_feature_policy=None, *, quality_gate_results: dict[str, bool] | None = None) -> None:
        self._runtime_feature_policy = runtime_feature_policy
        self._quality_gate_results = {str(key): bool(value) for key, value in dict(quality_gate_results or {}).items()}

    def snapshot(self) -> dict[str, object]:
        """Return the current module-status snapshot.

        Returns:
            dict[str, object]: Module identifier to raw module-status payload mapping.
                Values may be plain status strings or structured status dictionaries.

        Raises:
            None: The snapshot is static runtime metadata.
        """
        return dict(self.MODULE_STATUSES)

    def snapshot_details(self) -> dict[str, dict[str, object]]:
        """Return module statuses together with runtime enablement flags."""
        experimental_enabled = bool(getattr(self._runtime_feature_policy, 'experimental_modules_enabled', False))
        details: dict[str, dict[str, object]] = {}
        for module_id, payload in self.snapshot().items():
            if isinstance(payload, Mapping):
                raw_payload = dict(payload)
                status = str(raw_payload.get('status', 'unknown'))
                default_enabled = bool(status != 'experimental' or experimental_enabled)
                if status == 'experimental' and experimental_enabled:
                    enabled = True
                else:
                    enabled = bool(raw_payload.get('enabled', default_enabled))
                detail = {str(key): value for key, value in raw_payload.items()}
                detail['status'] = status
                detail['enabled'] = enabled
            else:
                status = str(payload)
                enabled = bool(status != 'experimental' or experimental_enabled)
                detail = {'status': status, 'enabled': enabled}
            governance = governance_for_module(str(module_id))
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
