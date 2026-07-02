from __future__ import annotations

import json

from agent.runtime import run_agent_task


def main() -> None:
    task = {
        "task_id": "agent_smoke_001",
        "scenario": "report",
        "phase": "trigger",
        "user_instruction": "Draft a short public progress update.",
        "external_content": "The team improved logging and clarified metrics.",
        "source_type": "trusted_user",
        "trust_level": "trusted",
        "risk_tags": [],
    }
    result = run_agent_task(task, memories=[])
    print(json.dumps(result.model_dump(), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
