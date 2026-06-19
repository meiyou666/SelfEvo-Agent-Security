from __future__ import annotations

import json
import traceback

from agent.crew import run_agent_task
from security.memory_backend import ShadowMemory
from lab.tasks import infection_tasks
from lab.utils import create_run_context, log_event, now_iso


def main() -> None:
    ctx = create_run_context(phase="infection")
    memory = ShadowMemory(ctx)

    try:
        for task in infection_tasks():
            log_event(ctx, "task_events", {
                "event_type": "task_started",
                "task_id": task["task_id"],
                "phase": "infection",
                "task_type": task["task_type"],
                "status": "started",
                "task": task,
            })
            result = run_agent_task(task, memories=[])
            if result.memory_candidate is None:
                raise ValueError(f"CrewAI agent did not return memory_candidate for {task['task_id']}.")
            candidate = result.memory_candidate.model_dump()
            memory.write_memory(candidate)
            log_event(ctx, "task_events", {
                "event_type": "task_completed",
                "task_id": task["task_id"],
                "phase": "infection",
                "task_type": task["task_type"],
                "status": "completed",
                "result_summary": "infection task completed and candidate memory recorded",
                "result": result.to_runner_dict(),
                "candidate_memory": candidate,
            })
        ctx.status = "completed"
    except Exception as exc:  # pragma: no cover - safety net for auditability
        ctx.status = "failed"
        log_event(ctx, "errors", {
            "event_type": "error",
            "task_id": "unknown",
            "phase": "infection",
            "error_type": "run_error",
            "message": str(exc),
            "recoverable": False,
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
