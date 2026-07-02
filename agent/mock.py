from __future__ import annotations

from typing import Any

from agent.schemas import AgentTaskResult, MemoryCandidate, ToolCallIntent


def run_mock_agent_task(task: dict[str, Any], memories: list[dict[str, Any]]) -> AgentTaskResult:
    """Deterministic offline agent used to validate the experiment pipeline."""
    if task.get("phase") == "infection":
        return _run_mock_infection(task)
    return _run_mock_trigger(task, memories)


def _run_mock_infection(task: dict[str, Any]) -> AgentTaskResult:
    content = task.get("external_content", "")
    summary = " ".join(content.split())[:500]
    memory = MemoryCandidate(
        content=summary or task.get("user_instruction", ""),
        source_id=task["input_source_ids"][0],
        source_type=task.get("source_type", "unknown"),
        source_trust_level=task.get("trust_level", "unknown"),
        risk_tags=task.get("risk_tags", []),
        created_from_phase="infection",
    )
    return AgentTaskResult(
        answer="Mock infection completed: summarized provided content into shadow memory.",
        memory_candidate=memory,
    )


def _run_mock_trigger(task: dict[str, Any], memories: list[dict[str, Any]]) -> AgentTaskResult:
    contains_untrusted_risk = any(
        memory.get("source_trust_level") == "untrusted" and memory.get("risk_tags")
        for memory in memories
    )
    tool_calls: list[ToolCallIntent] = []
    if task.get("task_type") == "trigger" and contains_untrusted_risk:
        risky_memory_ids = [
            memory["memory_id"]
            for memory in memories
            if memory.get("source_trust_level") == "untrusted" and memory.get("risk_tags")
        ]
        tool_calls.append(
            ToolCallIntent(
                tool_name="execute_command",
                args={"command": "mock_high_risk_intent"},
                reason="Mock backend simulates risky intent after retrieving untrusted memory.",
                derived_from_memory_ids=risky_memory_ids,
                derivation_type="potentially_derived",
            )
        )
    return AgentTaskResult(
        answer="Mock trigger completed: generated a benign response and optional tool intent.",
        tool_calls=tool_calls,
    )
