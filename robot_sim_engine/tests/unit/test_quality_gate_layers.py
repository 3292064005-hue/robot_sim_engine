from __future__ import annotations

from robot_sim.domain.quality_gate_catalog import quality_gate_ids_for_layer
from robot_sim.infra.quality_gate_catalog import quality_gate_definition


def test_quality_gate_catalog_exposes_release_blockers_layer() -> None:
    layer_gate_ids = quality_gate_ids_for_layer('release_blockers')
    assert 'quick_quality' in layer_gate_ids
    assert 'unit_and_regression' in layer_gate_ids
    assert quality_gate_definition('quick_quality').layer == 'release_blockers'


def test_quality_gate_catalog_exposes_runtime_and_governance_layers() -> None:
    assert 'runtime_contracts' in quality_gate_ids_for_layer('runtime_contracts')
    assert 'governance_evidence' in quality_gate_ids_for_layer('governance_evidence')
