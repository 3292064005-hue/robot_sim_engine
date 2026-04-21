from __future__ import annotations

from pathlib import Path
import shutil
from zipfile import ZipFile

from robot_sim.infra.release_package import build_release_zip, build_verified_release_zip, iter_release_files, should_include_path, stage_release_tree


def test_should_exclude_cache_and_build_artifacts() -> None:
    assert not should_include_path(Path('__pycache__/module.cpython-310.pyc'))
    assert not should_include_path(Path('.pytest_cache/v/cache/nodeids'))
    assert not should_include_path(Path('.mypy_cache/3.10/module.meta.json'))
    assert not should_include_path(Path('.ruff_cache/0.1/index'))
    assert not should_include_path(Path('build/lib/module.py'))
    assert not should_include_path(Path('artifacts/quality_evidence.json'))
    assert not should_include_path(Path('src/robot_sim_engine.egg-info/PKG-INFO'))
    assert not should_include_path(Path('.coverage'))
    assert not should_include_path(Path('FINAL_AUDIT.md'))
    assert not should_include_path(Path('scene_capture.png'))
    assert should_include_path(Path('src/robot_sim/core/fk.py'))


def test_iter_release_files_filters_unwanted_entries(tmp_path: Path) -> None:
    (tmp_path / 'src').mkdir()
    (tmp_path / 'src' / 'kept.py').write_text('print(1)\n', encoding='utf-8')
    (tmp_path / '.pytest_cache').mkdir()
    (tmp_path / '.pytest_cache' / 'state').write_text('x', encoding='utf-8')
    (tmp_path / '__pycache__').mkdir()
    (tmp_path / '__pycache__' / 'junk.pyc').write_bytes(b'x')
    rels = list(iter_release_files(tmp_path))
    assert rels == [Path('src/kept.py')]


def test_build_release_zip_excludes_caches(tmp_path: Path) -> None:
    (tmp_path / 'pkg').mkdir()
    (tmp_path / 'pkg' / 'real.py').write_text('x = 1\n', encoding='utf-8')
    (tmp_path / '__pycache__').mkdir()
    (tmp_path / '__pycache__' / 'junk.pyc').write_bytes(b'x')
    (tmp_path / '.coverage').write_text('data', encoding='utf-8')
    output = tmp_path / 'dist' / 'release.zip'
    build_release_zip(tmp_path, output, top_level_dir='robot_sim_engine')

    with ZipFile(output) as zf:
        names = sorted(zf.namelist())

    assert names == ['robot_sim_engine/pkg/real.py']


def test_exports_directory_is_excluded(tmp_path: Path) -> None:
    (tmp_path / 'exports').mkdir()
    (tmp_path / 'exports' / 'artifact.json').write_text('{}', encoding='utf-8')
    (tmp_path / 'src').mkdir()
    (tmp_path / 'src' / 'kept.py').write_text('print(1)\n', encoding='utf-8')
    rels = list(iter_release_files(tmp_path))
    assert rels == [Path('src/kept.py')]

def test_artifacts_directory_is_excluded(tmp_path: Path) -> None:
    (tmp_path / 'artifacts').mkdir()
    (tmp_path / 'artifacts' / 'artifact.json').write_text('{}', encoding='utf-8')
    (tmp_path / 'src').mkdir()
    (tmp_path / 'src' / 'kept.py').write_text('print(1)\n', encoding='utf-8')
    rels = list(iter_release_files(tmp_path))
    assert rels == [Path('src/kept.py')]


def test_release_zip_excludes_audits_screenshots_and_egg_info(tmp_path: Path) -> None:
    (tmp_path / 'src').mkdir()
    (tmp_path / 'src' / 'kept.py').write_text('print(1)\n', encoding='utf-8')
    (tmp_path / 'scene_capture.png').write_bytes(b'png')
    (tmp_path / 'FINAL_AUDIT.md').write_text('audit', encoding='utf-8')
    (tmp_path / 'src' / 'robot_sim_engine.egg-info').mkdir()
    (tmp_path / 'src' / 'robot_sim_engine.egg-info' / 'PKG-INFO').write_text('meta', encoding='utf-8')

    output = tmp_path / 'release.zip'
    build_release_zip(tmp_path, output, top_level_dir='robot_sim_engine')

    with ZipFile(output) as zf:
        names = sorted(zf.namelist())

    assert names == ['robot_sim_engine/src/kept.py']


def test_release_zip_built_from_project_root_excludes_runtime_exports(project_root: Path, tmp_path: Path) -> None:
    output = tmp_path / 'project-release.zip'
    build_release_zip(project_root, output, top_level_dir='robot_sim_engine')

    with ZipFile(output) as zf:
        names = zf.namelist()

    assert not any(name.startswith('robot_sim_engine/exports/') for name in names)
    assert not any(name.startswith('robot_sim_engine/artifacts/') for name in names)


def test_packaged_config_staging_is_excluded(tmp_path: Path) -> None:
    (tmp_path / 'build' / 'packaged_config_staging').mkdir(parents=True)
    (tmp_path / 'build' / 'packaged_config_staging' / 'app.yaml').write_text('x: 1\n', encoding='utf-8')
    (tmp_path / 'src').mkdir()
    (tmp_path / 'src' / 'kept.py').write_text('print(1)\n', encoding='utf-8')
    rels = list(iter_release_files(tmp_path))
    assert rels == [Path('src/kept.py')]


def test_stage_release_tree_regenerates_stale_contract_docs_in_stage_only(project_root: Path, tmp_path: Path) -> None:
    source_root = tmp_path / 'repo-copy'
    for rel in iter_release_files(project_root):
        dest = source_root / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(project_root / rel, dest)
    stale_doc = source_root / 'docs' / 'generated' / 'capability_matrix.md'
    stale_doc.write_text('stale\n', encoding='utf-8')

    report = stage_release_tree(source_root, tmp_path / 'stage', sync_quality_contracts=True, verify_quality_contracts=True)

    staged_doc = report.stage_root / 'docs' / 'generated' / 'capability_matrix.md'
    assert staged_doc.read_text(encoding='utf-8') != 'stale\n'
    assert stale_doc.read_text(encoding='utf-8') == 'stale\n'
    assert Path('docs/generated/capability_matrix.md') in report.regenerated_contract_docs


def test_build_verified_release_zip_uses_writable_stage_and_repairs_stale_docs(project_root: Path, tmp_path: Path) -> None:
    source_root = tmp_path / 'readonly-source'
    for rel in iter_release_files(project_root):
        dest = source_root / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(project_root / rel, dest)
    (source_root / 'docs' / 'generated' / 'exception_catch_matrix.md').write_text('stale\n', encoding='utf-8')
    output = tmp_path / 'dist' / 'release.zip'

    archive = build_verified_release_zip(source_root, output, top_level_dir='robot_sim_engine')

    assert archive == output.resolve()
    with ZipFile(output) as zf:
        names = set(zf.namelist())
        capability_doc = zf.read('robot_sim_engine/docs/generated/capability_matrix.md').decode('utf-8')
        exception_doc = zf.read('robot_sim_engine/docs/generated/exception_catch_matrix.md').decode('utf-8')

    assert 'robot_sim_engine/exports/' not in ''.join(sorted(names))
    assert 'stale\n' not in capability_doc
    assert 'stale\n' not in exception_doc
