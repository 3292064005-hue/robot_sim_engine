from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ExportArtifactDefaults:
    trajectory_bundle_name: str = 'trajectory_bundle.npz'
    trajectory_metrics_name: str = 'trajectory_metrics.json'
    session_name: str = 'session.json'
    package_name: str = 'robot_sim_package.zip'
    benchmark_report_name: str = 'benchmark_report.json'
    benchmark_cases_name: str = 'benchmark_cases.csv'


DEFAULT_EXPORT_ARTIFACTS = ExportArtifactDefaults()
