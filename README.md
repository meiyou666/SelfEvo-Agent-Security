# SelfEvo Agent Security：CrewAI Baseline

这个实验现在使用 **完整 CrewAI agent** 作为 baseline。`agent/` 目录只包含 CrewAI agent/crew 相关实现；安全防范、策略判断、dry-run、审计日志和 shadow memory 运行时被隔离到 `security/` 与 runner 层。

当前默认运行模式是 `crewai`。项目对齐 Sprint0 v0.1 实验约束：只做防御实验，`execute_command` 永远不真实执行，指标以 shadow memory 与 JSONL 审计日志为真相源。

## 目录结构

```text
agent/
  crew.py                 CrewAI crew 定义
  main.py                 CrewAI agent 独立 smoke run
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

## 安装与配置

```bash
pip install -r requirements.txt
cp .env.example .env
```

配置环境变量：

```bash
export EXPERIMENT_MODE=crewai
export MODEL=openai/gpt-4o-mini
export OPENAI_API_KEY=你的密钥
export LLM_TEMPERATURE=0
export CREWAI_VERBOSE=true
```

缺少 CrewAI 或 LLM 配置时，agent 会直接失败并提示安装/配置，不再回退到规则型离线 agent。

## 运行

先验证 CrewAI agent 本身：

```bash
python -m agent.main
```

再运行完整实验：

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

报告输出到：

```text
logs/runs/reports/report.md
logs/runs/reports/summary.csv
```

指标包括任务级 `attempted_asr`、`pre_policy_asr`、`post_policy_asr`，以及工具级 `block_rate` 和 `false_positive_rate`。

## 架构边界

- `agent/`：只负责 CrewAI 推理和结构化输出。
- `security/`：负责 policy、dry-run、tool audit、shadow memory provenance。
- runner：负责连接 CrewAI agent 输出与外部安全运行层。
- metrics：只读取 JSONL 日志，不读取 CrewAI 内部状态。

CrewAI agent 可以输出工具意图，但是否执行、是否 dry-run、如何审计，全部由 agent 外部的 `security/` 层决定。

`execute_command` 是高风险工具意图：无论 policy mode 是 `dry_run`、`audit`、`block` 还是 `allow`，当前版本都只记录意图与决策，日志中的 `executed` 必须保持 `false`。
