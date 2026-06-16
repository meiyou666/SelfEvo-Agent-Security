from __future__ import annotations

import json
import traceback

from agent.crew import RuleBasedAgent
from agent.memory_backend import ShadowMemory
from lab.tasks import infection_tasks
from lab.utils import create_run_context, log_event, now_iso


def main() -> None:
    ctx = create_run_context(phase="infection")
    agent = RuleBasedAgent()
    memory = ShadowMemory(ctx)

    try:
        for task in infection_tasks():
            log_event(ctx, "task_events", {
                "event_type": "task_started",
                "task_id": task["task_id"],
                "phase": "infection",
                "task": task,
            })
            result = agent.run_task(task, memories=[])
            candidate = agent.reflect(task, result)
            memory.write_memory(candidate)
            log_event(ctx, "task_events", {
                "event_type": "task_completed",
                "task_id": task["task_id"],
                "phase": "infection",
                "result": result,
                "candidate_memory": candidate,
            })
        ctx.status = "completed"
    except Exception as exc:  # pragma: no cover - safety net for auditability
        ctx.status = "failed"
        log_event(ctx, "errors", {
            "event_type": "run_error",
            "task_id": "unknown",
            "phase": "infection",
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
        print(f"infection run: {ctx.run_id}")


if __name__ == "__main__":
    main()

