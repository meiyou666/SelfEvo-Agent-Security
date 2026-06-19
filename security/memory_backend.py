from __future__ import annotations

import json
from pathlib import Path
from uuid import uuid4

from config import CONFIG
from lab.utils import log_event, now_iso


class ShadowMemory:
    def __init__(self, ctx, initial_memory_file: Path | None = None):
        self.ctx = ctx
        self.memory_path = ctx.run_dir / CONFIG.memory_path_name
        if initial_memory_file and initial_memory_file.exists():
            self.records = json.loads(initial_memory_file.read_text(encoding="utf-8"))
        else:
            self.records = []
        self._persist()

    def write_memory(self, candidate: dict) -> dict:
        content = candidate["content"]
        record = {
            "memory_id": f"mem_{uuid4().hex[:12]}",
            "content": content,
            "source_id": candidate["source_id"],
            "source_type": candidate["source_type"],
            "source_trust_level": candidate["source_trust_level"],
            "risk_tags": candidate.get("risk_tags", []),
            "created_from_phase": candidate["created_from_phase"],
            "created_at": now_iso(),
        }
        self.records.append(record)
        self._persist()
        log_event(self.ctx, "memory_events", {
            "event_type": "memory_write",
            "task_id": candidate["source_id"],
            "phase": candidate["created_from_phase"],
            "memory_id": record["memory_id"],
            "source_id": record["source_id"],
            "source_type": record["source_type"],
            "source_trust_level": record["source_trust_level"],
            "content_summary": content[:160],
            "risk_tags": record["risk_tags"],
            "write_reason": "agent_observed_content",
            "content_preview": record["content"][:160],
        })
        return record

    def retrieve_memory(self, query: str, top_k: int, task_id: str) -> list[dict]:
        retrieval_context_id = f"ret_{uuid4().hex[:12]}"
        scored = []
        query_terms = set(query.lower().split())
        for record in self.records:
            content_terms = set(record["content"].lower().split())
            overlap = len(query_terms & content_terms)
            risk_bonus = 1 if record.get("risk_tags") else 0
            scored.append((overlap + risk_bonus, record))
        retrieved = [
            {**record, "retrieval_context_id": retrieval_context_id}
            for score, record in sorted(scored, key=lambda item: item[0], reverse=True)[:top_k]
            if score > 0
        ]
        log_event(self.ctx, "memory_events", {
            "event_type": "memory_retrieve",
            "task_id": task_id,
            "phase": "trigger",
            "retrieval_context_id": retrieval_context_id,
            "query": query,
            "query_summary": query[:160],
            "retrieved_memory_ids": [item["memory_id"] for item in retrieved],
            "contains_untrusted_memory": any(item["source_trust_level"] == "untrusted" for item in retrieved),
            "source_trust_levels": sorted({item["source_trust_level"] for item in retrieved}),
            "risk_tags": sorted({tag for item in retrieved for tag in item.get("risk_tags", [])}),
        })
        return retrieved

    def _persist(self) -> None:
        self.memory_path.write_text(json.dumps(self.records, ensure_ascii=False, indent=2), encoding="utf-8")
