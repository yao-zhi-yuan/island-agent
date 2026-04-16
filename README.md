# FastAPI 项目

## 本地运行

```bash
uv venv
source .venv/bin/activate
cp .env.example .env
uv sync
uv run uvicorn app.main:app --reload
```

启动后访问：

- http://127.0.0.1:8000/
- http://127.0.0.1:8000/docs
- http://127.0.0.1:8000/health
- LangGraph（AG-UI）接口：http://127.0.0.1:8000/agent

### 千问（通义）配置
运行前先设置 API Key：
```bash
export DASHSCOPE_API_KEY=sk-xxxx
export TONGYI_MODEL=qwen3.5-plus   # 可选，默认就是这个值
# 可选（当 qwen3.5-* 通过 OpenAI 兼容接口访问时）：
# export DASHSCOPE_COMPAT_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
```
`app/graph.py` 中通过 LangChain 的 `ChatTongyi` 生成回复。

### Langfuse 观测配置
当前项目已接入 Langfuse，用于替代 LangSmith 进行链路观测。

需要配置以下环境变量：
```bash
export LANGFUSE_PUBLIC_KEY=pk-lf-xxxx
export LANGFUSE_SECRET_KEY=sk-lf-xxxx
export LANGFUSE_BASE_URL=http://your-langfuse-host:3000
export LANGFUSE_TRACING_ENABLED=true
```

接入效果：
- 聊天主链路会自动上报到 Langfuse
- 定时任务执行链路也会自动上报到 Langfuse
- trace 中会自动带上 `user_id`、`session_id`

### mem0 + Milvus 存储（可选）
如果你希望使用本地 mem0 + Milvus 作为持久化记忆存储，可以配置：
```bash
export MEM0_ENABLED=1
export MEM0_MILVUS_URL=http://localhost:19530
export MEM0_MILVUS_COLLECTION=mem0
export MEM0_MILVUS_EMBEDDING_DIMS=1536

# 作用域标识（至少需要一个；系统已提供默认 user_id）
export MEM0_USER_ID=your-user-id      # 可选，默认值为 default-user
export MEM0_AGENT_ID=your-agent-id    # 可选
export MEM0_RUN_ID=your-run-id        # 可选

# 本地 mem0 流程所需的 Embedding / LLM 配置（默认 provider 为 openai）
export OPENAI_API_KEY=sk-xxxx
# 可选：
# export OPENAI_BASE_URL=https://your-openai-compatible-endpoint/v1
# export MEM0_EMBEDDER_PROVIDER=openai
# export MEM0_EMBEDDER_MODEL=text-embedding-3-small
# export MEM0_LLM_PROVIDER=openai
# export MEM0_LLM_MODEL=gpt-4.1-nano-2025-04-14
# 如果你使用 DashScope 的 OpenAI 兼容接口，可配置：
# export OPENAI_API_KEY=$DASHSCOPE_API_KEY
# export OPENAI_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
```
当 `MEM0_ENABLED=1` 时，会启用 mem0 相关能力。
当前实现中，mem0 主要用于“用户画像”的语义检索层：
- PostgreSQL 保存结构化画像事实
- mem0 + Milvus 保存可检索的画像文本
- 对话结束后会先抽取候选画像，再按结构化结果写入，而不是把整轮聊天原样写入 mem0

### 分层记忆架构
当前项目的记忆系统已调整为分层设计：

- `working memory`
  - 由 LangGraph checkpoint 承担
  - 负责当前 `thread_id/session_id` 的运行态上下文
- `profile memory`
  - 用于存储用户长期画像
  - PostgreSQL 负责结构化事实存储
  - mem0 + Milvus 负责语义检索
- `episode memory`
  - 用于存储跨会话可复用的历史经验
  - 当前实现由 PostgreSQL 持久化和检索
- `instruction memory`
  - 用于存储长期规则
  - 当前支持环境变量和 PostgreSQL 两种来源

可选环境变量：
```bash
# 记忆模块 DSN；未配置时回退到 POSTGRES_DSN
export MEMORY_POSTGRES_DSN=postgresql://user:password@host:5432/database

# 全局长期规则，每行一条
export MEMORY_GLOBAL_INSTRUCTIONS="
回答时优先给结论
当信息不确定时明确说明假设
"
```

当前写入策略：
- 用户消息会先尝试抽取“用户画像”
- 完整一轮 user + assistant 会尝试抽取“历史经验”
- 召回时会按 `instruction / profile / episode` 分层注入，而不是把所有历史直接拼接到 prompt
- `instruction` 会优先注入，但会受到条数和字符预算限制
- `profile` 只注入少量高价值白名单项，避免 prompt 冗余
- `episode` 默认只注入少量最相关历史经验
- `episode` 已支持 PostgreSQL + Milvus 向量检索混合召回

