from __future__ import annotations

from pathlib import Path

from robot_sim.infra.docs_manifest import (
    CANONICAL_DOCS,
    DOCS_FRONT_MATTER_REQUIRED_KEYS,
    DOC_SPECIFIC_SEMANTIC_CONTRACTS,
    ENTRY_PAGE_REQUIRED_KEYS,
    ENTRY_PAGES,
    GENERATED_DOC_REQUIRED_KEYS,
    GENERATED_DOCS,
    semantic_scope_docs,
)

SEMANTIC_SCOPE_DOCS: tuple[str, ...] = semantic_scope_docs()
ENTRY_PAGE_MAX_NONEMPTY_LINES = 15
ENTRY_PAGE_MAX_HEADINGS = 1

def parse_front_matter(text: str) -> dict[str, str]:
    if not text.startswith('---\n'):
        return {}
    end = text.find('\n---\n', 4)
    if end == -1:
        return {}
    block = text[4:end]
    values: dict[str, str] = {}
    for raw_line in block.splitlines():
        line = raw_line.strip()
        if not line or ':' not in line:
            continue
        key, value = line.split(':', 1)
        values[key.strip()] = value.strip()
    return values


def _require_keys(path: Path, metadata: dict[str, str], keys: tuple[str, ...]) -> list[str]:
    errors: list[str] = []
    for key in keys:
        if key not in metadata or not metadata[key]:
            errors.append(f'{path.as_posix()} missing front matter key: {key}')
    return errors


def _body_after_front_matter(text: str) -> str:
    if not text.startswith('---\n'):
        return text
    end = text.find('\n---\n', 4)
    if end == -1:
        return text
    return text[end + 5 :]


def _verify_specific_semantic_markers(root: Path) -> list[str]:
    errors: list[str] = []
    for rel, contract in DOC_SPECIFIC_SEMANTIC_CONTRACTS.items():
        path = root / rel
        if not path.exists():
            errors.append(f'missing semantic contract doc: {rel}')
            continue
        text = path.read_text(encoding='utf-8')
        for marker in contract.get('required', ()):  # pragma: no branch - fixed schema
            if marker not in text:
                errors.append(f'{rel} missing semantic contract marker: {marker}')
        for marker in contract.get('forbidden', ()):
            if marker in text:
                errors.append(f'{rel} contains stale semantic marker: {marker}')
    return errors


def _verify_semantic_scope_registration(root: Path) -> list[str]:
    errors: list[str] = []
    expected = set(SEMANTIC_SCOPE_DOCS)
    actual = {path.relative_to(root).as_posix() for path in (root / 'docs').rglob('*.md')}
    unexpected = sorted(actual - expected)
    missing = sorted(expected - actual)
    for rel in unexpected:
        errors.append(f'unregistered explanatory doc outside semantic scope: {rel}')
    for rel in missing:
        errors.append(f'known explanatory doc missing from docs tree: {rel}')
    return errors


