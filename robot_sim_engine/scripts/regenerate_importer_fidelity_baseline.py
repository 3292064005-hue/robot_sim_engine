from __future__ import annotations

import json
import sys
from pathlib import Path


def _configure_path() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    src_root = repo_root / 'src'
    if str(src_root) not in sys.path:
        sys.path.insert(0, str(src_root))


_configure_path()

from robot_sim.app.container import build_container  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[1]
BASELINE_PATH = REPO_ROOT / 'tests' / 'regression' / 'baselines' / 'importer_fidelity_baseline.json'


def _write_structured_urdf(path: Path) -> None:
    path.write_text(
        '<robot name="baseline">'
        '<link name="base"><visual><geometry><box size="1 1 1"/></geometry></visual></link>'
        '<link name="tip"><collision><geometry><sphere radius="0.1"/></geometry></collision></link>'
        '<joint name="j1" type="revolute">'
        '<parent link="base"/><child link="tip"/>'
        '<origin xyz="0 0 1" rpy="0 0 0"/><axis xyz="0 0 1"/><limit lower="-1" upper="1"/>'
        '</joint></robot>',
        encoding='utf-8',
    )


def build_baseline(root: Path = REPO_ROOT) -> dict[str, object]:
    container = build_container(root)
    with __import__('tempfile').TemporaryDirectory(prefix='fidelity-baseline-') as tmpdir:
        urdf_path = Path(tmpdir) / 'structured.urdf'
        _write_structured_urdf(urdf_path)
        yaml_spec = container.robot_registry.load('planar_2dof')
        urdf_spec = container.import_robot_uc.execute(urdf_path, importer_id='urdf')
    return {
        'yaml_planar_2dof': {
            'name': yaml_spec.name,
            'dof': yaml_spec.dof,
            'fidelity': yaml_spec.canonical_model.fidelity if yaml_spec.canonical_model else 'native',
            'execution_adapter': yaml_spec.canonical_model.execution_adapter if yaml_spec.canonical_model else '',
            'joint_count': yaml_spec.source_model_summary.get('joint_count', yaml_spec.dof),
            'link_count': yaml_spec.source_model_summary.get('link_count', yaml_spec.dof + 1),
        },
        'urdf_structured_serial': {
            'name': urdf_spec.name,
            'fidelity': urdf_spec.canonical_model.fidelity if urdf_spec.canonical_model else urdf_spec.metadata.get('import_fidelity', ''),
            'execution_adapter': urdf_spec.canonical_model.execution_adapter if urdf_spec.canonical_model else '',
            'joint_count': urdf_spec.source_model_summary['joint_count'],
            'link_count': urdf_spec.source_model_summary['link_count'],
            'has_visual': urdf_spec.source_model_summary['has_visual'],
            'has_collision': urdf_spec.source_model_summary['has_collision'],
            'warnings': list(urdf_spec.metadata.get('warnings', ())),
        },
    }


def main() -> int:
    payload = build_baseline(REPO_ROOT)
    BASELINE_PATH.parent.mkdir(parents=True, exist_ok=True)
    BASELINE_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True), encoding='utf-8')
    print(f'wrote {BASELINE_PATH.relative_to(REPO_ROOT)}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
