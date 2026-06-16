from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parent
LOG_ROOT = ROOT / "logs" / "runs"
DATA_ROOT = ROOT / "data"


@dataclass(frozen=True)
class ExperimentConfig:
    mode: str = "offline"
    policy_mode: str = "dry_run"
    memory_path_name: str = "shadow_memory.json"
    run_id_prefix: str = "run"


CONFIG = ExperimentConfig()

