from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

from robot_sim.application.services.config_service import ConfigService

<<<<<<< HEAD
_SUPPORTED_PLUGIN_STATUSES = ('stable', 'beta', 'experimental', 'internal', 'deprecated')
_DEFAULT_PLUGIN_STATUS_ALLOWLIST = ('stable', 'deprecated')

=======
>>>>>>> 3ed78e647985c6d680c085e4480d898855278db3

@dataclass(frozen=True)
class RuntimeFeaturePolicy:
    """Profile-scoped runtime feature toggles.

    Attributes:
        active_profile: Active configuration profile.
        experimental_modules_enabled: Whether experimental modules may be mounted/used.
        experimental_backends_enabled: Whether experimental backends may be advertised as available.
        plugin_discovery_enabled: Whether externally declared plugins may be discovered and loaded.
        contract_doc_autogen_enabled: Whether CI/profile expects contract docs to be regenerated.
<<<<<<< HEAD
        plugin_status_allowlist: Plugin rollout statuses allowed for the active profile.
=======
>>>>>>> 3ed78e647985c6d680c085e4480d898855278db3
    """

    active_profile: str = ConfigService.DEFAULT_PROFILE
    experimental_modules_enabled: bool = False
    experimental_backends_enabled: bool = False
    plugin_discovery_enabled: bool = False
    contract_doc_autogen_enabled: bool = False
<<<<<<< HEAD
    plugin_status_allowlist: tuple[str, ...] = _DEFAULT_PLUGIN_STATUS_ALLOWLIST

    @property
    def host_capabilities(self) -> tuple[str, ...]:
        """Return host capability badges exposed to plugin negotiation."""
        capabilities = [f'profile:{self.active_profile}']
        if self.experimental_modules_enabled:
            capabilities.append('experimental_modules')
        if self.experimental_backends_enabled:
            capabilities.append('experimental_backends')
        if self.plugin_discovery_enabled:
            capabilities.append('plugin_discovery')
        if self.contract_doc_autogen_enabled:
            capabilities.append('contract_doc_autogen')
        capabilities.extend(f'plugin_status:{status}' for status in self.plugin_status_allowlist)
        return tuple(capabilities)
=======
>>>>>>> 3ed78e647985c6d680c085e4480d898855278db3

    def as_dict(self) -> dict[str, object]:
        """Return the policy as a serializable mapping."""
        return {
            'active_profile': self.active_profile,
            'experimental_modules_enabled': self.experimental_modules_enabled,
            'experimental_backends_enabled': self.experimental_backends_enabled,
            'plugin_discovery_enabled': self.plugin_discovery_enabled,
            'contract_doc_autogen_enabled': self.contract_doc_autogen_enabled,
<<<<<<< HEAD
            'plugin_status_allowlist': list(self.plugin_status_allowlist),
            'host_capabilities': list(self.host_capabilities),
        }

    def allows_plugin_status(self, status: str) -> bool:
        """Return whether the active profile allows the supplied plugin rollout status."""
        return str(status) in set(self.plugin_status_allowlist)

=======
        }

>>>>>>> 3ed78e647985c6d680c085e4480d898855278db3

class RuntimeFeatureService:
    """Resolve runtime feature toggles from profile overlays."""

