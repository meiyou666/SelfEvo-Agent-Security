from __future__ import annotations

import os
import sys
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
FIXTURE_ROOTS = (DATA_ROOT / "poison_pages", DATA_ROOT / "fixtures")
CREWAI_STORAGE_ROOT = ROOT / ".crewai_storage"
CREWAI_LOCALAPPDATA_ROOT = ROOT / ".crewai_localappdata"

os.environ.setdefault("CREWAI_STORAGE_DIR", str(CREWAI_STORAGE_ROOT))
os.environ["LOCALAPPDATA"] = os.getenv("CREWAI_LOCALAPPDATA", str(CREWAI_LOCALAPPDATA_ROOT))
os.environ.setdefault("CREWAI_TRACING_ENABLED", "false")
os.environ.setdefault("OTEL_SDK_DISABLED", "true")

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")


@dataclass(frozen=True)
class ExperimentConfig:
    schema_version: str = "0.1"
    mode: str = os.getenv("EXPERIMENT_MODE", "crewai")
    policy_mode: str = os.getenv("POLICY_MODE", "dry_run")
    memory_path_name: str = "shadow_memory.json"
    memory_backend: str = "shadow_memory_v0"
    run_id_prefix: str = "run"
    agent_backend: str = os.getenv("AGENT_BACKEND", "crewai")
    llm_model: str = os.getenv("MODEL", "openai/gpt-4o-mini")
    llm_temperature: float = float(os.getenv("LLM_TEMPERATURE", "0.0"))
    crewai_verbose: bool = os.getenv("CREWAI_VERBOSE", "true").lower() in {"1", "true", "yes", "on"}
    task_set_version: str = os.getenv("TASK_SET_VERSION", "tasks_v0.1")
    sample_set_version: str = os.getenv("SAMPLE_SET_VERSION", "poison_v0.1")
    random_seed: int = int(os.getenv("RANDOM_SEED", "42"))
    max_fixture_chars: int = int(os.getenv("MAX_FIXTURE_CHARS", "100000"))


CONFIG = ExperimentConfig()
