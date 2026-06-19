from __future__ import annotations

from uuid import uuid4

from config import CONFIG
from security.policy import policy_check
from lab.utils import log_event


class ToolRuntime:
    def __init__(self, ctx):
        self.ctx = ctx

    def call_tool(self, tool_call: dict, task: dict, retrieved_memories: list[dict]) -> dict:
        decision = policy_check(tool_call, task, retrieved_memories, CONFIG.policy_mode)
        retrieved_memory_ids = [item["memory_id"] for item in retrieved_memories]
        retrieval_context_id = self._retrieval_context_id(retrieved_memories)
        tool_call_id = f"tool_{uuid4().hex[:12]}"
        policy_event_id = f"pol_{uuid4().hex[:12]}"
        derived_from_memory_ids = self._derived_from_memory_ids(tool_call, retrieved_memory_ids)
        event = {
            "event_type": "policy_decision",
            "task_id": task["task_id"],
            "phase": task["phase"],
            "policy_event_id": policy_event_id,
            "tool_call_id": tool_call_id,
            "tool_name": tool_call["tool_name"],
            "policy_mode": CONFIG.policy_mode,
            "risk_level": decision["risk_level"],
            "decision": decision["decision"],
            "executed": decision["executed"],
            "matched_rules": decision["matched_rules"],
            "reason": decision["reason"],
            "retrieval_context_id": retrieval_context_id,
            "retrieved_memory_ids": retrieved_memory_ids,
            "contains_untrusted_memory": decision["contains_untrusted_memory"],
            "risk_tags": decision["risk_tags"],
        }
        log_event(self.ctx, "policy_events", event)

        tool_event = {
            "event_type": "tool_call",
            "task_id": task["task_id"],
            "phase": task["phase"],
            "tool_call_id": tool_call_id,
            "tool_name": tool_call["tool_name"],
            "args_redacted": self._redact_args(tool_call.get("args", {})),
            "risk_level": decision["risk_level"],
            "retrieval_context_id": retrieval_context_id,
            "retrieved_memory_ids": retrieved_memory_ids,
            "derived_from_memory_ids": derived_from_memory_ids,
            "derivation_type": self._normalize_derivation_type(tool_call.get("derivation_type")),
            "policy_decision": decision["decision"],
            "executed": decision["executed"],
            "risk_tags": decision["risk_tags"],
            "result_summary": "dry-run only" if not decision["executed"] else "allowed by policy",
        }
        log_event(self.ctx, "tool_calls", tool_event)

        return {
            "ok": decision["decision"] in {"allow", "audit", "dry_run"},
            "executed": decision["executed"],
            "decision": decision["decision"],
            "message": "Tool call processed by external security runtime.",
        }

    def _redact_args(self, args: dict) -> dict:
        redacted = dict(args)
        if "command" in redacted:
            redacted["command"] = "REDACTED_DRY_RUN_COMMAND"
        return redacted

    def _retrieval_context_id(self, retrieved_memories: list[dict]) -> str | None:
        for memory in retrieved_memories:
            if memory.get("retrieval_context_id"):
                return memory["retrieval_context_id"]
        return None

    def _derived_from_memory_ids(self, tool_call: dict, retrieved_memory_ids: list[str]) -> list[str]:
        explicit_ids = tool_call.get("derived_from_memory_ids") or []
        if explicit_ids:
            return [memory_id for memory_id in explicit_ids if memory_id in retrieved_memory_ids]
        return retrieved_memory_ids

    def _normalize_derivation_type(self, value: str | None) -> str:
        aliases = {
            "direct": "directly_derived",
            "potential": "potentially_derived",
            "none": "unknown_derivation",
            "unknown": "unknown_derivation",
        }
        if value in {"directly_derived", "potentially_derived", "unknown_derivation"}:
            return value
        return aliases.get(value, "unknown_derivation")
