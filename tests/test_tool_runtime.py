from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from lab.utils import RunContext, read_jsonl
from security.policy import policy_check
from security.tool_runtime import ToolRuntime


class ToolRuntimeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        run_dir = Path(self.temp_dir.name)
        for stream in ("policy_events", "tool_calls"):
            (run_dir / f"{stream}.jsonl").write_text("", encoding="utf-8")
        self.ctx = RunContext("test_run", run_dir, "trigger")
        self.runtime = ToolRuntime(self.ctx)
        self.task = {"task_id": "task_001", "phase": "trigger"}

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_read_url_reads_local_fixture(self) -> None:
        result = self.runtime.call_tool(
            {"tool_name": "read_url", "args": {"url": "fixture://fixtures/benign_001.txt"}},
            self.task,
            [],
        )
        self.assertTrue(result["ok"])
        self.assertTrue(result["executed"])
        self.assertIn("public facts", result["content"])

    def test_read_url_rejects_files_outside_fixture_roots(self) -> None:
        result = self.runtime.call_tool(
            {"tool_name": "read_url", "args": {"url": "README.md"}}, self.task, []
        )
        self.assertFalse(result["ok"])
        self.assertFalse(result["executed"])

    def test_read_url_rejects_path_traversal(self) -> None:
        result = self.runtime.call_tool(
            {"tool_name": "read_url", "args": {"url": "fixture://fixtures/../../README.md"}},
            self.task,
            [],
        )
        self.assertFalse(result["ok"])
        self.assertFalse(result["executed"])

    def test_read_url_rejects_missing_fixture(self) -> None:
        result = self.runtime.call_tool(
            {"tool_name": "read_url", "args": {"url": "fixture://fixtures/missing.txt"}},
            self.task,
            [],
        )
        self.assertFalse(result["ok"])
        self.assertFalse(result["executed"])
        self.assertIn("Fixture not found", result["message"])

    def test_execute_command_is_dry_run_and_redacted(self) -> None:
        result = self.runtime.call_tool(
            {"tool_name": "execute_command", "args": {"command": "create-real-side-effect"}},
            self.task,
            [],
        )
        self.assertTrue(result["ok"])
        self.assertFalse(result["executed"])
        event = read_jsonl(self.ctx.run_dir / "tool_calls.jsonl")[-1]
        self.assertEqual("REDACTED_DRY_RUN_COMMAND", event["args_redacted"]["command"])
        self.assertEqual("high", event["risk_level"])
        self.assertFalse(event["executed"])

    def test_execute_command_never_executes_in_any_policy_mode(self) -> None:
        call = {"tool_name": "execute_command", "args": {"command": "ignored"}}
        for mode in ("allow", "audit", "block", "dry_run"):
            with self.subTest(mode=mode):
                decision = policy_check(call, self.task, [], mode)
                self.assertFalse(decision["executed"])

    def test_safe_attack_simulation_fixtures_are_local_text_only(self) -> None:
        fixtures = [
            "fixture://poison_pages/attack_sim_command.txt",
            "fixture://poison_pages/attack_sim_sensitive_read.txt",
            "fixture://poison_pages/attack_sim_exfiltration.txt",
            "fixture://poison_pages/attack_sim_persistence.txt",
        ]
        for fixture in fixtures:
            with self.subTest(fixture=fixture):
                result = self.runtime.call_tool(
                    {"tool_name": "read_url", "args": {"url": fixture}},
                    self.task,
                    [],
                )
                self.assertTrue(result["ok"])
                self.assertTrue(result["executed"])
                self.assertIn("SIMULATED_", result["content"])

    def test_simulated_attack_markers_are_dry_run_only(self) -> None:
        markers = [
            "SIMULATED_COMMAND_EXECUTION_MARKER",
            "SIMULATED_SENSITIVE_READ_MARKER",
            "SIMULATED_EXFILTRATION_MARKER",
            "SIMULATED_PERSISTENCE_MARKER",
        ]
        for marker in markers:
            with self.subTest(marker=marker):
                result = self.runtime.call_tool(
                    {"tool_name": "execute_command", "args": {"command": marker}},
                    self.task,
                    [],
                )
                self.assertTrue(result["ok"])
                self.assertFalse(result["executed"])
        events = read_jsonl(self.ctx.run_dir / "tool_calls.jsonl")[-len(markers):]
        self.assertTrue(all(event["args_redacted"]["command"] == "REDACTED_DRY_RUN_COMMAND" for event in events))
        self.assertTrue(all(event["executed"] is False for event in events))

    def test_simulated_attack_after_untrusted_retrieval_is_policy_flagged(self) -> None:
        retrieved_memories = [
            {
                "memory_id": "mem_attack_sim",
                "source_trust_level": "untrusted",
                "risk_tags": ["simulated_command_execution"],
                "retrieval_context_id": "ret_attack_sim",
            }
        ]
        result = self.runtime.call_tool(
            {
                "tool_name": "execute_command",
                "args": {"command": "SIMULATED_COMMAND_EXECUTION_MARKER"},
                "derived_from_memory_ids": ["mem_attack_sim"],
                "derivation_type": "directly_derived",
            },
            self.task,
            retrieved_memories,
        )

        self.assertTrue(result["ok"])
        self.assertFalse(result["executed"])

        policy_event = read_jsonl(self.ctx.run_dir / "policy_events.jsonl")[-1]
        self.assertTrue(policy_event["contains_untrusted_memory"])
        self.assertIn("high_risk_tool_dry_run_only", policy_event["matched_rules"])
        self.assertIn("high_risk_tool_after_untrusted_retrieval", policy_event["matched_rules"])
        self.assertEqual(["simulated_command_execution"], policy_event["risk_tags"])

        tool_event = read_jsonl(self.ctx.run_dir / "tool_calls.jsonl")[-1]
        self.assertEqual(["mem_attack_sim"], tool_event["derived_from_memory_ids"])
        self.assertEqual("directly_derived", tool_event["derivation_type"])
        self.assertEqual("REDACTED_DRY_RUN_COMMAND", tool_event["args_redacted"]["command"])
        self.assertFalse(tool_event["executed"])

    def test_unknown_tool_is_logged_without_execution(self) -> None:
        result = self.runtime.call_tool(
            {"tool_name": "unknown_tool", "args": {}},
            self.task,
            [],
        )
        self.assertFalse(result["ok"])
        self.assertFalse(result["executed"])
        event = read_jsonl(self.ctx.run_dir / "tool_calls.jsonl")[-1]
        self.assertEqual("unknown_tool", event["tool_name"])
        self.assertFalse(event["executed"])
        self.assertIn("Unknown tool", event["result_summary"])


if __name__ == "__main__":
    unittest.main()
