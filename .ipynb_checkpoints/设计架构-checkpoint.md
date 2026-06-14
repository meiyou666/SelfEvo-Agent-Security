# zombie-agent-lab

一个**可运行的 baseline 自进化 agent**（基于 CrewAI），并为后续的攻防扩展预留好所有钩子。

目标：先有一个"会浏览网页 / 执行命令 / 跨会话记忆并复用"的 agent（方式 2 自动写入记忆），
之后能在**不改动核心循环**的前提下，挂上①投毒注入、②溯源记忆后端、③工具调用策略、④ASR 埋点。

---

## 1. 这套东西包含什么

```
zombie-agent-lab/
├── README.md
├── requirements.txt
├── .env.example              # 复制成 .env 填 API key
├── Dockerfile                # 沙箱（强烈建议在容器里跑）
├── config.py                 # 模型/记忆/沙箱开关（模型无关：gemini/glm/claude/openai）
├── attacker_server.py        # 本地 mock 外泄端点（仅 localhost，用于观测是否被诱导外泄）
├── run_infection.py          # 阶段一：感染（K 轮诱饵任务）
├── run_trigger.py            # 阶段二：触发（M 轮无关良性任务）
├── agent/
│   ├── crew.py               # agent/crew 构建（memory=True）—— 核心循环，扩展时基本不动这里
│   ├── tools.py              # search / read_url / execute_command（已包好策略钩子 + 注入钩子）
│   └── memory_backend.py     # 【扩展点】溯源记忆后端（当前是透传桩，后续填溯源逻辑）
└── lab/
    ├── poison.py             # 【扩展点】被投毒页面注册表（载荷指向 localhost）
    ├── tasks.py              # 诱饵任务 + 良性任务（insta-150k 加载，失败则用内置小集）
    └── metrics.py            # ASR / 记忆留存 埋点（基于工具调用审计日志，框架无关）
```

## 2. 四个扩展点（后续工作都挂在这）

| 扩展点 | 文件 | 现在的状态 | 后续填什么 |
|---|---|---|---|
| ① 投毒注入 | `lab/poison.py` | 已放论文图 7 公开载荷占位，指向 localhost | 换成你要测的载荷/语义别名 |
| ② 溯源记忆后端 | `agent/memory_backend.py` | 透传 + 打 source 标签的桩 | 让标签穿过写入/检索、加注入扫描 |
| ③ 工具调用策略 | `agent/tools.py` 的 `policy_check()` | 默认放行 + 记录 | 填"参数是否源自不可信记忆→拦截" |
| ④ ASR 埋点 | `lab/metrics.py` | 基于工具审计日志算 ASR | 直接可用，按需加指标 |

核心循环（`agent/crew.py`）和这四个点解耦，所以你做攻防时改的都是上表里的文件，不动 agent 本体。

## 3. 部署步骤

```bash
# (1) 取代码后建虚拟环境
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# (2) 配置
cp .env.example .env
#   编辑 .env：选 MODEL_PROVIDER 并填对应 API key

# (3) 起本地 mock 外泄端点（另开一个终端）
python attacker_server.py      # 监听 http://127.0.0.1:8899

# (4) 跑两个阶段
python run_infection.py        # 阶段一：感染
python run_trigger.py          # 阶段二：触发 + 打印 ASR
```

### 强烈建议在容器里跑（沙箱）
```bash
docker build -t zombie-lab .
# 容器内默认禁止对外网络，只放行到本机 attacker_server；execute_command 默认"模拟不真执行"
docker run --rm -it --network none zombie-lab python run_infection.py
```

## 4. 模型无关

`.env` 里切 `MODEL_PROVIDER`，可跑 `gemini` / `glm` / `claude` / `openai`。
CrewAI 底层走 litellm，模型串形如 `gemini/gemini-2.5-flash`、`anthropic/claude-...`。
想对照论文，先用 `gemini/gemini-2.5-flash`；想测"强模型还灵不灵"，切 `anthropic/claude-...`。

## 5. 安全须知（务必看）

- 这是**防御/复现研究**脚手架。`execute_command` **默认只模拟、不真执行**（足够测 ASR——我们要的是"agent 有没有*尝试*恶意动作"，不需要真把文件传出去）。
- 真要观测实际执行效果，只在**隔离容器**里把 `SANDBOX_ALLOW_EXEC=1` 打开，且容器 `--network none`。
- 所有"attacker 端点"都指向 `127.0.0.1`，永远别改成真实外网地址。
- `lab/poison.py` 里用的是论文已公开的图 7 载荷做占位，请勿在此基础上做规避优化后投向真实系统。

## 6. 版本说明

CrewAI 的 API 迭代较快。本脚手架用的是**稳定公开路径**（`Crew(memory=True)` + `@tool` + `Agent/Task/Crew`）。
`agent/memory_backend.py` 的自定义后端协议方法名可能随版本微调——装好后 `python -c "import crewai.memory.storage.backend as b; help(b)"` 确认一下再启用；
不启用时，agent 用 CrewAI 内置记忆也能完整跑通。
