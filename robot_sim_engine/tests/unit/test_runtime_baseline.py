from __future__ import annotations

from robot_sim.infra.runtime_baseline import evaluate_runtime_baseline, read_os_release


def test_read_os_release_parses_key_values(tmp_path) -> None:
    path = tmp_path / 'os-release'
    path.write_text('ID=ubuntu\nVERSION_ID="22.04"\nNAME="Ubuntu"\n', encoding='utf-8')
    payload = read_os_release(path)
    assert payload['ID'] == 'ubuntu'
    assert payload['VERSION_ID'] == '22.04'
    assert payload['NAME'] == 'Ubuntu'


def test_headless_baseline_allows_python_313_with_warning() -> None:
    report = evaluate_runtime_baseline(
        'headless',
        platform_system='Linux',
        version_info=(3, 13, 2),
        os_release={'ID': 'ubuntu', 'VERSION_ID': '22.04'},
        build_available=False,
    )
    assert report.ok is True
    assert report.errors == ()
    assert report.warnings


def test_gui_baseline_requires_ubuntu_2204_python310_and_pyside65() -> None:
    report = evaluate_runtime_baseline(
        'gui',
        platform_system='Linux',
        version_info=(3, 13, 0),
        os_release={'ID': 'ubuntu', 'VERSION_ID': '24.04'},
        pyside_version='6.4.0',
        build_available=True,
    )
    assert report.ok is False
    assert any('Ubuntu 22.04' in error for error in report.errors)
    assert any('Python 3.10' in error for error in report.errors)
    assert any('PySide6 >= 6.5' in error for error in report.errors)


def test_release_baseline_requires_build_module() -> None:
    report = evaluate_runtime_baseline(
        'release',
        platform_system='Linux',
        version_info=(3, 10, 14),
        os_release={'ID': 'ubuntu', 'VERSION_ID': '22.04'},
        build_available=False,
    )
    assert report.ok is False
    assert report.errors == ('release baseline requires the build module (python -m build)',)
