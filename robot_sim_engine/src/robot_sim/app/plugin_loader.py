from __future__ import annotations

from dataclasses import dataclass, field
import inspect
from importlib import import_module
from importlib.metadata import entry_points
from pathlib import Path
from typing import Callable

import yaml

from robot_sim.application.services.runtime_feature_service import RuntimeFeaturePolicy
from robot_sim.app.version_catalog import current_version_catalog

_SUPPORTED_PLUGIN_API_VERSION = 'v1'
_SUPPORTED_PLUGIN_KINDS = {'solver', 'planner', 'importer', 'scene_backend', 'collision_backend'}
_SUPPORTED_PLUGIN_STATUSES = {'stable', 'beta', 'experimental', 'internal', 'deprecated'}
_ALWAYS_ALLOWED_PLUGIN_SOURCES = {'builtin', 'shipped_plugin'}
_EXTERNAL_PLUGIN_SOURCES = {'external', 'entry_point'}
_SUPPORTED_PLUGIN_SOURCES = _ALWAYS_ALLOWED_PLUGIN_SOURCES | _EXTERNAL_PLUGIN_SOURCES


@dataclass(frozen=True)
class PluginManifest:
    """Controlled plugin declaration loaded from configuration."""

    plugin_id: str
    kind: str
    factory: str = ''
    entry_point: str = ''
    aliases: tuple[str, ...] = ()
    metadata: dict[str, object] = field(default_factory=dict)
    source: str = 'external'
    replace: bool = False
    enabled_profiles: tuple[str, ...] = ()
    status: str = 'stable'
    api_version: str = _SUPPORTED_PLUGIN_API_VERSION
    sdk_contract_version: str = _SUPPORTED_PLUGIN_API_VERSION
    min_host_version: str = ''
    required_host_capabilities: tuple[str, ...] = ()
    optional_host_capabilities: tuple[str, ...] = ()

    def allows_profile(self, profile: str) -> bool:
        if not self.enabled_profiles:
            return True
        return str(profile) in set(self.enabled_profiles)

    @property
    def is_external(self) -> bool:
        return self.source not in _ALWAYS_ALLOWED_PLUGIN_SOURCES


@dataclass(frozen=True)
class PluginRegistration:
    """Resolved plugin payload ready for a registry."""

    plugin_id: str
    instance: object
    aliases: tuple[str, ...]
    metadata: dict[str, object]
    negotiated_host_capabilities: tuple[str, ...] = ()
    missing_optional_host_capabilities: tuple[str, ...] = ()
    replace: bool = False
    source: str = 'external'


