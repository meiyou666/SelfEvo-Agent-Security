# 合并说明

## ChatGPT 调用相关文件是什么

当前项目没有单独的 `openai_agent.py` 或 `chatgpt_client.py`。ChatGPT/OpenAI 调用复用已有 DeepSeek 的 OpenAI-compatible 接口。

真正相关的文件是：

```text
config.py
agent/runtime.py
agent/crew.py
agent/schemas.py
agent/config/agents.yaml
agent/config/tasks.yaml
```

实验运行与结果统计相关文件是：

```text
run_attack_scenarios.py
run_infection.py
run_trigger.py
lab/tasks.py
lab/utils.py
lab/metrics.py
security/policy.py
security/tool_runtime.py
```

## 合并时优先检查

1. `config.py` 是否仍然读取这些环境变量：

```text
MODEL
LLM_PROVIDER
LLM_API_KEY
LLM_BASE_URL
LLM_STRUCTURED_OUTPUT
LLM_TEMPERATURE
AGENT_BACKEND
POLICY_MODE
```

2. `agent/crew.py` 中 `_build_llm()` 是否把以上配置传给 CrewAI `LLM(...)`。

3. `agent/crew.py` 中 `_supports_provider_response_format()` 是否允许关闭结构化输出。

4. `run_attack_scenarios.py` 运行真实模型时必须使用：

```powershell
--agent-backend crewai
```

不能使用：

```powershell
--agent-backend mock
```

## 最小合并策略

如果你们已有 DeepSeek 代码，通常只需要合并：

```text
config/.env.chatgpt.example
README.md 中 OpenAI 配置说明
docs/OPENAI_RESULTS.md 中结果表
```

代码文件不一定需要重复合并，除非你们现有分支缺少：

```text
LLM_STRUCTURED_OUTPUT
LLM_TEMPERATURE
run_attack_scenarios.py
baseline / dry_run 指标字段
```

## 重要配置差异

DeepSeek 常用：

```env
MODEL=deepseek-v4-flash
LLM_BASE_URL=https://api.deepseek.com
LLM_STRUCTURED_OUTPUT=off
LLM_TEMPERATURE=0
```

OpenAI 本次跑通：

```env
MODEL=gpt-5.5
LLM_BASE_URL=
LLM_STRUCTURED_OUTPUT=off
LLM_TEMPERATURE=1
```

注意：不要写 `MODEL=openai/gpt-5.5`，本项目当前 CrewAI/OpenAI provider 会把它原样传给 OpenAI API，导致模型 ID 无效。
