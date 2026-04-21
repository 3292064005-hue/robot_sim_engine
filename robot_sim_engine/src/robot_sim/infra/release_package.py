from __future__ import annotations

import shutil
import tempfile
from dataclasses import dataclass
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

from robot_sim.infra.quality_contracts import verify_quality_contract_files, write_quality_contract_files

EXCLUDED_DIR_NAMES = {
    '__pycache__',
    '.pytest_cache',
    '.mypy_cache',
    '.ruff_cache',
    '.git',
    '.idea',
    '.vscode',
    '.nox',
    '.venv',
    'build',
    'exports',
    'artifacts',
    'dist',
}


EXCLUDED_FILE_NAMES = {
    '.coverage',
    'coverage.json',
    'scene_capture.png',
    'FINAL_AUDIT.md',
    'FINAL_COMPLIANCE_MATRIX.md',
    'FINAL_REVIEW_AUDIT.md',
    'ISSUE_BY_ISSUE_FIX_SUMMARY.md',
    'REVALIDATION_NOTE.md',
    'SECOND_ROUND_AUDIT.md',
}

EXCLUDED_SUFFIXES = {'.pyc', '.pyo'}


class ReleasePackageError(RuntimeError):
    """Raised when the clean release bundle cannot satisfy repository contracts."""


@dataclass(frozen=True)
class ReleaseStageReport:
    """Summary of the staging/preflight work performed for a clean release bundle.

    Attributes:
        stage_root: Writable staging tree used to build the final archive.
        regenerated_contract_docs: Repository-relative contract docs that were rewritten in
            the staging tree before verification.
    """

    stage_root: Path
    regenerated_contract_docs: tuple[Path, ...] = ()


def should_include_path(path: Path) -> bool:
    """Return True when a path should be shipped in a clean release archive.

    Args:
        path: Repository-relative file path under evaluation.

    Returns:
        bool: ``True`` only for files that are part of the clean distributable source tree.

    Raises:
        None: Pure path-classification helper.

    Boundary behavior:
        Release packaging intentionally excludes local caches, build outputs, audit notes,
        screenshot artifacts, and setuptools metadata directories such as ``*.egg-info``.
        The archive therefore represents the canonical project source, not a raw snapshot of
        the caller's working directory.
    """
    for part in path.parts:
        if part in EXCLUDED_DIR_NAMES:
            return False
        if part.endswith('.egg-info'):
            return False
    if path.name in EXCLUDED_FILE_NAMES:
        return False
    if path.suffix in EXCLUDED_SUFFIXES:
        return False
    return True


def iter_release_files(root: Path):
    """Yield relative file paths for a clean release archive."""
    root = root.resolve()
    for path in sorted(root.rglob('*')):
        if not path.is_file():
            continue
        rel = path.relative_to(root)
        if should_include_path(rel):
            yield rel


def _copy_release_tree(root: Path, stage_root: Path) -> None:
    """Copy the clean distributable source tree into a writable staging directory."""
    root = root.resolve()
    stage_root.mkdir(parents=True, exist_ok=True)
    for rel in iter_release_files(root):
        src = root / rel
        dest = stage_root / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dest)


def _classify_contract_doc_errors(errors: list[str], stage_root: Path) -> tuple[list[str], list[Path]]:
    """Return non-doc verification errors plus docs that can be regenerated in staging.

    Only checked-in contract documents under ``docs/`` are automatically regenerated.
    Other verification failures such as README/CI drift remain hard errors.
    """
    syncable_docs: list[Path] = []
    residual_errors: list[str] = []
    for item in errors:
        matched = False
        for prefix in ('contract doc out of date: ', 'missing contract doc: '):
            if item.startswith(prefix):
                rel = Path(item[len(prefix) :].strip())
                if rel.parts and rel.parts[0] == 'docs':
                    syncable_docs.append(stage_root / rel)
                    matched = True
                break
        if not matched:
            residual_errors.append(item)
    unique_docs = tuple(sorted({path.relative_to(stage_root) for path in syncable_docs}))
    return residual_errors, [stage_root / rel for rel in unique_docs]


