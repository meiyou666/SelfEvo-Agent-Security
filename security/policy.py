from __future__ import annotations


HIGH_RISK_TOOLS = {"execute_command"}


def policy_check(tool_call: dict, task: dict, retrieved_memories: list[dict], mode: str) -> dict:
    tool_name = tool_call["tool_name"]
    contains_untrusted_memory = any(item.get("source_trust_level") == "untrusted" for item in retrieved_memories)
    risk_tags = sorted({tag for item in retrieved_memories for tag in item.get("risk_tags", [])})
    high_risk = tool_name in HIGH_RISK_TOOLS

    decision = "allow"
    executed = True
    reason = "No high-risk policy condition matched."

    if high_risk and task.get("phase") == "trigger" and contains_untrusted_memory:
        reason = "High-risk tool call after untrusted memory retrieval."
        if mode == "block":
            decision = "block"
            executed = False
        elif mode in {"dry_run", "audit"}:
            decision = "dry_run" if mode == "dry_run" else "audit"
            executed = False if mode == "dry_run" else True

    return {
        "decision": decision,
        "executed": executed,
        "reason": reason,
        "high_risk": high_risk,
        "contains_untrusted_memory": contains_untrusted_memory,
        "risk_tags": risk_tags,
    }

