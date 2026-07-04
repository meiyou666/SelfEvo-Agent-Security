from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from config import CONFIG, DATA_ROOT, FIXTURE_ROOTS, ROOT
from security.policy import policy_check
from lab.utils import log_event


class ToolError(ValueError):
    """Raised when a tool request violates the offline experiment contract."""


class ToolRuntime:
    def __init__(self, ctx):
        self.ctx = ctx

    def call_tool(self, tool_call: dict, task: dict, retrieved_memories: list[dict]) -> dict:
        tool_name = tool_call.get("tool_name", "")
        args = tool_call.get("args", {})
        decision = policy_check(tool_call, task, retrieved_memories, CONFIG.policy_mode)
        retrieved_memory_ids = [item["memory_id"] for item in retrieved_memories]
        retrieval_context_id = self._retrieval_context_id(retrieved_memories)
        tool_call_id = f"tool_{uuid4().hex[:12]}"
        policy_event_id = f"pol_{uuid4().hex[:12]}"
        derived_from_memory_ids = self._derived_from_memory_ids(tool_call, retrieved_memory_ids)

        try:
            result = self._dispatch(tool_name, args, decision["executed"])
        except ToolError as exc:
            result = {"ok": False, "executed": False, "message": str(exc)}

        policy_event = {
            "event_type": "policy_decision",
            "task_id": task["task_id"],
            "phase": task["phase"],
            "policy_event_id": policy_event_id,
            "tool_call_id": tool_call_id,
            "tool_name": tool_name,
            "policy_mode": CONFIG.policy_mode,
            "risk_level": decision["risk_level"],
            "decision": decision["decision"],
            "executed": result["executed"],
            "matched_rules": decision["matched_rules"],
            "reason": decision["reason"],
            "retrieval_context_id": retrieval_context_id,
            "retrieved_memory_ids": retrieved_memory_ids,
            "contains_untrusted_memory": decision["contains_untrusted_memory"],
            "risk_tags": decision["risk_tags"],
            "would_execute_without_defense": decision["would_execute_without_defense"],
            "simulated_executed": decision["simulated_executed"],
        }
        log_event(self.ctx, "policy_events", policy_event)

        tool_event = {
            "event_type": "tool_call",
            "task_id": task["task_id"],
            "phase": task["phase"],
            "tool_call_id": tool_call_id,
            "tool_name": tool_name,
            "args_redacted": self._redact_args(args),
            "risk_level": decision["risk_level"],
            "retrieval_context_id": retrieval_context_id,
            "retrieved_memory_ids": retrieved_memory_ids,
            "derived_from_memory_ids": derived_from_memory_ids,
            "derivation_type": self._normalize_derivation_type(tool_call.get("derivation_type")),
            "policy_decision": decision["decision"],
            "matched_rules": decision["matched_rules"],
            "executed": result["executed"],
            "would_execute_without_defense": decision["would_execute_without_defense"],
            "simulated_executed": decision["simulated_executed"],
            "risk_tags": decision["risk_tags"],
            "result_summary": result["message"],
        }
        log_event(self.ctx, "tool_calls", tool_event)
        if decision["simulated_executed"]:
            self._record_demo_effect(tool_call_id, tool_name, args, task, derived_from_memory_ids)
        return {**result, "decision": decision["decision"], "tool_call_id": tool_call_id}

    def _dispatch(self, tool_name: str, args: dict, policy_allows_execution: bool) -> dict:
        if tool_name == "read_url":
            if not policy_allows_execution:
                return {"ok": False, "executed": False, "message": "Fixture read blocked by policy."}
            content, fixture = self._read_fixture(args.get("url", ""))
            return {
                "ok": True,
                "executed": True,
                "message": f"Read local fixture {fixture.relative_to(ROOT).as_posix()}.",
                "content": content,
            }
        if tool_name == "execute_command":
            return {"ok": True, "executed": False, "message": "dry-run only; command was not executed"}
        if tool_name == "write_report":
            return {"ok": True, "executed": True, "message": "Synthetic report action completed."}
        raise ToolError(f"Unknown tool: {tool_name or '<empty>'}")

    def _read_fixture(self, url: str) -> tuple[str, Path]:
        if not isinstance(url, str) or not url.strip():
            raise ToolError("read_url requires a non-empty local fixture path.")
        if url.startswith("fixture://"):
            raw = url.removeprefix("fixture://")
            candidate = (DATA_ROOT / raw).resolve()
        else:
            raw = url
            candidate = (ROOT / raw).resolve()
        allowed = any(candidate.is_relative_to(root.resolve()) for root in FIXTURE_ROOTS)
        if not allowed or candidate.suffix.lower() != ".txt":
            raise ToolError("read_url only permits .txt files under data/poison_pages or data/fixtures.")
        if not candidate.is_file():
            raise ToolError(f"Fixture not found: {raw}")
        try:
            content = candidate.read_text(encoding="utf-8")
        except (OSError, UnicodeError) as exc:
            raise ToolError(f"Unable to read fixture as UTF-8 text: {raw}") from exc
        if len(content) > CONFIG.max_fixture_chars:
            raise ToolError("Fixture exceeds the configured size limit.")
        return content, candidate

    @staticmethod
    def _redact_args(args: dict) -> dict:
        redacted = dict(args)
        if "command" in redacted:
            redacted["command"] = "REDACTED_DRY_RUN_COMMAND"
        return redacted

    @staticmethod
    def _retrieval_context_id(retrieved_memories: list[dict]) -> str | None:
        for memory in retrieved_memories:
            if memory.get("retrieval_context_id"):
                return memory["retrieval_context_id"]
        return None

    @staticmethod
    def _derived_from_memory_ids(tool_call: dict, retrieved_memory_ids: list[str]) -> list[str]:
        explicit_ids = tool_call.get("derived_from_memory_ids") or []
        if explicit_ids:
            return [memory_id for memory_id in explicit_ids if memory_id in retrieved_memory_ids]
        return retrieved_memory_ids

    @staticmethod
    def _normalize_derivation_type(value: str | None) -> str:
        aliases = {
            "direct": "directly_derived",
            "potential": "potentially_derived",
            "none": "unknown_derivation",
            "unknown": "unknown_derivation",
        }
        if value in {"directly_derived", "potentially_derived", "unknown_derivation"}:
            return value
        return aliases.get(value, "unknown_derivation")

    def _record_demo_effect(
        self,
        tool_call_id: str,
        tool_name: str,
        args: dict,
        task: dict,
        derived_from_memory_ids: list[str],
    ) -> None:
        effect = self._demo_effect_for_marker(str(args.get("command", "")))
        log_event(self.ctx, "demo_effects", {
            "event_type": "demo_effect",
            "task_id": task["task_id"],
            "phase": task["phase"],
            "tool_call_id": tool_call_id,
            "tool_name": tool_name,
            "simulated_target": "isolated_demo_state",
            "effect_type": effect["effect_type"],
            "visible_effect": effect["visible_effect"],
            "safety_boundary": "No real process, filesystem mutation, secret access, or network request occurred.",
            "derived_from_memory_ids": derived_from_memory_ids,
        })

    @staticmethod
    def _demo_effect_for_marker(command: str) -> dict:
        effects = {
            "SIMULATED_COMMAND_EXECUTION_MARKER": {
                "effect_type": "command_execution",
                "visible_effect": "Demo 状态变化：模拟命令执行已进入危险执行路径。",
            },
            "SIMULATED_SENSITIVE_READ_MARKER": {
                "effect_type": "sensitive_read",
                "visible_effect": "Demo 状态变化：模拟敏感信息读取已进入危险执行路径。",
            },
            "SIMULATED_EXFILTRATION_MARKER": {
                "effect_type": "exfiltration",
                "visible_effect": "Demo 状态变化：模拟数据外传已进入危险执行路径。",
            },
            "SIMULATED_PERSISTENCE_MARKER": {
                "effect_type": "persistence",
                "visible_effect": "Demo 状态变化：模拟持久化修改已进入危险执行路径。",
            },
        }
        return effects.get(command, {
            "effect_type": "unknown_high_risk_intent",
            "visible_effect": "Demo 状态变化：模拟高风险工具动作已进入危险执行路径。",
        })
