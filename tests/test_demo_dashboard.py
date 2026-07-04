from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from lab.demo_dashboard import render_dashboard


class DemoDashboardTests(unittest.TestCase):
    def test_render_dashboard_contains_attack_and_defense_sections(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            output_path = Path(temp) / "demo_dashboard.html"
            render_dashboard(output_path)

            content = output_path.read_text(encoding="utf-8")
            self.assertIn("Agent 记忆污染攻击/防御 Demo", content)
            self.assertIn("无防护 baseline", content)
            self.assertIn("开启 dry_run 防护", content)
            self.assertIn("真实执行次数始终为 0", content)


if __name__ == "__main__":
    unittest.main()