def _verify_generic_semantic_policies(root: Path) -> list[str]:
    errors: list[str] = []
    for rel in SEMANTIC_SCOPE_DOCS:
        path = root / rel
        if not path.exists():
            continue
        text = path.read_text(encoding='utf-8')
        body = _body_after_front_matter(text)
        nonempty_lines = [line for line in body.splitlines() if line.strip()]
        heading_count = sum(1 for line in nonempty_lines if line.startswith('## '))

        if '# ' not in body:
            errors.append(f'{rel} missing top-level title heading')

        if rel in ENTRY_PAGES:
            target = ENTRY_PAGES[rel]
            if target.startswith('docs/generated/'):
                required_markers = (
                    '本文件是稳定入口页。',
                    'canonical generated doc:',
                    'regeneration source:',
                    'editing policy:',
                    '请跳转阅读：',
                )
            else:
                required_markers = ('> Legacy entry page.',)
            for marker in required_markers:
                if marker not in text:
                    errors.append(f'{rel} missing entry-page semantic marker: {marker}')
            if heading_count > ENTRY_PAGE_MAX_HEADINGS:
                errors.append(
                    f'{rel} entry-page semantic drift: expected <= {ENTRY_PAGE_MAX_HEADINGS} secondary headings, got {heading_count}'
                )
            if len(nonempty_lines) > ENTRY_PAGE_MAX_NONEMPTY_LINES:
                errors.append(
                    f'{rel} entry-page semantic drift: expected <= {ENTRY_PAGE_MAX_NONEMPTY_LINES} non-empty lines, got {len(nonempty_lines)}'
                )
            continue

        if rel in GENERATED_DOCS:
            metadata = parse_front_matter(text)
            errors.extend(_require_keys(path, metadata, GENERATED_DOC_REQUIRED_KEYS))
            if '> Legacy entry page.' in text or '本文件是稳定入口页。' in text:
                errors.append(f'{rel} generated doc leaked entry-page marker')
            if len(nonempty_lines) < 5:
                errors.append(f'{rel} generated doc too small to act as canonical contract surface')
            continue

        if rel in CANONICAL_DOCS:
            if '> Legacy entry page.' in text or '本文件是稳定入口页。' in text:
                errors.append(f'{rel} canonical doc leaked entry-page marker')
            if len(nonempty_lines) < 6:
                errors.append(f'{rel} canonical doc too small to act as explanatory source of truth')
            if not any(marker in body for marker in ('\n## ', '\n- ', '\n1. ', '\n| --- |', '阅读建议：')):
                errors.append(f'{rel} canonical doc missing explanatory structural markers')
    return errors


def verify_docs_information_architecture(project_root: str | Path) -> list[str]:
    root = Path(project_root)
    errors: list[str] = []

    for rel in CANONICAL_DOCS:
        path = root / rel
        if not path.exists():
            errors.append(f'missing canonical doc: {rel}')
            continue
        metadata = parse_front_matter(path.read_text(encoding='utf-8'))
        errors.extend(_require_keys(path, metadata, DOCS_FRONT_MATTER_REQUIRED_KEYS))
        if metadata.get('status') != 'canonical':
            errors.append(f'{rel} expected status=canonical, got {metadata.get("status")!r}')

    for rel in GENERATED_DOCS:
        path = root / rel
        if not path.exists():
            errors.append(f'missing generated doc: {rel}')
            continue
        metadata = parse_front_matter(path.read_text(encoding='utf-8'))
        errors.extend(_require_keys(path, metadata, GENERATED_DOC_REQUIRED_KEYS))
        if metadata.get('status') != 'generated':
            errors.append(f'{rel} expected status=generated, got {metadata.get("status")!r}')

    for rel, target in ENTRY_PAGES.items():
        path = root / rel
        if not path.exists():
            errors.append(f'missing entry page: {rel}')
            continue
        text = path.read_text(encoding='utf-8')
        metadata = parse_front_matter(text)
        errors.extend(_require_keys(path, metadata, ENTRY_PAGE_REQUIRED_KEYS))
        if metadata.get('status') != 'entry-page':
            errors.append(f'{rel} expected status=entry-page, got {metadata.get("status")!r}')
        if metadata.get('canonical_target') != target:
            errors.append(f'{rel} canonical_target drifted: expected {target!r}, got {metadata.get("canonical_target")!r}')
        if target not in text:
            errors.append(f'{rel} body no longer references canonical target {target!r}')

    index_path = root / 'docs' / 'index.md'
    index_text = index_path.read_text(encoding='utf-8') if index_path.exists() else ''
    if 'docs/governance/documentation-governance.md' not in index_text:
        errors.append('docs/index.md missing documentation governance navigation entry')

    readme_path = root / 'README.md'
    if readme_path.exists():
        readme = readme_path.read_text(encoding='utf-8')
        for marker in ('docs/index.md', 'docs/governance/documentation-governance.md', 'verify_docs_information_architecture.py'):
            if marker not in readme:
                errors.append(f'README missing docs architecture marker: {marker}')
    else:
        errors.append('missing README.md')

    errors.extend(_verify_semantic_scope_registration(root))
    errors.extend(_verify_generic_semantic_policies(root))
    errors.extend(_verify_specific_semantic_markers(root))
    return errors
