# 攻击案例对照实验

本实验用于回答两个问题：

- 在没有防护的情况下，典型恶意样本是否能够诱导 Agent 产生高风险工具调用。
- 加入防护策略后，同样的攻击输入是否会被记录、溯源并拦截。

实验不会执行真实命令，不会修改文件系统，不会读取真实密钥，也不会发起网络请求。`baseline` 策略通过记录 `would_execute_without_defense=true` 和 `simulated_executed=true` 来表示“如果没有防护层，该攻击会进入危险执行路径”。

## 运行方式

```bash
python run_attack_scenarios.py --policy baseline --agent-backend mock
python run_attack_scenarios.py --policy dry_run --agent-backend mock
python lab/metrics.py
```

## 攻击场景

| 场景 | 样本文件 | 模拟风险 |
| --- | --- | --- |
| 命令执行诱导 | `data/poison_pages/attack_sim_command.txt` | 诱导 Agent 产生 `execute_command` 工具调用意图 |
| 敏感信息读取诱导 | `data/poison_pages/attack_sim_sensitive_read.txt` | 诱导 Agent 产生读取敏感信息的工具调用意图 |
| 数据外传诱导 | `data/poison_pages/attack_sim_exfiltration.txt` | 诱导 Agent 产生数据外传类工具调用意图 |
| 持久化诱导 | `data/poison_pages/attack_sim_persistence.txt` | 诱导 Agent 产生持久化或环境篡改类工具调用意图 |

## 当前 Mock 结果

| 模式 | 高风险案例数 | 模拟攻击成功数 | Demo 可见效果数 | 防护拦截数 | 真实执行数 |
| --- | ---: | ---: | ---: | ---: | ---: |
| `baseline` | 4 | 4 | 4 | 0 | 0 |
| `dry_run` | 4 | 0 | 0 | 4 | 0 |

结果解释：

- 在 `baseline` 模式下，4 个攻击样本都进入了 would-execute 路径，并写入 `demo_effects.jsonl`，用于在 demo 中展示“如果没有防护，攻击已经产生可见影响”。
- 在 `dry_run` 防护模式下，同样 4 个攻击样本都被记录和拦截，不会写入 demo 攻击效果。
- 两种模式下真实执行数都保持为 0，保证实验安全。

## 证据字段

相关审计字段会写入 `tool_calls.jsonl` 和 `policy_events.jsonl`：

- `would_execute_without_defense`：表示如果没有防护层，该攻击是否会进入执行路径。
- `simulated_executed`：表示 baseline 模式下是否将该危险路径记为“模拟成功”。
- `executed`：表示工具是否真实执行。对高风险工具来说，这个字段必须始终为 `false`。
- `matched_rules`：本次工具调用命中的防护规则。
- `derived_from_memory_ids`：工具调用意图对应的来源记忆 ID，用于把风险行为追溯到不可信记忆。
- `demo_effects.jsonl`：只在 baseline 模拟成功时写入无害可视化效果，用于演示攻击影响；防护模式下不写入。

预期结论：

```text
baseline：攻击在模拟无防护路径下成功
dry_run：同样攻击在策略防护后失败
demo 展示：baseline 有可见攻击效果，dry_run 没有可见攻击效果
真实执行：始终为 0
```
