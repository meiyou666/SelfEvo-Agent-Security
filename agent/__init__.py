from __future__ import annotations

__all__ = [
    "AgentTaskResult",
    "MemoryCandidate",
    "SecurityExperimentCrew",
    "ToolCallIntent",
    "run_agent_task",
]


def __getattr__(name: str):
    """Load optional CrewAI dependencies only when agent APIs are requested."""
    if name in {"SecurityExperimentCrew", "run_agent_task"}:
        from agent.crew import SecurityExperimentCrew, run_agent_task

        return {"SecurityExperimentCrew": SecurityExperimentCrew, "run_agent_task": run_agent_task}[name]
    if name in {"AgentTaskResult", "MemoryCandidate", "ToolCallIntent"}:
        from agent.schemas import AgentTaskResult, MemoryCandidate, ToolCallIntent

        return {
            "AgentTaskResult": AgentTaskResult,
            "MemoryCandidate": MemoryCandidate,
            "ToolCallIntent": ToolCallIntent,
        }[name]
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
