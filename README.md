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
  runtime.py              Agent backend 选择入口
  crew.py                 CrewAI crew 定义
  mock.py                 离线 mock backend
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
AGENT_BACKEND=crewai
POLICY_MODE=dry_run
MODEL=openai/gpt-4o-mini
LLM_PROVIDER=openai
LLM_API_KEY=replace-with-your-key
LLM_BASE_URL=
LLM_STRUCTURED_OUTPUT=auto
LLM_TEMPERATURE=0
CREWAI_VERBOSE=true
MAX_FIXTURE_CHARS=100000
CREWAI_TRACING_ENABLED=false
OTEL_SDK_DISABLED=true
```

DeepSeek OpenAI-compatible 示例：

```env
AGENT_BACKEND=crewai
MODEL=deepseek-v4-flash
LLM_PROVIDER=openai
LLM_API_KEY=replace-with-your-deepseek-key
LLM_BASE_URL=https://api.deepseek.com
LLM_STRUCTURED_OUTPUT=auto
```

DeepSeek 当前不使用 CrewAI 的 provider `response_format`，项目会在 DeepSeek 配置下自动改用 prompt JSON + 本地 parser。

没有 API key 时可以使用离线兜底 backend 验证日志链路：

```env
AGENT_BACKEND=mock
```

`mock` backend 不代表真实 LLM 行为，只用于验证 infection / trigger / metrics 是否能跑通。

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
- OpenAI-compatible LLM 配置，已支持 DeepSeek API。
- `AGENT_BACKEND=mock` 离线兜底，可在没有 API key 时验证完整日志链路。

未覆盖：

- 真实 LLM 实验需要可用 API key 和余额。
- `mock` backend 只能用于链路验证，不能代表真实 CrewAI/LLM 行为。
