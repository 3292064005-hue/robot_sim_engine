from __future__ import annotations
from pathlib import Path
import yaml

class ConfigService:
    def __init__(self, config_dir: str | Path) -> None:
        self.config_dir = Path(config_dir)

    def load_yaml(self, name: str) -> dict:
        path = self.config_dir / name
        with path.open("r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