class PluginLoader:
    """Load declared plugins under a strict allowlist and API-version contract."""

    def __init__(
        self,
        config_path: str | Path | tuple[str | Path, ...] | list[str | Path],
        *,
        policy: RuntimeFeaturePolicy,
        host_version: str | None = None,
    ) -> None:
        raw_paths = config_path if isinstance(config_path, (list, tuple)) else (config_path,)
        self._config_paths = tuple(Path(path) for path in raw_paths)
        self._policy = policy
        self._host_version = str(host_version or current_version_catalog().app_version or '').strip()

    def manifests(self, kind: str) -> tuple[PluginManifest, ...]:
        manifests: list[PluginManifest] = []
        for manifest in self._load_manifests():
            enabled, _reason = self._decision_for_manifest(manifest, requested_kind=kind)
            if enabled:
                manifests.append(manifest)
        return tuple(manifests)

    def registrations(self, kind: str, **context) -> tuple[PluginRegistration, ...]:
        registrations: list[PluginRegistration] = []
        for manifest in self.manifests(kind):
            factory = self._resolve_factory(manifest)
            negotiated = self._negotiated_capabilities(manifest)
            payload = self._call_factory(factory, {**context, **negotiated})
            instance = payload['instance'] if isinstance(payload, dict) else payload
            metadata = dict(manifest.metadata)
            aliases = manifest.aliases
            if isinstance(payload, dict):
                metadata.update(dict(payload.get('metadata', {}) or {}))
                aliases = tuple(str(alias) for alias in payload.get('aliases', aliases) or ())
            metadata.setdefault('status', manifest.status)
            metadata.setdefault('source', manifest.source)
            metadata.setdefault('api_version', manifest.api_version)
            metadata.setdefault('sdk_contract_version', manifest.sdk_contract_version)
            metadata.setdefault('min_host_version', manifest.min_host_version)
            metadata.setdefault('kind', manifest.kind)
            metadata.setdefault('required_host_capabilities', list(manifest.required_host_capabilities))
            metadata.setdefault('optional_host_capabilities', list(manifest.optional_host_capabilities))
            metadata.setdefault('negotiated_host_capabilities', list(negotiated['negotiated_host_capabilities']))
            metadata.setdefault('missing_optional_host_capabilities', list(negotiated['missing_optional_host_capabilities']))
            registrations.append(
                PluginRegistration(
                    plugin_id=manifest.plugin_id,
                    instance=instance,
                    aliases=aliases,
                    metadata=metadata,
                    negotiated_host_capabilities=tuple(negotiated['negotiated_host_capabilities']),
                    missing_optional_host_capabilities=tuple(negotiated['missing_optional_host_capabilities']),
                    replace=manifest.replace,
                    source=manifest.source,
                )
            )
        return tuple(registrations)

    def audit(self, kind: str | None = None) -> tuple[dict[str, object], ...]:
        rows: list[dict[str, object]] = []
        for manifest in self._load_manifests():
            enabled, reason = self._decision_for_manifest(manifest, requested_kind=kind)
            if kind is not None and manifest.kind != str(kind):
                continue
            rows.append(
                {
                    'id': manifest.plugin_id,
                    'kind': manifest.kind,
                    'status': manifest.status,
                    'enabled': enabled,
                    'reason': reason,
                    'source': manifest.source,
                    'replace': manifest.replace,
                    'enabled_profiles': list(manifest.enabled_profiles),
                    'aliases': list(manifest.aliases),
                    'sdk_contract_version': manifest.sdk_contract_version,
                    'min_host_version': manifest.min_host_version,
                    'host_version': self._host_version,
                    'metadata': dict(manifest.metadata),
                    'required_host_capabilities': list(manifest.required_host_capabilities),
                    'optional_host_capabilities': list(manifest.optional_host_capabilities),
                    'negotiated_host_capabilities': list(self._negotiated_capabilities(manifest)['negotiated_host_capabilities']),
                    'missing_optional_host_capabilities': list(self._negotiated_capabilities(manifest)['missing_optional_host_capabilities']),
                }
            )
        return tuple(rows)

    def _load_manifests(self) -> tuple[PluginManifest, ...]:
        manifests: list[PluginManifest] = []
        seen_ids: set[str] = set()
        for config_path in self._config_paths:
            if not config_path.exists():
                continue
            payload = yaml.safe_load(config_path.read_text(encoding='utf-8')) or {}
            if not isinstance(payload, dict):
                raise ValueError(f'plugin manifest must be a mapping: {config_path}')
            raw_plugins = payload.get('plugins', ())
            if raw_plugins is None:
                continue
            if not isinstance(raw_plugins, list):
                raise ValueError(f'plugins section must be a list: {config_path}')
            for entry in raw_plugins:
                if not isinstance(entry, dict):
                    raise ValueError(f'plugin entry must be a mapping: {config_path}')
                factory = str(entry.get('factory', '') or '')
                entry_point_ref = str(entry.get('entry_point', '') or '')
                if bool(factory) == bool(entry_point_ref):
                    raise ValueError(f'plugin entry must define exactly one of factory or entry_point: {config_path}')
                plugin_id = str(entry['id'])
                if plugin_id in seen_ids:
                    raise ValueError(f'duplicate plugin id in manifest chain: {plugin_id}')
                seen_ids.add(plugin_id)
                source = str(entry.get('source', 'entry_point' if entry_point_ref else 'external'))
                manifest = PluginManifest(
                    plugin_id=plugin_id,
                    kind=str(entry['kind']),
                    factory=factory,
                    entry_point=entry_point_ref,
                    aliases=tuple(str(alias) for alias in entry.get('aliases', ()) or ()),
                    metadata=dict(entry.get('metadata', {}) or {}),
                    source=source,
                    replace=bool(entry.get('replace', False)),
                    enabled_profiles=tuple(str(profile) for profile in entry.get('enabled_profiles', ()) or ()),
                    status=str(entry.get('status', 'stable')),
                    api_version=str(entry.get('api_version', _SUPPORTED_PLUGIN_API_VERSION) or _SUPPORTED_PLUGIN_API_VERSION),
                    sdk_contract_version=str(entry.get('sdk_contract_version', entry.get('api_version', _SUPPORTED_PLUGIN_API_VERSION)) or entry.get('api_version', _SUPPORTED_PLUGIN_API_VERSION) or _SUPPORTED_PLUGIN_API_VERSION),
                    min_host_version=str(entry.get('min_host_version', '') or ''),
                    required_host_capabilities=tuple(str(item) for item in entry.get('required_host_capabilities', ()) or ()),
                    optional_host_capabilities=tuple(str(item) for item in entry.get('optional_host_capabilities', ()) or ()),
                )
                self._validate_manifest(manifest)
                manifests.append(manifest)
        return tuple(manifests)

    def _decision_for_manifest(self, manifest: PluginManifest, *, requested_kind: str | None) -> tuple[bool, str]:
        if requested_kind is not None and manifest.kind != str(requested_kind):
            return False, 'kind_mismatch'
        if not manifest.allows_profile(self._policy.active_profile):
            return False, 'profile_disabled'
        if not self._policy.allows_plugin_status(manifest.status):
            return False, 'status_disabled'
        if manifest.is_external and not self._policy.plugin_discovery_enabled:
            return False, 'discovery_disabled'
        if manifest.min_host_version and not self._host_version_satisfies(manifest.min_host_version):
            return False, 'host_version_too_old'
        host_capabilities = set(getattr(self._policy, 'host_capabilities', ()) or ())
        if any(capability not in host_capabilities for capability in manifest.required_host_capabilities):
            return False, 'required_host_capability_missing'
        return True, 'enabled'

    def _negotiated_capabilities(self, manifest: PluginManifest) -> dict[str, tuple[str, ...]]:
        host_capabilities = tuple(getattr(self._policy, 'host_capabilities', ()) or ())
        host_set = set(host_capabilities)
        negotiated = []
        for capability in (*manifest.required_host_capabilities, *manifest.optional_host_capabilities):
            if capability in host_set and capability not in negotiated:
                negotiated.append(capability)
        missing_optional = [capability for capability in manifest.optional_host_capabilities if capability not in host_set]
        return {
            'host_capabilities': host_capabilities,
            'negotiated_host_capabilities': tuple(negotiated),
            'missing_optional_host_capabilities': tuple(missing_optional),
        }

    def _resolve_factory(self, manifest: PluginManifest) -> Callable[..., object]:
        if manifest.entry_point:
            return self._resolve_entry_point(manifest.entry_point)
        module_name, _, attr_name = str(manifest.factory).partition(':')
        if not module_name or not attr_name:
            raise ValueError(f'invalid plugin factory path: {manifest.factory}')
        module = import_module(module_name)
        factory = getattr(module, attr_name)
        if not callable(factory):
            raise TypeError(f'plugin factory is not callable: {manifest.factory}')
        return factory

    @staticmethod
    def _resolve_entry_point(entry_point_ref: str) -> Callable[..., object]:
        group, _, name = str(entry_point_ref).partition(':')
        if not group or not name:
            raise ValueError(f'invalid plugin entry_point reference: {entry_point_ref}')
        discovered = entry_points()
        if hasattr(discovered, 'select'):
            matches = tuple(discovered.select(group=group, name=name))
        else:
            matches = tuple(ep for ep in discovered.get(group, ()) if ep.name == name)
        if not matches:
            raise ValueError(f'plugin entry point not found: {entry_point_ref}')
        payload = matches[0].load()
        if callable(payload):
            return payload
        return lambda **_context: payload

    @staticmethod
    def _call_factory(factory: Callable[..., object], context: dict[str, object]) -> object:
        signature = inspect.signature(factory)
        parameters = tuple(signature.parameters.values())
        accepts_var_kw = any(param.kind is inspect.Parameter.VAR_KEYWORD for param in parameters)
        required_keyword_only = [
            param.name
            for param in parameters
            if param.kind is inspect.Parameter.KEYWORD_ONLY and param.default is inspect._empty
        ]
        required_without_defaults = [
            param.name
            for param in parameters
            if param.kind in (inspect.Parameter.POSITIONAL_ONLY, inspect.Parameter.POSITIONAL_OR_KEYWORD)
            and param.default is inspect._empty
        ]
        accepted_context = {name: value for name, value in context.items() if name in signature.parameters or accepts_var_kw}
        missing_keyword_only = [name for name in required_keyword_only if name not in accepted_context]
        missing_required_positional = [name for name in required_without_defaults if name not in accepted_context]
        if not missing_keyword_only and not missing_required_positional:
            return factory(**accepted_context)
        if not required_without_defaults and not required_keyword_only:
            return factory()
        raise ValueError(
            f'plugin factory signature incompatible with supported calling modes: {factory!r}; '
            f'required_positional={required_without_defaults}; required_keyword_only={required_keyword_only}'
        )

    def _host_version_satisfies(self, min_host_version: str) -> bool:
        host_tuple = self._parse_version(self._host_version)
        required_tuple = self._parse_version(min_host_version)
        if host_tuple is None or required_tuple is None:
            return False
        return host_tuple >= required_tuple

    @staticmethod
    def _parse_version(text: str) -> tuple[int, int, int] | None:
        raw = str(text or '').strip()
        if not raw:
            return None
        parts = raw.split('.')
        normalized: list[int] = []
        for item in parts[:3]:
            if not item.isdigit():
                return None
            normalized.append(int(item))
        while len(normalized) < 3:
            normalized.append(0)
        return tuple(normalized)

    @staticmethod
    def _validate_manifest(manifest: PluginManifest) -> None:
        if manifest.kind not in _SUPPORTED_PLUGIN_KINDS:
            raise ValueError(
                f'unsupported plugin kind for {manifest.plugin_id!r}: {manifest.kind!r}; '
                f'supported={tuple(sorted(_SUPPORTED_PLUGIN_KINDS))!r}'
            )
        if manifest.status not in _SUPPORTED_PLUGIN_STATUSES:
            raise ValueError(
                f'unsupported plugin status for {manifest.plugin_id!r}: {manifest.status!r}; '
                f'supported={tuple(sorted(_SUPPORTED_PLUGIN_STATUSES))!r}'
            )
        if manifest.source not in _SUPPORTED_PLUGIN_SOURCES:
            raise ValueError(
                f'unsupported plugin source for {manifest.plugin_id!r}: {manifest.source!r}; '
                f'supported={tuple(sorted(_SUPPORTED_PLUGIN_SOURCES))!r}'
            )
        if manifest.api_version != _SUPPORTED_PLUGIN_API_VERSION:
            raise ValueError(
                f'unsupported plugin api_version for {manifest.plugin_id!r}: {manifest.api_version!r}; '
                f'supported={_SUPPORTED_PLUGIN_API_VERSION!r}'
            )
        if manifest.sdk_contract_version != _SUPPORTED_PLUGIN_API_VERSION:
            raise ValueError(
                f'unsupported plugin sdk_contract_version for {manifest.plugin_id!r}: {manifest.sdk_contract_version!r}; '
                f'supported={_SUPPORTED_PLUGIN_API_VERSION!r}'
            )
        if manifest.min_host_version and PluginLoader._parse_version(manifest.min_host_version) is None:
            raise ValueError(
                f'invalid plugin min_host_version for {manifest.plugin_id!r}: {manifest.min_host_version!r}; '
                'expected dotted numeric version like 0.7.0'
            )
        if manifest.source in _EXTERNAL_PLUGIN_SOURCES and not (manifest.factory or manifest.entry_point):
            raise ValueError(f'plugin manifest missing load target: {manifest.plugin_id!r}')
