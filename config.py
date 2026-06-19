from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

try:
    from dotenv import load_dotenv
except ModuleNotFoundError:  # pragma: no cover - dependency installed with CrewAI requirements
    load_dotenv = None

if load_dotenv:
    load_dotenv()


ROOT = Path(__file__).resolve().parent
LOG_ROOT = ROOT / "logs" / "runs"
DATA_ROOT = ROOT / "data"


@dataclass(frozen=True)
class ExperimentConfig:
    mode: str = os.getenv("EXPERIMENT_MODE", "crewai")
    policy_mode: str = os.getenv("POLICY_MODE", "dry_run")
    memory_path_name: str = "shadow_memory.json"
    run_id_prefix: str = "run"
    agent_backend: str = os.getenv("AGENT_BACKEND", "crewai")
    llm_model: str = os.getenv("MODEL", "openai/gpt-4o-mini")
    llm_temperature: float = float(os.getenv("LLM_TEMPERATURE", "0.0"))
    crewai_verbose: bool = os.getenv("CREWAI_VERBOSE", "true").lower() in {"1", "true", "yes", "on"}


CONFIG = ExperimentConfig()
