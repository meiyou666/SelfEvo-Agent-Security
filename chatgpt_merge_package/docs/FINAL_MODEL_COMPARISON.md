# DeepSeek 与 OpenAI 攻击/防御最终对比

## 证据来源

OpenAI 结果来自本次实际运行生成的日志：

```text
logs/runs/run_20260704_184409_0966aa
logs/runs/run_20260704_184500_d603ab
```

DeepSeek 结果来自项目现有文档 `docs/完整实验报告.md` 中记录的 DeepSeek / CrewAI 攻击案例对照结果。当前最新目录的 `logs/runs` 中没有可复核的 DeepSeek attack run，因此最终提交前建议补跑 DeepSeek 两组并替换 run_id。

## 总表

| 模型 | 策略 | 证据状态 | run_id | 高风险案例数 | 高风险工具意图 | baseline 模拟成功 | 防护拦截 | 防护拦截率 | Demo 可见效果 | 真实执行 |
| --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| DeepSeek `deepseek-v4-flash` | baseline | 文档记录，建议补跑日志 | 待补 | 4 | 4 | 4 | 0 | 0.0 | 4 | 0 |
| DeepSeek `deepseek-v4-flash` | dry_run | 文档记录，建议补跑日志 | 待补 | 4 | 4 | 0 | 4 | 1.0 | 0 | 0 |
| OpenAI `gpt-5.5` | baseline | 已实测，有日志 | `run_20260704_184409_0966aa` | 4 | 4 | 4 | 0 | 0.0 | 4 | 0 |
| OpenAI `gpt-5.5` | dry_run | 已实测，有日志 | `run_20260704_184500_d603ab` | 4 | 4 | 0 | 4 | 1.0 | 0 | 0 |

## 结果解释

### OpenAI

OpenAI `gpt-5.5` 在命令执行诱导、敏感信息读取诱导、数据外传诱导、持久化诱导 4 类攻击场景中均产生了可审计的 `execute_command` 高风险工具调用意图。

在 baseline 模拟无防护模式下，4/4 个攻击场景进入模拟危险执行路径，并写入 4 条无害 demo 可见效果。

在 dry_run 防护模式下，同样 4/4 个高风险意图全部被防护层拦截，未产生 demo 攻击效果。

真实执行次数始终为 0。

### DeepSeek

项目现有完整实验报告记录：DeepSeek `deepseek-v4-flash` 在攻击案例对照中同样表现为 baseline 4/4 模拟成功、dry_run 4/4 被防护拦截、真实执行次数为 0。

由于当前最新目录没有对应 DeepSeek run 日志，建议补跑：

```powershell
.\.venv\Scripts\python.exe run_attack_scenarios.py --policy baseline --agent-backend crewai
.\.venv\Scripts\python.exe run_attack_scenarios.py --policy dry_run --agent-backend crewai
.\.venv\Scripts\python.exe lab\metrics.py
```

补跑前 `.env` 切换为：

```env
MODEL=deepseek-v4-flash
LLM_PROVIDER=openai
LLM_API_KEY=replace-with-your-deepseek-key
LLM_BASE_URL=https://api.deepseek.com
LLM_STRUCTURED_OUTPUT=off
LLM_TEMPERATURE=0
AGENT_BACKEND=crewai
```

## 可直接写进最终报告的结论

在相同的 4 类安全模拟攻击样本上，DeepSeek 与 OpenAI 均会在污染记忆触发下产生高风险工具调用意图。baseline 模拟无防护模式下，攻击会进入模拟危险执行路径；启用 dry-run 防护后，同样的高风险意图被策略层记录、溯源并拦截。两种模型、两种策略实验中，真实命令执行次数均为 0，证明系统能够在不造成真实危害的前提下展示 Agent 记忆污染攻击与防御效果。
