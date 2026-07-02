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
    if name == "run_agent_task":
        from agent.runtime import run_agent_task

        return run_agent_task
    if name == "SecurityExperimentCrew":
        from agent.crew import SecurityExperimentCrew

        return SecurityExperimentCrew
    if name in {"AgentTaskResult", "MemoryCandidate", "ToolCallIntent"}:
        from agent.schemas import AgentTaskResult, MemoryCandidate, ToolCallIntent

        return {
            "AgentTaskResult": AgentTaskResult,
            "MemoryCandidate": MemoryCandidate,
            "ToolCallIntent": ToolCallIntent,
        }[name]
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
