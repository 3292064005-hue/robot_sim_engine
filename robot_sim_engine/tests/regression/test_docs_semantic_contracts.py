from __future__ import annotations

from pathlib import Path
import shutil

from robot_sim.infra.docs_information_architecture import SEMANTIC_SCOPE_DOCS, verify_docs_information_architecture


def test_docs_semantic_contracts_are_current(project_root: Path) -> None:
    assert verify_docs_information_architecture(project_root) == []


def test_all_docs_markdown_files_are_registered_for_semantic_coverage(project_root: Path) -> None:
    actual = {path.relative_to(project_root).as_posix() for path in (project_root / 'docs').rglob('*.md')}
    assert actual == set(SEMANTIC_SCOPE_DOCS)


def test_importer_architecture_doc_semantic_drift_is_rejected(project_root: Path, tmp_path: Path) -> None:
    repo_copy = tmp_path / 'repo'
    shutil.copytree(project_root, repo_copy)
    doc_path = repo_copy / 'docs' / 'architecture' / 'importer-model.md'
    text = doc_path.read_text(encoding='utf-8')
    text = text.replace('branched_tree_supported: true', 'branched_tree_supported: false', 1)
    doc_path.write_text(text, encoding='utf-8')

    errors = verify_docs_information_architecture(repo_copy)
    assert any('contains stale semantic marker: branched_tree_supported: false' in item for item in errors)


def test_legacy_entry_page_bloat_is_rejected(project_root: Path, tmp_path: Path) -> None:
    repo_copy = tmp_path / 'repo'
    shutil.copytree(project_root, repo_copy)
    doc_path = repo_copy / 'docs' / 'planning_scene.md'
    text = doc_path.read_text(encoding='utf-8')
    text += '\n额外说明 A\n额外说明 B\n额外说明 C\n额外说明 D\n额外说明 E\n额外说明 F\n额外说明 G\n额外说明 H\n'
    doc_path.write_text(text, encoding='utf-8')

    errors = verify_docs_information_architecture(repo_copy)
    assert any('entry-page semantic drift: expected <= 15 non-empty lines' in item for item in errors)


def test_docs_gate_description_drift_is_rejected(project_root: Path, tmp_path: Path) -> None:
    repo_copy = tmp_path / 'repo'
    shutil.copytree(project_root, repo_copy)
    doc_path = repo_copy / 'docs' / 'guides' / 'testing-and-quality.md'
    text = doc_path.read_text(encoding='utf-8')
    text = text.replace('全量说明文档 semantic coverage', 'semantic checks removed', 1)
    doc_path.write_text(text, encoding='utf-8')

    errors = verify_docs_information_architecture(repo_copy)
    assert any('docs/guides/testing-and-quality.md missing semantic contract marker: 全量说明文档 semantic coverage' in item for item in errors)


def test_unregistered_doc_is_rejected(project_root: Path, tmp_path: Path) -> None:
    repo_copy = tmp_path / 'repo'
    shutil.copytree(project_root, repo_copy)
    rogue_doc = repo_copy / 'docs' / 'rogue-note.md'
    rogue_doc.write_text(
        '---\nowner: docs\naudience: all\nstatus: canonical\nsource_of_truth: manual\nlast_reviewed: 2026-04-18\n---\n# Rogue Note\n\nThis file bypasses semantic scope registration.\n',
        encoding='utf-8',
    )

    errors = verify_docs_information_architecture(repo_copy)
    assert any('unregistered explanatory doc outside semantic scope: docs/rogue-note.md' in item for item in errors)
