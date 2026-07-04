from __future__ import annotations

from typing import Any

from config import CONFIG
from agent.schemas import AgentTaskResult


def run_agent_task(task: dict[str, Any], memories: list[dict[str, Any]]) -> AgentTaskResult:
    if CONFIG.agent_backend == "mock":
        from agent.mock import run_mock_agent_task

        return run_mock_agent_task(task, memories)
    if CONFIG.agent_backend == "crewai":
        from agent.crew import run_agent_task as run_crewai_agent_task

        return run_crewai_agent_task(task, memories)
    raise RuntimeError(f"Unsupported AGENT_BACKEND: {CONFIG.agent_backend}")
