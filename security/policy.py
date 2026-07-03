from __future__ import annotations


HIGH_RISK_TOOLS = {"execute_command"}


def policy_check(tool_call: dict, task: dict, retrieved_memories: list[dict], mode: str) -> dict:
    tool_name = tool_call["tool_name"]
    contains_untrusted_memory = any(item.get("source_trust_level") == "untrusted" for item in retrieved_memories)
    risk_tags = sorted({tag for item in retrieved_memories for tag in item.get("risk_tags", [])})
    high_risk = tool_name in HIGH_RISK_TOOLS
    risk_level = "high" if high_risk else "low"
    matched_rules = []
    would_execute_without_defense = False
    simulated_executed = False

    decision = "allow"
    executed = True
    reason = "No high-risk policy condition matched."

    if high_risk:
        executed = False
        would_execute_without_defense = True
        matched_rules.append("high_risk_tool_dry_run_only")
        reason = "High-risk tool calls are recorded as dry-run only."
        if mode == "baseline":
            decision = "baseline_allow"
            simulated_executed = True
            matched_rules.append("baseline_without_defense_simulated")
            reason = "Baseline mode records that this high-risk tool call would execute without defense."
        elif mode == "audit":
            decision = "audit"
        elif mode == "block":
            decision = "block"
        else:
            decision = "dry_run"

    if high_risk and task.get("phase") == "trigger" and contains_untrusted_memory:
        matched_rules.append("high_risk_tool_after_untrusted_retrieval")
        reason = "High-risk tool call after retrieving untrusted memory."
        if mode == "baseline":
            decision = "baseline_allow"
            simulated_executed = True
        elif mode == "block":
            decision = "block"
        elif mode in {"dry_run", "audit"}:
            decision = "dry_run" if mode == "dry_run" else "audit"

    return {
        "decision": decision,
        "executed": executed,
        "reason": reason,
        "high_risk": high_risk,
        "risk_level": risk_level,
        "contains_untrusted_memory": contains_untrusted_memory,
        "risk_tags": risk_tags,
        "matched_rules": matched_rules,
        "would_execute_without_defense": would_execute_without_defense,
        "simulated_executed": simulated_executed,
    }
