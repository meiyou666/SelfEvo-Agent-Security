# ChatGPT/OpenAI 调用合并包

本包用于把当前项目从 DeepSeek 实验配置扩展到 ChatGPT/OpenAI 实验配置，并保留本次已经跑通的 OpenAI 攻击/防御结果。

## 结论

当前项目不需要为 ChatGPT 单独新增一套 Agent 代码。DeepSeek 和 ChatGPT 共用同一条 CrewAI/OpenAI-compatible 调用链路：

```text
.env
  -> config.py
  -> agent/runtime.py
  -> agent/crew.py
  -> CrewAI LLM
  -> run_attack_scenarios.py / run_infection.py / run_trigger.py
```

也就是说，调用 ChatGPT 的核心差异是 `.env` 配置，而不是新增模型调用文件。

## 需要合并或检查的文件

这些是模型调用和实验运行相关的核心文件，已复制到 `source/` 目录，方便对照合并：

```text
source/config.py
source/agent/runtime.py
source/agent/crew.py
source/agent/schemas.py
source/agent/config/agents.yaml
source/agent/config/tasks.yaml
source/run_attack_scenarios.py
source/run_infection.py
source/run_trigger.py
source/lab/tasks.py
source/lab/utils.py
source/lab/metrics.py
source/security/policy.py
source/security/tool_runtime.py
```

ChatGPT 专用配置模板在：

```text
config/.env.chatgpt.example
```

## 推荐 ChatGPT 配置

把 `config/.env.chatgpt.example` 复制为项目根目录 `.env`，再填入你的 OpenAI API key。

关键配置：

```env
AGENT_BACKEND=crewai
MODEL=gpt-5.5
LLM_PROVIDER=openai
LLM_API_KEY=replace-with-your-openai-api-key
LLM_BASE_URL=
LLM_TEMPERATURE=1
LLM_STRUCTURED_OUTPUT=off
POLICY_MODE=dry_run
```

本次验证中，以下组合可以成功调用 OpenAI：

```text
MODEL=gpt-5.5
LLM_TEMPERATURE=1
LLM_STRUCTURED_OUTPUT=off
```

不要使用：

```env
MODEL=openai/gpt-5.5
```

因为当前 CrewAI/OpenAI provider 会把它原样传给 OpenAI API，导致 `invalid model ID`。

## 运行方式

进入项目根目录：

```powershell
cd "D:\桌面\SelfEvo-Agent-Security-develop\SelfEvo-Agent-Security-develop"
```

如果已创建 `.venv`：

```powershell
.\.venv\Scripts\python.exe -m unittest discover -v
.\.venv\Scripts\python.exe -m agent.main
```

运行 ChatGPT/OpenAI 攻击对照实验：

```powershell
.\.venv\Scripts\python.exe run_attack_scenarios.py --policy baseline --agent-backend crewai
.\.venv\Scripts\python.exe run_attack_scenarios.py --policy dry_run --agent-backend crewai
.\.venv\Scripts\python.exe lab\metrics.py
```

也可以使用本包内脚本：

```powershell
.\scripts\run_openai_attack.ps1
```

## 本次 OpenAI 结果

本次已使用 OpenAI `gpt-5.5` 完成攻击/防御对照：

| 模型 | 策略 | run_id | 高风险案例 | 模拟成功 | 防护拦截 | Demo 可见效果 | 真实执行 |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: |
| OpenAI gpt-5.5 | baseline | `run_20260704_184409_0966aa` | 4 | 4 | 0 | 4 | 0 |
| OpenAI gpt-5.5 | dry_run | `run_20260704_184500_d603ab` | 4 | 0 | 4 | 0 | 0 |

原始报告已复制到：

```text
results/openai_baseline_attack_case_results.md
results/openai_dry_run_attack_case_results.md
```

## 推荐最终对比实验

为了满足“DeepSeek 和 OpenAI 都进行攻击防御，并分别阐述各自结果”的目标，最终建议固定同一套攻击样本，跑四组：

```text
DeepSeek baseline
DeepSeek dry_run
OpenAI baseline
OpenAI dry_run
```

报告中重点对比：

```text
attack_scenario_risky_tool_attempt_count
baseline_simulated_success_count
visible_demo_effect_count
defense_blocked_count
defense_block_rate
real_executed_count
```

展示口径：

```text
DeepSeek 和 OpenAI 都能在污染记忆触发下产生高风险工具调用意图；
无防护 baseline 会进入模拟危险路径；
防护开启后全部被 dry-run 拦截；
两种模型下真实执行次数均为 0。
```

## 安全说明

- 本包不包含真实 `.env`，不会包含 API key。
- `execute_command` 始终不会真实执行系统命令。
- baseline 只写入无害的 `demo_effects.jsonl`，用于展示“如果没有防护会进入危险路径”。
- dry_run 防护组不会产生 demo 攻击效果。
