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
