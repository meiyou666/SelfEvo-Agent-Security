from __future__ import annotations

import html
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from config import LOG_ROOT
from lab.utils import read_jsonl


def _latest_attack_run(policy_mode: str) -> Path | None:
    candidates = []
    for run_dir in LOG_ROOT.glob("run_*"):
        metadata_path = run_dir / "run_metadata.json"
        if not metadata_path.exists():
            continue
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        if metadata.get("policy_mode") == policy_mode and str(metadata.get("phase", "")).startswith("attack_"):
            candidates.append(run_dir)
    return max(candidates, key=lambda path: path.stat().st_mtime) if candidates else None


def _case_rows(run_dir: Path | None) -> list[dict]:
    if run_dir is None:
        return []
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
    return [
        {
            "run_id": metadata["run_id"],
            "policy_mode": metadata["policy_mode"],
            "case": titles.get(event["task_id"], event["task_id"]),
            "would_execute": event.get("would_execute_without_defense", False),
            "visible_effect": demo_effects.get(event["tool_call_id"], {}).get(
                "visible_effect",
                "防护生效，无 demo 攻击效果",
            ),
            "real_executed": event.get("executed", False),
            "rules": ", ".join(event.get("matched_rules", [])),
        }
        for event in tool_calls
    ]


def render_dashboard(output_path: Path) -> Path:
    baseline_rows = _case_rows(_latest_attack_run("baseline"))
    dry_run_rows = _case_rows(_latest_attack_run("dry_run"))
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(_html_document(baseline_rows, dry_run_rows), encoding="utf-8")
    return output_path


def _html_document(baseline_rows: list[dict], dry_run_rows: list[dict]) -> str:
    return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <title>Agent 安全攻击防御 Demo</title>
  <style>
    body {{ font-family: Arial, sans-serif; margin: 32px; line-height: 1.5; }}
    table {{ border-collapse: collapse; width: 100%; margin: 16px 0 32px; }}
    th, td {{ border: 1px solid #ddd; padding: 8px; vertical-align: top; }}
    th {{ background: #f5f5f5; }}
    .bad {{ color: #b42318; font-weight: 700; }}
    .good {{ color: #067647; font-weight: 700; }}
    code {{ background: #f5f5f5; padding: 2px 4px; }}
  </style>
</head>
<body>
  <h1>Agent 记忆污染攻击/防御 Demo</h1>
  <p>本页面由本地 JSONL 审计日志生成。所有攻击效果均为安全模拟，真实执行次数始终为 0。</p>
  <h2>无防护 baseline：攻击产生可见效果</h2>
  {_table(baseline_rows, show_attack=True)}
  <h2>开启 dry_run 防护：攻击被拦截</h2>
  {_table(dry_run_rows, show_attack=False)}
  <h2>结论</h2>
  <p><span class="bad">baseline</span> 展示攻击会进入模拟危险路径；
  <span class="good">dry_run</span> 展示同样攻击被防护层拦截。两组实验均不执行真实危险操作。</p>
</body>
</html>
"""


def _table(rows: list[dict], show_attack: bool) -> str:
    if not rows:
        return "<p>暂无对应运行日志，请先运行攻击案例对照实验。</p>"
    body = "\n".join(
        "<tr>"
        f"<td>{html.escape(row['case'])}</td>"
        f"<td>{html.escape(row['policy_mode'])}</td>"
        f"<td>{'是' if row['would_execute'] else '否'}</td>"
        f"<td class=\"{'bad' if show_attack else 'good'}\">{html.escape(row['visible_effect'])}</td>"
        f"<td>{'是' if row['real_executed'] else '否'}</td>"
        f"<td><code>{html.escape(row['rules'])}</code></td>"
        "</tr>"
        for row in rows
    )
    return (
        "<table>"
        "<thead><tr><th>案例</th><th>策略</th><th>无防护是否会执行</th>"
        "<th>Demo 可见效果</th><th>真实执行</th><th>命中规则</th></tr></thead>"
        f"<tbody>{body}</tbody></table>"
    )


def main() -> None:
    output_path = LOG_ROOT / "reports" / "demo_dashboard.html"
    print(f"demo dashboard: {render_dashboard(output_path)}")


if __name__ == "__main__":
    main()
