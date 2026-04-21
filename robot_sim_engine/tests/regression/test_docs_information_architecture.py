from __future__ import annotations

from pathlib import Path

from robot_sim.infra.docs_information_architecture import verify_docs_information_architecture


def test_docs_information_architecture_is_current(project_root: Path):
    assert verify_docs_information_architecture(project_root) == []
