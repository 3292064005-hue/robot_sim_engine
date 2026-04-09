from __future__ import annotations

from robot_sim.infra.release_environment_gate import ReleaseEnvironmentGate


def test_release_environment_contract_loads(project_root) -> None:
    gate = ReleaseEnvironmentGate(project_root / 'configs' / 'release_environment.yaml')
    contract = gate.load_contract('release')
    assert contract.os_id == 'ubuntu'
    assert contract.python_major == 3
    assert contract.python_minor == 10


def test_release_environment_gate_reports_exact_python_requirement(monkeypatch, project_root) -> None:
    gate = ReleaseEnvironmentGate(project_root / 'configs' / 'release_environment.yaml')

    class DummyBaseline:
        platform_system = 'Linux'
        python_version = '3.13.5'
        os_id = 'ubuntu'
        os_version_id = '22.04'
        pyside_version = '6.5.0'
        build_available = True
        errors = ()
        warnings = ()

    monkeypatch.setattr('robot_sim.infra.release_environment_gate.evaluate_runtime_baseline', lambda mode: DummyBaseline())
    report = gate.evaluate('release')
    assert report.ok is False
    assert any('requires Python 3.10' in error for error in report.errors)
