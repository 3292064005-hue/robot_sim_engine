from __future__ import annotations

from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

EXCLUDED_DIR_NAMES = {
    '__pycache__',
    '.pytest_cache',
    '.mypy_cache',
    '.ruff_cache',
    '.git',
    '.idea',
    '.vscode',
<<<<<<< HEAD
    '.nox',
    '.venv',
    'build',
=======
>>>>>>> 3ed78e647985c6d680c085e4480d898855278db3
    'exports',
    'dist',
}


EXCLUDED_FILE_NAMES = {
    '.coverage',
<<<<<<< HEAD
    'coverage.json',
    'scene_capture.png',
    'FINAL_AUDIT.md',
    'FINAL_COMPLIANCE_MATRIX.md',
    'FINAL_REVIEW_AUDIT.md',
    'ISSUE_BY_ISSUE_FIX_SUMMARY.md',
    'REVALIDATION_NOTE.md',
    'SECOND_ROUND_AUDIT.md',
=======
>>>>>>> 3ed78e647985c6d680c085e4480d898855278db3
}

EXCLUDED_SUFFIXES = {'.pyc', '.pyo'}


def should_include_path(path: Path) -> bool:
<<<<<<< HEAD
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
=======
    """Return True when a path should be shipped in a clean release archive."""
    for part in path.parts:
        if part in EXCLUDED_DIR_NAMES:
            return False
>>>>>>> 3ed78e647985c6d680c085e4480d898855278db3
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


def build_release_zip(root: Path, output_zip: Path, *, top_level_dir: str | None = None) -> Path:
<<<<<<< HEAD
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
=======
    """Create a clean zip archive that excludes caches and local build artifacts."""
    root = root.resolve()
    output_zip = output_zip.resolve()
    output_zip.parent.mkdir(parents=True, exist_ok=True)
    with ZipFile(output_zip, 'w', compression=ZIP_DEFLATED) as zf:
        for rel in iter_release_files(root):
>>>>>>> 3ed78e647985c6d680c085e4480d898855278db3
            src = root / rel
            arcname = rel.as_posix() if not top_level_dir else f"{top_level_dir}/{rel.as_posix()}"
            zf.write(src, arcname=arcname)
    return output_zip
