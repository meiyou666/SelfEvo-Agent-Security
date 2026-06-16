from __future__ import annotations


RISK_TERMS = ("mock_secret", "private token", "sensitive file", "read_private_file")


class RuleBasedAgent:
    """Deterministic stand-in for an LLM agent during the offline MVP."""

    def run_task(self, task: dict, memories: list[dict]) -> dict:
        tool_calls: list[dict] = []
        memory_text = "\n".join(item.get("content", "") for item in memories)

        if any(term in memory_text.lower() for term in RISK_TERMS):
            tool_calls.append({
                "tool_name": "execute_command",
                "args": {
                    "command": "DRY_RUN_READ_MOCK_SECRET",
                    "reason": "Retrieved memory requested adding a mock secret to a report.",
                },
            })

        if task.get("scenario") == "report":
            tool_calls.append({
                "tool_name": "write_report",
                "args": {"topic": "weekly public progress"},
            })

        return {
            "answer": f"Processed {task['task_id']} in {task['phase']} phase.",
            "tool_calls": tool_calls,
        }

    def reflect(self, task: dict, result: dict) -> dict:
        content = task.get("external_content", "")
        if task.get("phase") == "infection":
            content = (
                "Reusable troubleshooting notes: "
                + content
            )
        return {
            "content": content,
            "source_id": task["task_id"],
            "source_type": task["source_type"],
            "source_trust_level": task["trust_level"],
            "risk_tags": task.get("risk_tags", []),
            "created_from_phase": task["phase"],
        }

