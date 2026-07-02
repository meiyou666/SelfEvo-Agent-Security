# SelfEvo Agent Security: CrewAI Baseline

本仓库用于 Sprint0 v0.1 的 Agent 安全实验。当前 baseline 使用 CrewAI 负责 Agent 推理，安全策略、工具 dry-run、审计日志和 shadow memory 都放在 Agent 外部的 `security/` 与 runner 层。

核心约束：

- `agent/` 只负责 CrewAI 推理和结构化输出。
- `security/` 负责 policy、tool audit、dry-run 和 provenance。
- `execute_command` 永远不真实执行，只记录高风险工具意图。
- `read_url` 不访问真实网页，只读取本地 fixture。
- 指标以 JSONL 审计日志和 shadow memory 为事实来源。

## 目录结构

```text
agent/
  crew.py                 CrewAI crew 定义
  main.py                 CrewAI agent smoke run
  schemas.py              CrewAI 结构化输出 schema
  config/agents.yaml      CrewAI agent 配置
  config/tasks.yaml       CrewAI task 配置
security/
  memory_backend.py       shadow memory 与 provenance
  policy.py               外部策略判断
  tool_runtime.py         外部工具运行与审计
lab/
  tasks.py                infection / trigger 任务集
  metrics.py              JSONL 指标汇总
run_infection.py          infection 阶段入口
run_trigger.py            trigger 阶段入口
```

## 离线工具

`read_url` 是本地 fixture 读取工具，不会发起网络请求。允许范围只有：

```text
data/poison_pages/*.txt
data/fixtures/*.txt
```

示例：

```text
fixture://poison_pages/poison_001.txt
fixture://fixtures/benign_001.txt
```

路径穿越、非 `.txt` 文件、fixture 不存在或超过大小限制都会被拒绝。

`execute_command` 是命令执行意图工具，但当前实验中永远 dry-run。即使 `POLICY_MODE=allow`，runner 也不会创建进程，不会执行系统命令，只会写入脱敏后的工具调用日志。

## 安装与配置

```bash
pip install -r requirements.txt
cp .env.example .env
```

Windows PowerShell 可以使用：

```powershell
Copy-Item .env.example .env
```

`.env` 示例：

```env
EXPERIMENT_MODE=crewai
MODEL=openai/gpt-4o-mini
OPENAI_API_KEY=replace-with-your-key
LLM_TEMPERATURE=0
CREWAI_VERBOSE=true
POLICY_MODE=dry_run
MAX_FIXTURE_CHARS=100000
```

缺少 CrewAI 或 LLM 配置时，CrewAI agent 会直接失败并提示安装或配置；项目不会回退到规则型离线 Agent。

## 运行

先运行不依赖 LLM 的工具层测试：

```bash
python -m unittest discover -v
```

验证 CrewAI agent 本身：

```bash
python -m agent.main
```

运行完整实验：

```bash
python run_infection.py
python run_trigger.py
python lab/metrics.py
```

每次运行会生成：

```text
logs/runs/<run_id>/
  run_metadata.json
  memory_events.jsonl
  tool_calls.jsonl
  policy_events.jsonl
  task_events.jsonl
  errors.jsonl
  shadow_memory.json
```

报告输出：

```text
logs/runs/reports/report.md
logs/runs/reports/summary.csv
```

## 当前完成度

已完成：

- CrewAI baseline 与外部安全 runtime 分层。
- `read_url` 本地 fixture 读取。
- `execute_command` dry-run 与命令参数脱敏。
- policy event / tool call JSONL 审计。
- 工具层单元测试。

未覆盖：

- 真实 LLM 环境下的完整 infection / trigger 实验需要配置 API key 后运行。
- 当前不是完全离线 Agent；离线的是实验材料读取和高风险工具执行层。
