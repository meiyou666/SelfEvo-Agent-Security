from __future__ import annotations

from config import CONFIG
from security.policy import policy_check
from lab.utils import log_event


class ToolRuntime:
    def __init__(self, ctx):
        self.ctx = ctx

    def call_tool(self, tool_call: dict, task: dict, retrieved_memories: list[dict]) -> dict:
        decision = policy_check(tool_call, task, retrieved_memories, CONFIG.policy_mode)
        retrieved_memory_ids = [item["memory_id"] for item in retrieved_memories]
        event = {
            "event_type": "policy_decision",
            "task_id": task["task_id"],
            "phase": task["phase"],
            "tool_name": tool_call["tool_name"],
            "policy_mode": CONFIG.policy_mode,
            "decision": decision["decision"],
            "executed": decision["executed"],
            "reason": decision["reason"],
            "retrieved_memory_ids": retrieved_memory_ids,
            "contains_untrusted_memory": decision["contains_untrusted_memory"],
            "risk_tags": decision["risk_tags"],
        }
        log_event(self.ctx, "policy_events", event)

        tool_event = {
            "event_type": "tool_call",
            "task_id": task["task_id"],
            "phase": task["phase"],
            "tool_name": tool_call["tool_name"],
            "args_redacted": self._redact_args(tool_call.get("args", {})),
            "retrieved_memory_ids": retrieved_memory_ids,
            "derived_from_memory_ids": retrieved_memory_ids,
            "policy_decision": decision["decision"],
            "executed": decision["executed"],
            "risk_tags": decision["risk_tags"],
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
