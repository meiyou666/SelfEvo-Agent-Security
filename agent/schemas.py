from __future__ import annotations

import json
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator


DerivationType = Literal["directly_derived", "potentially_derived", "unknown_derivation"]


class ToolCallIntent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tool_name: str
    args: dict[str, Any] = Field(default_factory=dict)
    reason: str = ""
    derived_from_memory_ids: list[str] = Field(default_factory=list)
    derivation_type: DerivationType = "unknown_derivation"

    @field_validator("derivation_type", mode="before")
    @classmethod
    def normalize_derivation_type(cls, value: Any) -> str:
        aliases = {
            "direct": "directly_derived",
            "potential": "potentially_derived",
            "none": "unknown_derivation",
            "unknown": "unknown_derivation",
        }
        return aliases.get(value, value)


class MemoryCandidate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    content: str
    source_id: str
    source_type: str
    source_trust_level: str
    risk_tags: list[str] = Field(default_factory=list)
    created_from_phase: str


class AgentTaskResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    answer: str
    tool_calls: list[ToolCallIntent] = Field(default_factory=list)
    memory_candidate: MemoryCandidate | None = None
    raw_output: Any | None = None

    def to_runner_dict(self) -> dict[str, Any]:
        return {
            "answer": self.answer,
            "tool_calls": [tool_call.model_dump() for tool_call in self.tool_calls],
        }


def parse_agent_task_result(output: Any) -> AgentTaskResult:
    payload = _normalize_agent_task_payload(_coerce_output_payload(output))
    try:
        result = AgentTaskResult.model_validate(payload)
    except ValidationError as exc:
        raise ValueError(f"CrewAI output did not match AgentTaskResult schema: {exc}") from exc
    return result.model_copy(update={"raw_output": _safe_raw_output(output)})


def _coerce_output_payload(output: Any) -> Any:
    if isinstance(output, AgentTaskResult):
        return output.model_dump()
    if isinstance(output, dict):
        if isinstance(output.get("raw"), str):
            return _loads_json(output["raw"])
        return output
    for attr in ("pydantic", "json_dict", "raw"):
        value = getattr(output, attr, None)
        if value is None:
            continue
        if isinstance(value, BaseModel):
            return value.model_dump()
        if isinstance(value, dict):
            return value
        if isinstance(value, str):
            return _loads_json(value)
    if isinstance(output, BaseModel):
        payload = output.model_dump()
        if isinstance(payload.get("raw"), str):
            return _loads_json(payload["raw"])
        return payload
    if isinstance(output, str):
        return _loads_json(output)
    return _loads_json(str(output))


def _normalize_agent_task_payload(payload: Any) -> Any:
    if not isinstance(payload, dict):
        return payload
    normalized = {
        "answer": payload.get("answer", ""),
        "tool_calls": [_normalize_tool_call(item) for item in (payload.get("tool_calls") or [])],
        "memory_candidate": _normalize_memory_candidate(payload.get("memory_candidate")),
    }
    return normalized


def _normalize_tool_call(payload: Any) -> Any:
    if not isinstance(payload, dict):
        return payload
    return {
        "tool_name": payload.get("tool_name", ""),
        "args": payload.get("args", {}),
        "reason": payload.get("reason", ""),
        "derived_from_memory_ids": payload.get("derived_from_memory_ids", []),
        "derivation_type": payload.get("derivation_type", "unknown_derivation"),
    }


def _normalize_memory_candidate(payload: Any) -> Any:
    if payload is None or not isinstance(payload, dict):
        return payload
    return {
        "content": payload.get("content", ""),
        "source_id": payload.get("source_id", ""),
        "source_type": payload.get("source_type", ""),
        "source_trust_level": payload.get("source_trust_level", ""),
        "risk_tags": payload.get("risk_tags", []),
        "created_from_phase": payload.get("created_from_phase", ""),
    }


def _loads_json(value: str) -> Any:
    text = value.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError("CrewAI output was not valid JSON.") from exc


def _safe_raw_output(output: Any) -> Any:
    if isinstance(output, BaseModel):
        return output.model_dump()
    if isinstance(output, (dict, list, str, int, float, bool)) or output is None:
        return output
    return str(output)
