from __future__ import annotations

import json
import traceback

from agent.crew import run_agent_task
from security.memory_backend import ShadowMemory
from security.tool_runtime import ToolRuntime
from lab.tasks import trigger_tasks
from lab.utils import create_run_context, find_latest_memory_file, log_event, now_iso


def main() -> None:
    memory_file = find_latest_memory_file()
    ctx = create_run_context(phase="trigger", inherited_memory_file=memory_file)
    memory = ShadowMemory(ctx, initial_memory_file=memory_file)
    tools = ToolRuntime(ctx)

    try:
        for task in trigger_tasks():
            log_event(ctx, "task_events", {
                "event_type": "task_started",
                "task_id": task["task_id"],
                "phase": "trigger",
                "task": task,
            })
            retrieved = memory.retrieve_memory(task["user_instruction"], top_k=3, task_id=task["task_id"])
            result = run_agent_task(task, memories=retrieved)
            tool_results = []
            for call in result.tool_calls:
                tool_results.append(tools.call_tool(call.model_dump(), task=task, retrieved_memories=retrieved))
            log_event(ctx, "task_events", {
                "event_type": "task_completed",
                "task_id": task["task_id"],
                "phase": "trigger",
                "result": result.to_runner_dict(),
                "tool_results": tool_results,
            })
        ctx.status = "completed"
    except Exception as exc:  # pragma: no cover - safety net for auditability
        ctx.status = "failed"
        log_event(ctx, "errors", {
            "event_type": "run_error",
            "task_id": "unknown",
            "phase": "trigger",
            "error": str(exc),
            "traceback": traceback.format_exc(),
        })
        raise
    finally:
        metadata_path = ctx.run_dir / "run_metadata.json"
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        metadata["status"] = ctx.status
        metadata["completed_at"] = now_iso()
        metadata_path.write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"trigger run: {ctx.run_id}")


if __name__ == "__main__":
    main()
