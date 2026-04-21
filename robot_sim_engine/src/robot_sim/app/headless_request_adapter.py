from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Mapping

import yaml


ErrorFactory = Callable[[str], Exception] | type[Exception]


@dataclass(frozen=True)
class HeadlessRequestContractAdapter:
    """Load machine-readable headless request payloads into one canonical mapping.

    The adapter is intentionally transport-focused: it performs no business validation and does
    not require the application container. This allows CLI callers to reject malformed request
    payloads *before* runtime bootstrap, which keeps headless error contracts deterministic.

    Args:
        error_factory: Exception type or callable used to materialize request-contract failures.

    Boundary behavior:
        When both ``request_file`` and ``request_json`` are omitted, the adapter returns an empty
        mapping so downstream workflows can rely on their own defaults. Inline JSON and file-based
        input remain mutually exclusive.
    """

    error_factory: ErrorFactory

    def load(
        self,
        path: str | Path | None = None,
        *,
        request_file: str | Path | None = None,
        request_json: str | None = None,
    ) -> dict[str, object]:
        """Load one request payload from JSON text or a JSON/YAML file.

        Args:
            path: Backward-compatible positional file path.
            request_file: Explicit JSON/YAML request file path.
            request_json: Inline JSON mapping payload.

        Returns:
            dict[str, object]: Normalized request mapping.

        Raises:
            Exception: An instance from ``error_factory`` when the request transport payload is
                malformed, missing, or not representable as a mapping.
        """
        resolved_path = request_file if request_file is not None else path
        if resolved_path is not None and request_json is not None:
            self._raise('request_file and request_json are mutually exclusive')
        if request_json is not None:
            payload = self._parse_inline_json(request_json)
        elif resolved_path is not None:
            payload = self._parse_file(Path(resolved_path))
        else:
            payload = {}
        return self._ensure_mapping(payload)

    def _parse_inline_json(self, request_json: str) -> object:
        try:
            return json.loads(request_json or '{}')
        except json.JSONDecodeError as exc:
            self._raise(f'invalid request_json: {exc.msg} at line {exc.lineno} column {exc.colno}')

    def _parse_file(self, request_path: Path) -> object:
        expanded = request_path.expanduser()
        if not expanded.exists():
            self._raise(f'request file not found: {expanded}')
        try:
            text = expanded.read_text(encoding='utf-8')
        except OSError as exc:
            self._raise(f'failed to read request file {expanded}: {exc}')
        suffix = expanded.suffix.lower()
        if suffix == '.json':
            try:
                return json.loads(text or '{}')
            except json.JSONDecodeError as exc:
                self._raise(f'invalid JSON request file {expanded}: {exc.msg} at line {exc.lineno} column {exc.colno}')
        try:
            payload = yaml.safe_load(text)
            return {} if payload is None else payload
        except yaml.YAMLError as exc:
            self._raise(f'invalid YAML request file {expanded}: {exc}')

    def _ensure_mapping(self, payload: object) -> dict[str, object]:
        if payload is None:
            return {}
        if not isinstance(payload, Mapping):
            self._raise('request payload must be a mapping object')
        return {str(key): value for key, value in payload.items()}

    def _raise(self, message: str) -> None:
        raise self.error_factory(message)