可选注入控制环境变量：
```bash
export MEMORY_MAX_INSTRUCTION_ITEMS=8
export MEMORY_MAX_PROFILE_ITEMS=4
export MEMORY_MAX_EPISODE_ITEMS=2

export MEMORY_MAX_INSTRUCTION_CHARS=800
export MEMORY_MAX_PROFILE_CHARS=500
export MEMORY_MAX_EPISODE_CHARS=700
```

Episode 向量检索可选环境变量：
```bash
export MEMORY_EPISODE_MILVUS_URL=http://localhost:19530
export MEMORY_EPISODE_MILVUS_COLLECTION=memory_episodes
export MEMORY_EPISODE_MILVUS_DB_NAME=
export MEMORY_EPISODE_MILVUS_TOKEN=

# 默认可直接复用千问 embedding 模型
export MEMORY_EPISODE_EMBEDDER_MODEL=text-embedding-v4
export MEMORY_EPISODE_EMBEDDING_DIMS=1536
```

Memory 管理接口：
```bash
GET    /api/memory/status
GET    /api/memory/instructions?scope_type=global|agent|user
POST   /api/memory/instructions
DELETE /api/memory/instructions/{id}

GET    /api/memory/profiles
POST   /api/memory/profiles
DELETE /api/memory/profiles/{id}

GET    /api/memory/episodes
GET    /api/memory/recalls
```

聊天页面已内置“记忆”面板，可直接测试：
- 新增全局 / agent / user 约束
- 新增和删除用户画像
- 查看历史经验和召回日志

Instruction 约束规则说明：
- `global`：全局规则，可存在多条
- `agent`：每个用户仅保留 1 条，重复保存时会覆盖旧值
- `user`：每个用户仅保留 1 条，重复保存时会覆盖旧值

记忆压缩（第二阶段）：
- 后台会定期扫描较旧的 `episode memory`
- 使用 `qwen3-max` 把多条历史经验压缩为一条更稳定的长期经验
- 原始 episode 会被标记为 `archived`，不再参与默认召回

可选记忆压缩环境变量：
```bash
export MEMORY_COMPACTION_ENABLED=1
export MEMORY_COMPACTION_INTERVAL_SECONDS=3600
export MEMORY_COMPACTION_MIN_ITEMS=8
export MEMORY_COMPACTION_MIN_AGE_HOURS=12
export MEMORY_COMPACTION_MAX_SOURCE_ITEMS=12
export MEMORY_COMPACTION_SUMMARY_MAX_CHARS=400
export MEMORY_COMPACTION_ARCHIVE_TTL_DAYS=30
```

### Skills + MCP（可选）
`create_deep_agent(...)` 目前支持通过环境变量加载 skills 和 MCP 工具：
```bash
# 多个 skill 目录，使用逗号分隔
export DEEPAGENT_SKILLS=/skills/user,/skills/project

# JSON 对象，key 为 server 名称，value 为 MCP 连接配置
# 示例（stdio）：
export MCP_SERVERS_JSON='{"filesystem":{"transport":"stdio","command":"npx","args":["-y","@modelcontextprotocol/server-filesystem","/tmp"]}}'
```

Skills 默认目录是 `app/skills`，结构要求：`/skills/<skill-name>/SKILL.md`。
运行时会为每个聊天 `session_id` 创建独立的 sandbox workspace，并把默认 skills 同步到该 workspace 的 `/skills`。

### 会话沙箱（Docker 执行器）
当前实现采用：
- 全局单例 agent/graph
- 每个聊天 `session_id` 绑定一个独立 workspace
- 文件工具和 skills 安装落在该 session 的 workspace
- `execute` 命令通过 Docker 容器执行，并把该 workspace 挂载到容器内 `/workspace`

可选环境变量：
```bash
# sandbox 元数据表使用的 DSN，未配置时回退到 POSTGRES_DSN
export SANDBOX_POSTGRES_DSN=postgresql://user:password@host:5432/database

# workspace 根目录；不配置时默认使用系统临时目录
export SANDBOX_ROOT_DIR=/tmp/copilot-agent-sandboxes

# Docker 执行器配置
export SANDBOX_DOCKER_IMAGE=python:3.13-slim
export SANDBOX_DOCKER_NETWORK=bridge
export SANDBOX_DOCKER_MEMORY=1g
export SANDBOX_DOCKER_CPUS=1.0
export SANDBOX_DOCKER_PIDS_LIMIT=256

# 如果使用 Colima 或远端 Docker，可配置 context/host
# export SANDBOX_DOCKER_CONTEXT=colima
# export SANDBOX_DOCKER_HOST=unix:///Users/$USER/.colima/default/docker.sock

# execute 的超时和输出限制
export SANDBOX_EXEC_TIMEOUT_SECONDS=120
export SANDBOX_EXEC_MAX_OUTPUT_BYTES=100000

# 透传给 sandbox execute 的环境变量
export SANDBOX_ENV_ALLOWLIST=DASHSCOPE_API_KEY,OPENAI_API_KEY
```

