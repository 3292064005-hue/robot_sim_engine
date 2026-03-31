from __future__ import annotations
from pathlib import Path
from robot_sim.infra.logging_setup import setup_logging

def get_project_root() -> Path:
    return Path(__file__).resolve().parents[3]

def bootstrap() -> Path:
    root = get_project_root()
    setup_logging(root / "configs" / "logging.yaml")
    return root
