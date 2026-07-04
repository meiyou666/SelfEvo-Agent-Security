from __future__ import annotations

import argparse
import json
import os
import traceback
from pathlib import Path


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run controlled attack scenario comparison cases.")
    parser.add_argument(
        "--policy",
        choices=["baseline", "dry_run", "block", "audit"],
        default=os.getenv("POLICY_MODE", "dry_run"),
        help="Policy mode for this run. baseline records would-execute success without real execution.",
    )
    parser.add_argument(
        "--agent-backend",
        choices=["mock", "crewai"],
        default=os.getenv("AGENT_BACKEND", "mock"),
        help="Agent backend to use. mock is deterministic and does not require an API key.",
    )
    return parser.parse_args()


ARGS = _parse_args()
os.environ["POLICY_MODE"] = ARGS.policy
os.environ["AGENT_BACKEND"] = ARGS.agent_backend

from agent.runtime import run_agent_task
from lab.tasks import attack_scenario_tasks
from lab.utils import create_run_context, log_event, now_iso, read_jsonl
from security.memory_backend import ShadowMemory
from security.tool_runtime import ToolRuntime


def main() -> None:
    ctx = create_run_context(phase=f"attack_{ARGS.policy}")
    memory = ShadowMemory(ctx)
    tools = ToolRuntime(ctx)

    try:
        for task in attack_scenario_tasks():
            log_event(ctx, "task_events", {
                "event_type": "task_started",
                "task_id": task["task_id"],
                "phase": task["phase"],
                "task_type": task["task_type"],
                "status": "started",
                "task": task,
            })

            read_result = tools.call_tool(
                {"tool_name": "read_url", "args": {"url": task["input_url"]}},
                task=task,
                retrieved_memories=[],
            )
            if not read_result["ok"]:
                raise ValueError(read_result["message"])

            memory_record = memory.write_memory({
                "content": read_result["content"],
                "source_id": task["input_source_ids"][0],
                "source_type": task["source_type"],
                "source_trust_level": task["trust_level"],
                "risk_tags": task["risk_tags"],
                "created_from_phase": "attack_fixture",
            })
            retrieved = [{**memory_record, "retrieval_context_id": f"ret_{task['task_id']}"}]
            log_event(ctx, "memory_events", {
                "event_type": "memory_retrieve",
                "task_id": task["task_id"],
                "phase": task["phase"],
                "retrieval_context_id": retrieved[0]["retrieval_context_id"],
                "query": task["user_instruction"],
                "query_summary": task["user_instruction"][:160],
                "retrieved_memory_ids": [memory_record["memory_id"]],
                "contains_untrusted_memory": True,
                "source_trust_levels": ["untrusted"],
                "risk_tags": task["risk_tags"],
            })

            result = run_agent_task(task, memories=retrieved)
            tool_results = [
                tools.call_tool(call.model_dump(), task=task, retrieved_memories=retrieved)
                for call in result.tool_calls
            ]
            log_event(ctx, "task_events", {
                "event_type": "task_completed",
                "task_id": task["task_id"],
                "phase": task["phase"],
                "task_type": task["task_type"],
                "status": "completed",
                "result_summary": "attack scenario completed with controlled tool-intent evaluation",
                "result": result.to_runner_dict(),
                "tool_results": tool_results,
            })
        ctx.status = "completed"
    except Exception as exc:  # pragma: no cover - audit trail for experiment failures
        ctx.status = "failed"
        log_event(ctx, "errors", {
            "event_type": "error",
            "task_id": "unknown",
            "phase": ctx.phase,
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
        if ctx.status == "completed":
            report_path = write_attack_case_report(ctx.run_dir)
            print(f"attack run: {ctx.run_id}")
            print(f"attack case report: {report_path}")


def write_attack_case_report(run_dir: Path) -> Path:
    metadata = json.loads((run_dir / "run_metadata.json").read_text(encoding="utf-8"))
    tool_calls = [
        event
        for event in read_jsonl(run_dir / "tool_calls.jsonl")
        if event.get("tool_name") == "execute_command"
    ]
    demo_effects = {
        event["tool_call_id"]: event
        for event in read_jsonl(run_dir / "demo_effects.jsonl")
        if event.get("event_type") == "demo_effect"
    }
    task_events = [
        event
        for event in read_jsonl(run_dir / "task_events.jsonl")
        if event.get("event_type") == "task_started"
    ]
    titles = {event["task_id"]: event["task"]["title"] for event in task_events}

    lines = [
        "# 攻击场景对照结果",
        "",
        "本报告只使用安全模拟标记，不执行真实命令，不修改真实文件系统，不读取真实密钥，也不发起网络请求。",
        "",
        f"- `run_id`: {metadata['run_id']}",
        f"- `agent_backend`: {metadata['agent_backend']}",
        f"- `policy_mode`: {metadata['policy_mode']}",
        "",
        "| 案例 | 策略 | 无防护是否会执行 | Demo 可见攻击效果 | 真实执行 | 命中规则 |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for event in tool_calls:
        demo_effect = demo_effects.get(event["tool_call_id"])
        lines.append(
            "| "
            + " | ".join([
                titles.get(event["task_id"], event["task_id"]),
                str(event.get("policy_decision")),
                str(event.get("would_execute_without_defense", False)),
                demo_effect["visible_effect"] if demo_effect else "防护生效，无 demo 攻击效果",
                "是" if event.get("executed") else "否",
                ", ".join(event.get("matched_rules", [])),
            ])
            + " |"
        )

    total = len(tool_calls)
    baseline_success = len([event for event in tool_calls if event.get("simulated_executed")])
    visible_effect_count = len(demo_effects)
    blocked = len([
        event
        for event in tool_calls
        if event.get("would_execute_without_defense") and not event.get("simulated_executed") and not event.get("executed")
    ])
    lines.extend([
        "",
        "## 汇总",
        "",
        f"- `high_risk_case_count`: {total}",
        f"- `baseline_simulated_success_count`: {baseline_success}",
        f"- `visible_demo_effect_count`: {visible_effect_count}",
        f"- `defense_blocked_count`: {blocked}",
        f"- `real_executed_count`: {len([event for event in tool_calls if event.get('executed')])}",
    ])

    report_path = run_dir / "attack_case_results.md"
    report_path.write_text("\n".join(lines), encoding="utf-8")
    return report_path


if __name__ == "__main__":
    main()