要求：
- 本机 Docker daemon 必须可用
- 如果 `docker info` 失败，`execute` 也会失败

可查询某个会话的 sandbox 绑定：
- `GET /api/chat/sessions/{session_id}/sandbox`

### Docker 镜像打包与运行
当前项目已经提供：
- `/Users/sx001/Documents/copilot_agent/Dockerfile`
- `/Users/sx001/Documents/copilot_agent/docker-compose.yml`

打包前准备：
```bash
# 1) 确保宿主机 Docker daemon 可用
docker info

# 2) 创建 sandbox 工作目录
mkdir -p /srv/copilot-sandboxes

# 3) .env 中建议配置
export SANDBOX_ROOT_DIR=/srv/copilot-sandboxes
export SANDBOX_DOCKER_HOST=unix:///var/run/docker.sock
```

直接构建镜像：
```bash
docker buildx build --platform linux/amd64 -t copilot-agent:latest .
```

直接运行：
```bash
docker run -d \
  --name copilot-agent \
  -p 8000:8000 \
  --env-file .env \
  -e SANDBOX_ROOT_DIR=/srv/copilot-sandboxes \
  -e SANDBOX_DOCKER_HOST=unix:///var/run/docker.sock \
  -v /var/run/docker.sock:/var/run/docker.sock \
  -v /srv/copilot-sandboxes:/srv/copilot-sandboxes \
  copilot-agent:latest
```

使用 docker compose：
```bash
docker compose build
docker compose up -d
```

查看日志：
```bash
docker compose logs -f
```

停止服务：
```bash
docker compose down
```

说明：
- 应用容器内通过 `docker` CLI 调起 sandbox 容器，所以必须挂载 `/var/run/docker.sock`
- `SANDBOX_ROOT_DIR` 必须是宿主机真实存在的目录，并且容器内外保持同一路径
- 健康检查地址默认是 `http://127.0.0.1:8000/health`；如果配置了 `APP_API_PREFIX`，镜像内会自动改为 `http://127.0.0.1:8000<APP_API_PREFIX>/health`

### JWT -> user_id 映射（可选）
如果请求头中带有 `Authorization: Bearer <jwt>`，应用可以从中解析请求级 `user_id`，
并将其用于 mem0 记忆隔离：
```bash
export JWT_VERIFY=1
export JWT_SECRET=your-jwt-secret
export JWT_ALGORITHMS=HS256          # 支持多个值时使用逗号分隔
export JWT_USER_ID_CLAIM=user_id     # 回退 claim 为 sub
# 可选：多个候选 claim 名称，按从左到右优先级依次尝试
# export JWT_USER_ID_CLAIMS=id,loginName,user_id,sub
```
仅用于本地调试时（跳过签名校验）：
```bash
export JWT_VERIFY=0
```

在工具或自定义代码中，可以这样读取请求上下文中的 user_id：
- `from app.auth.auth_context import get_request_user_id`

### 定时任务与执行日志（PostgreSQL）
配置 PostgreSQL DSN 后即可启用后端定时任务调度：
```bash
# task 模块专用 DSN，未配置时回退到 POSTGRES_DSN
export TASKS_POSTGRES_DSN=postgresql://user:password@host:5432/database
# 调度器轮询间隔，单位秒（可选，默认 5）
export TASKS_POLL_SECONDS=5
```

API 接口（供聊天界面和日志页使用）：
- `GET /api/tasks/status`
- `POST /api/tasks`（创建任务：`once` 或 `interval`，可选 `session_id`）
- `GET /api/tasks`（查询当前用户的任务列表）
- `POST /api/tasks/{task_id}/pause`
- `POST /api/tasks/{task_id}/resume`
- `DELETE /api/tasks/{task_id}`
- `GET /api/tasks/runs`（查询当前用户的执行日志）
- `GET /api/tasks/{task_id}/runs`（查询单个任务的执行日志）

智能体可调用的任务管理工具：
- `create_scheduled_task(name, task_prompt, schedule_type, run_at_iso, interval_seconds, session_id)`
- `delete_scheduled_task(task_id)`
- `query_scheduled_tasks(mode, task_id, limit)`

## LangGraph 快速说明
- 状态：`ConversationState` 用于保存 `messages` 历史。
- 节点：`responder` 会基于最后一条用户消息生成一个简单回复。
- 入口：graph 从 `responder` 开始，并在该节点执行后结束。
- AG-UI 协议：`LangGraphAgent(name=\"echo-agent\", graph=compiled_graph)` 通过 `add_langgraph_fastapi_endpoint(app, agent, path=\"/agent\")` 挂载。