<<<<<<< HEAD
    DEFAULT_FEATURES: dict[str, object] = {
=======
    DEFAULT_FEATURES: dict[str, bool] = {
>>>>>>> 3ed78e647985c6d680c085e4480d898855278db3
        'experimental_modules_enabled': False,
        'experimental_backends_enabled': False,
        'plugin_discovery_enabled': False,
        'contract_doc_autogen_enabled': False,
<<<<<<< HEAD
        'plugin_status_allowlist': _DEFAULT_PLUGIN_STATUS_ALLOWLIST,
=======
>>>>>>> 3ed78e647985c6d680c085e4480d898855278db3
    }

    def __init__(self, config_service: ConfigService) -> None:
        self._config_service = config_service

    def load_policy(self) -> RuntimeFeaturePolicy:
        """Load the active runtime feature policy.

        Returns:
            RuntimeFeaturePolicy: Feature toggles merged from default and active profile overlays.

        Raises:
<<<<<<< HEAD
            ValueError: If a profile defines malformed feature flags or plugin status gates.
=======
            ValueError: If a profile defines a non-mapping ``features`` section.
>>>>>>> 3ed78e647985c6d680c085e4480d898855278db3
        """
        merged = dict(self.DEFAULT_FEATURES)
        for profile_name in (ConfigService.DEFAULT_PROFILE, self._config_service.profile):
            overlay = self._features_overlay(profile_name)
            if overlay:
                merged.update(overlay)
        return RuntimeFeaturePolicy(
            active_profile=self._config_service.profile,
            experimental_modules_enabled=bool(merged['experimental_modules_enabled']),
            experimental_backends_enabled=bool(merged['experimental_backends_enabled']),
            plugin_discovery_enabled=bool(merged['plugin_discovery_enabled']),
            contract_doc_autogen_enabled=bool(merged['contract_doc_autogen_enabled']),
<<<<<<< HEAD
            plugin_status_allowlist=tuple(str(item) for item in merged['plugin_status_allowlist']),
        )

    def _features_overlay(self, profile_name: str) -> dict[str, object]:
=======
        )

    def _features_overlay(self, profile_name: str) -> dict[str, bool]:
>>>>>>> 3ed78e647985c6d680c085e4480d898855278db3
        payload = self._config_service.load_profile_yaml(profile_name)
        if not payload:
            return {}
        features = payload.get('features', {})
        if features is None:
            return {}
        if not isinstance(features, Mapping):
            raise ValueError(f'profile features must be a mapping: {profile_name}')
<<<<<<< HEAD
        normalized: dict[str, object] = {
            'experimental_modules_enabled': bool(features.get('experimental_modules_enabled', self.DEFAULT_FEATURES['experimental_modules_enabled'])),
            'experimental_backends_enabled': bool(features.get('experimental_backends_enabled', self.DEFAULT_FEATURES['experimental_backends_enabled'])),
            'plugin_discovery_enabled': bool(features.get('plugin_discovery_enabled', self.DEFAULT_FEATURES['plugin_discovery_enabled'])),
            'contract_doc_autogen_enabled': bool(features.get('contract_doc_autogen_enabled', self.DEFAULT_FEATURES['contract_doc_autogen_enabled'])),
            'plugin_status_allowlist': self._normalize_plugin_status_allowlist(
                features.get('plugin_status_allowlist', self.DEFAULT_FEATURES['plugin_status_allowlist']),
                profile_name,
            ),
        }
        return normalized

    @staticmethod
    def _normalize_plugin_status_allowlist(raw_value: object, profile_name: str) -> tuple[str, ...]:
        """Normalize profile plugin rollout gates into a validated tuple.

        Args:
            raw_value: Raw YAML feature value.
            profile_name: Profile name for error reporting.

        Returns:
            tuple[str, ...]: Validated ordered tuple of allowed plugin statuses.

        Raises:
            ValueError: If the profile provides malformed or unsupported statuses.
        """
        if raw_value is None:
            return _DEFAULT_PLUGIN_STATUS_ALLOWLIST
        if isinstance(raw_value, str):
            candidate_items = [raw_value]
        elif isinstance(raw_value, (list, tuple, set)):
            candidate_items = [str(item) for item in raw_value]
        else:
            raise ValueError(f'plugin_status_allowlist must be a sequence of strings: {profile_name}')
        normalized: list[str] = []
        for item in candidate_items:
            status = str(item).strip()
            if not status:
                raise ValueError(f'plugin_status_allowlist contains an empty value: {profile_name}')
            if status not in _SUPPORTED_PLUGIN_STATUSES:
                raise ValueError(
                    f'unsupported plugin status in allowlist for {profile_name}: {status!r}; '
                    f'supported={_SUPPORTED_PLUGIN_STATUSES!r}'
                )
            if status not in normalized:
                normalized.append(status)
        if not normalized:
            raise ValueError(f'plugin_status_allowlist must not be empty: {profile_name}')
        return tuple(normalized)
=======
        normalized: dict[str, bool] = {}
        for key, default_value in self.DEFAULT_FEATURES.items():
            if key in features:
                normalized[key] = bool(features[key])
            else:
                normalized[key] = bool(default_value)
        return normalized
>>>>>>> 3ed78e647985c6d680c085e4480d898855278db3