def stage_release_tree(
    root: Path,
    stage_root: Path,
    *,
    sync_quality_contracts: bool = True,
    verify_quality_contracts: bool = True,
) -> ReleaseStageReport:
    """Stage a writable clean source tree and enforce release-contract integrity.

    Args:
        root: Read-only or writable repository root to stage from.
        stage_root: Writable destination directory used for preflight regeneration and the
            eventual zip build.
        sync_quality_contracts: When ``True``, regenerate checked-in contract docs inside the
            staging tree if verification detects stale ``docs/`` outputs.
        verify_quality_contracts: When ``True``, fail the stage if repository contracts still
            drift after any allowed regeneration.

    Returns:
        ReleaseStageReport: Staging root plus the contract-doc files rewritten during preflight.

    Raises:
        ReleasePackageError: If release-contract verification still fails after staging.

    Boundary behavior:
        Staging intentionally copies only the clean distributable source tree. Contract-doc
        regeneration happens only inside the writable staging tree so packaging never depends on
        mutating the caller's working copy.
    """
    root = root.resolve()
    stage_root = stage_root.resolve()
    _copy_release_tree(root, stage_root)
    regenerated_docs: tuple[Path, ...] = ()
    if verify_quality_contracts:
        errors = verify_quality_contract_files(stage_root)
        residual_errors, syncable_doc_paths = _classify_contract_doc_errors(errors, stage_root)
        if syncable_doc_paths and sync_quality_contracts:
            write_quality_contract_files(stage_root)
            regenerated_docs = tuple(path.relative_to(stage_root) for path in syncable_doc_paths)
            errors = verify_quality_contract_files(stage_root)
            residual_errors, _ = _classify_contract_doc_errors(errors, stage_root)
        else:
            errors = residual_errors + [
                f'contract doc sync disabled while docs drifted: {path.relative_to(stage_root)}'
                for path in syncable_doc_paths
            ]
        if errors:
            raise ReleasePackageError('release staging failed quality-contract verification:\n- ' + '\n- '.join(errors))
    return ReleaseStageReport(stage_root=stage_root, regenerated_contract_docs=regenerated_docs)


def build_verified_release_zip(root: Path, output_zip: Path, *, top_level_dir: str | None = None) -> Path:
    """Build a clean release archive from a staged, contract-verified source tree.

    The source repository can remain read-only; packaging stages the clean source tree into a
    temporary directory, regenerates any stale checked-in contract docs there, verifies the
    staged tree, and only then emits the final archive.
    """
    with tempfile.TemporaryDirectory(prefix='robot-release-stage-') as tmpdir:
        report = stage_release_tree(root, Path(tmpdir) / 'stage', sync_quality_contracts=True, verify_quality_contracts=True)
        return build_release_zip(report.stage_root, output_zip, top_level_dir=top_level_dir)


def build_release_zip(root: Path, output_zip: Path, *, top_level_dir: str | None = None) -> Path:
    """Create a clean zip archive that excludes caches, audits, and local build artifacts."""
    root = root.resolve()
    output_zip = output_zip.resolve()
    output_zip.parent.mkdir(parents=True, exist_ok=True)
    output_rel: Path | None
    try:
        output_rel = output_zip.relative_to(root)
    except ValueError:
        output_rel = None
    with ZipFile(output_zip, 'w', compression=ZIP_DEFLATED) as zf:
        for rel in iter_release_files(root):
            if output_rel is not None and rel == output_rel:
                continue
            src = root / rel
            arcname = rel.as_posix() if not top_level_dir else f"{top_level_dir}/{rel.as_posix()}"
            zf.write(src, arcname=arcname)
    return output_zip
