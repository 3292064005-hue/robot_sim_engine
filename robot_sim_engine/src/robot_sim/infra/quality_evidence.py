from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
import hashlib
import json
import platform
import sys
from typing import Iterable

from robot_sim.infra.release_package import iter_release_files


def source_tree_fingerprint(repo_root: str | Path) -> dict[str, str]:
    """Return a deterministic fingerprint for the checked-in source tree.

    The fingerprint intentionally excludes ``artifacts/`` so freshly generated evidence can
    still be validated against the same source tree that produced it.
    """
    root = Path(repo_root).resolve()
    hasher = hashlib.sha256()
    file_count = 0
    for rel in iter_release_files(root):
        if rel.parts and rel.parts[0] == 'artifacts':
            continue
        src = root / rel
        hasher.update(rel.as_posix().encode('utf-8'))
        hasher.update(b'\0')
        hasher.update(src.read_bytes())
        hasher.update(b'\0')
        file_count += 1
    return {
        'repo_root': str(root),
        'source_tree_fingerprint': hasher.hexdigest(),
        'source_tree_file_count': str(file_count),
    }


def runtime_environment_fingerprint(repo_root: str | Path | None = None) -> dict[str, str]:
    """Return a compact runtime fingerprint used by quality evidence and perf budgets."""
    payload = {
        'python_version': platform.python_version(),
        'python_major_minor': '.'.join(platform.python_version().split('.')[:2]),
        'platform_system': platform.system().lower(),
        'platform_machine': platform.machine().lower(),
        'executable': sys.executable,
        'generated_at_utc': datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace('+00:00', 'Z'),
    }
    if repo_root is not None:
        payload.update(source_tree_fingerprint(repo_root))
    return payload


@dataclass(frozen=True)
class QualityEvidenceRecord:
    """Serializable gate-evidence record shared by benchmark/governance/release tooling."""

    evidence_id: str
    category: str
    ok: bool
    environment: dict[str, str] = field(default_factory=runtime_environment_fingerprint)
    details: dict[str, object] = field(default_factory=dict)

    def summary(self) -> dict[str, object]:
        return {
            'evidence_id': str(self.evidence_id),
            'category': str(self.category),
            'ok': bool(self.ok),
            'environment': dict(self.environment or {}),
            'details': dict(self.details or {}),
        }


def read_quality_evidence(path: str | Path) -> tuple[QualityEvidenceRecord, ...]:
    payload = json.loads(Path(path).read_text(encoding='utf-8'))
    return tuple(
        QualityEvidenceRecord(
            evidence_id=str(item.get('evidence_id', '')),
            category=str(item.get('category', 'unknown')),
            ok=bool(item.get('ok', False)),
            environment=dict(item.get('environment', {}) or {}),
            details=dict(item.get('details', {}) or {}),
        )
        for item in payload
    )


def write_quality_evidence(path: str | Path, records: Iterable[QualityEvidenceRecord]) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    payload = [record.summary() for record in records]
    target.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding='utf-8')
    return target


def render_quality_evidence_markdown(records: Iterable[QualityEvidenceRecord]) -> str:
    lines = ['# Quality Evidence', '']
    for record in records:
        lines.append(f"## {record.evidence_id}")
        lines.append('')
        lines.append(f"- category: `{record.category}`")
        lines.append(f"- ok: `{record.ok}`")
        env = ', '.join(f"{k}={v}" for k, v in sorted(record.environment.items()))
        lines.append(f"- environment: `{env}`")
        if record.details:
            lines.append('- details:')
            lines.append('```json')
            lines.append(json.dumps(record.details, indent=2, sort_keys=True))
            lines.append('```')
        lines.append('')
    return '\n'.join(lines).rstrip() + '\n'


def write_quality_evidence_markdown(path: str | Path, records: Iterable[QualityEvidenceRecord]) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    record_list = tuple(records)
    target.write_text(render_quality_evidence_markdown(record_list), encoding='utf-8')
    return target
