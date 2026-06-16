from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from config import CONFIG, LOG_ROOT


@dataclass
class RunContext:
    run_id: str
    run_dir: Path
    phase: str
    status: str = "running"


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def create_run_context(phase: str, inherited_memory_file: Path | None = None) -> RunContext:
    run_id = f"{CONFIG.run_id_prefix}_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid4().hex[:6]}"
    run_dir = LOG_ROOT / run_id
    run_dir.mkdir(parents=True, exist_ok=False)
    metadata = {
        "run_id": run_id,
        "phase": phase,
        "mode": CONFIG.mode,
        "policy_mode": CONFIG.policy_mode,
        "status": "running",
        "created_at": now_iso(),
        "inherited_memory_file": str(inherited_memory_file) if inherited_memory_file else None,
    }
    (run_dir / "run_metadata.json").write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
    for name in ["memory_events", "tool_calls", "policy_events", "task_events", "errors"]:
        (run_dir / f"{name}.jsonl").write_text("", encoding="utf-8")
    return RunContext(run_id=run_id, run_dir=run_dir, phase=phase)


def log_event(ctx: RunContext, stream: str, event: dict) -> None:
    event = {
        "event_id": f"evt_{uuid4().hex[:12]}",
        "run_id": ctx.run_id,
        "timestamp": now_iso(),
        **event,
    }
    path = ctx.run_dir / f"{stream}.jsonl"
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(event, ensure_ascii=False) + "\n")


def read_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def find_latest_memory_file() -> Path | None:
    if not LOG_ROOT.exists():
        return None
    candidates = sorted(LOG_ROOT.glob(f"*/{CONFIG.memory_path_name}"), key=lambda path: path.stat().st_mtime, reverse=True)
    return candidates[0] if candidates else None

