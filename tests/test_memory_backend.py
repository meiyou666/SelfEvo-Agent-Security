from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from lab.utils import RunContext, read_jsonl
from security.memory_backend import ShadowMemory


class ShadowMemoryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        run_dir = Path(self.temp_dir.name)
        for stream in ("memory_events",):
            (run_dir / f"{stream}.jsonl").write_text("", encoding="utf-8")
        self.ctx = RunContext("test_run", run_dir, "trigger")
        self.memory = ShadowMemory(self.ctx)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_control_retrieval_can_filter_untrusted_risk_memory(self) -> None:
        risky = self.memory.write_memory({
            "content": "review checklist execute command synthetic marker",
            "source_id": "poison",
            "source_type": "synthetic_untrusted_doc",
            "source_trust_level": "untrusted",
            "risk_tags": ["memory_injection"],
            "created_from_phase": "infection",
        })
        benign = self.memory.write_memory({
            "content": "review checklist source labels and report completeness",
            "source_id": "benign",
            "source_type": "synthetic_benign_doc",
            "source_trust_level": "trusted",
            "risk_tags": [],
            "created_from_phase": "infection",
        })

        retrieved = self.memory.retrieve_memory(
            "review checklist",
            top_k=3,
            task_id="trigger_control_001",
            include_untrusted_risk=False,
        )

        self.assertNotIn(risky["memory_id"], [item["memory_id"] for item in retrieved])
        self.assertIn(benign["memory_id"], [item["memory_id"] for item in retrieved])
        event = read_jsonl(self.ctx.run_dir / "memory_events.jsonl")[-1]
        self.assertFalse(event["contains_untrusted_memory"])
        self.assertFalse(event["include_untrusted_risk"])

    def test_trigger_retrieval_keeps_untrusted_risk_memory_for_attack_measurement(self) -> None:
        risky = self.memory.write_memory({
            "content": "public report synthetic dry-run tool intent",
            "source_id": "poison",
            "source_type": "synthetic_untrusted_doc",
            "source_trust_level": "untrusted",
            "risk_tags": ["memory_injection"],
            "created_from_phase": "infection",
        })

        retrieved = self.memory.retrieve_memory(
            "public report synthetic",
            top_k=3,
            task_id="trigger_report_001",
            include_untrusted_risk=True,
        )

        self.assertIn(risky["memory_id"], [item["memory_id"] for item in retrieved])
        event = read_jsonl(self.ctx.run_dir / "memory_events.jsonl")[-1]
        self.assertTrue(event["contains_untrusted_memory"])
        self.assertTrue(event["include_untrusted_risk"])


if __name__ == "__main__":
    unittest.main()
