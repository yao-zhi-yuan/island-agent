# Lighting Step 1A 新手本地联调手册

这份手册用于验证 lighting 业务域第 1 周最小闭环：

```text
创建照明设计项目 -> 更新 ProjectState -> 查询项目并读回 ProjectState -> 确认数据写入 Postgres
```

当前 Step 1A 只验证项目状态持久化，不包含 graph、tools、prompt、frontend，也不包含完整 CRUD。

## 1. 前置准备

进入项目目录：

```bash
cd /Users/yaozhiyuan/Documents/vscode/island-agent
```

确认 `uv` 可用：

```bash
uv --version
```

看到类似下面输出算成功：

```text
uv 0.x.x
```

确认 Docker 可用：

```bash
docker --version
```

看到类似下面输出算成功：

```text
Docker version xx.x.x
```

如果后续 Docker 命令提示不能连接 Docker daemon，说明 Docker Desktop 没启动，需要先打开 Docker Desktop。

安装项目依赖：

```bash
uv sync
```

看到依赖安装完成且没有报错，算成功。

## 2. 启动数据库

本地联调推荐用 Docker 启动一个 Postgres。这里把宿主机端口设为 `55432`，避免和本机已有 `5432` 冲突。

```bash
docker run --name island-agent-postgres \
  -e POSTGRES_PASSWORD=postgres \
  -e POSTGRES_DB=island_agent \
  -p 55432:5432 \
  -d postgres:16-alpine
```

看到一串容器 ID，算启动成功。

检查 Postgres 是否准备好：

```bash
docker exec island-agent-postgres pg_isready -U postgres -d island_agent
```

看到下面输出算成功：

```text
/var/run/postgresql:5432 - accepting connections
```

如果提示容器已存在，可以直接启动已有容器：

```bash
docker start island-agent-postgres
```

再检查一次：

```bash
docker exec island-agent-postgres pg_isready -U postgres -d island_agent
```

## 3. 配置环境变量

### 配置 qwen3.6-plus

当前仓库通过 DashScope 调用千问模型，key 配在 `DASHSCOPE_API_KEY`。

在当前终端执行：

```bash
export DASHSCOPE_API_KEY="你的 DashScope API Key"
export AGENT_MODEL="qwen3.6-plus"
```

看到什么算成功：

```bash
echo $DASHSCOPE_API_KEY
echo $AGENT_MODEL
```

能看到你刚才配置的 key 和 `qwen3.6-plus`，算成功。

也可以写到项目根目录 `.env` 文件里：

```bash
cat > .env <<'EOF'
DASHSCOPE_API_KEY=你的 DashScope API Key
AGENT_MODEL=qwen3.6-plus
LIGHTING_POSTGRES_DSN=postgresql://postgres:postgres@127.0.0.1:55432/island_agent
EOF
```

`app/main.py` 已经调用 `load_dotenv()`，启动 FastAPI 时会读取 `.env`。

### 配置 lighting 数据库

推荐显式配置 lighting 专用 DSN：

```bash
export LIGHTING_POSTGRES_DSN="postgresql://postgres:postgres@127.0.0.1:55432/island_agent"
```

确认配置生效：

```bash
echo $LIGHTING_POSTGRES_DSN
```

看到下面内容算成功：

```text
postgresql://postgres:postgres@127.0.0.1:55432/island_agent
```

### LIGHTING_POSTGRES_DSN 与 POSTGRES_DSN 的优先级

lighting store 的数据库连接优先级是：

```text
LIGHTING_POSTGRES_DSN 优先
POSTGRES_DSN 兜底
```

也就是说：

1. 如果配置了 `LIGHTING_POSTGRES_DSN`，lighting store 使用它。
2. 如果没有配置 `LIGHTING_POSTGRES_DSN`，但配置了 `POSTGRES_DSN`，lighting store 使用 `POSTGRES_DSN`。
3. 如果两个都没有配置，lighting store 不会启用，调用 lighting API 会返回 `503 lighting store not enabled`。

如果你希望所有模块共用同一个数据库，也可以只配置：

```bash
export POSTGRES_DSN="postgresql://postgres:postgres@127.0.0.1:55432/island_agent"
```

但 Step 1A 联调建议使用更明确的：

```bash
export LIGHTING_POSTGRES_DSN="postgresql://postgres:postgres@127.0.0.1:55432/island_agent"
```

## 4. 启动 FastAPI

启动服务：

```bash
cd /Users/yaozhiyuan/Documents/vscode/island-agent
uv run uvicorn app.main:app --reload
```

看到类似下面输出算成功：

```text
Uvicorn running on http://127.0.0.1:8000
[startup] Swagger UI: http://127.0.0.1:8000/docs
[startup] H5 Chat: http://127.0.0.1:8000/chat
[startup] AGUI Chat Endpoint: http://127.0.0.1:8000/v1/chat
```

再开一个新终端，测试健康检查：

```bash
curl -s http://127.0.0.1:8000/health
```

看到下面输出算成功：

```json
{"status":"ok"}
```

### 确认 lighting store 实际连到了哪个数据库

当前 Step 1A 没有做 `/api/lighting/status` 接口，所以最直接的确认方式是看你当前进程的环境变量：

```bash
echo $LIGHTING_POSTGRES_DSN
echo $POSTGRES_DSN
```

判断规则：

```text
如果 LIGHTING_POSTGRES_DSN 有值，lighting store 连它。
如果 LIGHTING_POSTGRES_DSN 为空但 POSTGRES_DSN 有值，lighting store 连 POSTGRES_DSN。
```

如果你用的是本手册里的配置，lighting store 实际连接的是：

```text
postgresql://postgres:postgres@127.0.0.1:55432/island_agent
```

还可以通过 Postgres 表验证连接是否正确。启动 FastAPI 后，执行：

```bash
docker exec -it island-agent-postgres psql -U postgres -d island_agent -c "\dt"
```

看到 `lighting_projects` 表，说明 FastAPI 启动时 lighting store 已连到这个数据库并建表成功。

## 5. 调接口验证

Step 1A 只有三个 lighting 接口：

```text
POST  /api/lighting/projects
GET   /api/lighting/projects/{project_id}
PATCH /api/lighting/projects/{project_id}/state
```

### 5.1 创建项目

```bash
curl -s -X POST http://127.0.0.1:8000/api/lighting/projects \
  -H 'Content-Type: application/json' \
  -d '{
    "session_id": "demo-session-001",
    "title": "卧室照明设计",
    "initial_requirement": "设计一个温馨卧室"
  }'
```

看到类似下面结果算成功：

```json
{
  "id": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
  "user_id": "demo-user",
  "session_id": "demo-session-001",
  "title": "卧室照明设计",
  "project_state": {
    "stage": "requirement",
    "requirement_spec": {
      "initial_requirement": "设计一个温馨卧室"
    },
    "geometry_spec": {},
    "design_strategy": {},
    "fixture_selection": {},
    "layout_plan": {},
    "quality_report": {},
    "delivery_package": {}
  },
  "created_at": "...",
  "updated_at": "..."
}
```

把返回的 `id` 保存到环境变量：

```bash
export PROJECT_ID="上一步返回的 id"
```

例如：

```bash
export PROJECT_ID="93d5fa26-0f6e-4e70-8536-493941893f0a"
```

### 5.2 查询项目

```bash
curl -s http://127.0.0.1:8000/api/lighting/projects/$PROJECT_ID
```

看到同一个 `id`，并且能看到 `project_state`，算成功。

### 5.3 更新 ProjectState

```bash
curl -s -X PATCH http://127.0.0.1:8000/api/lighting/projects/$PROJECT_ID/state \
  -H 'Content-Type: application/json' \
  -d '{
    "project_state": {
      "stage": "geometry",
      "requirement_spec": {
        "space_type": "bedroom",
        "style": "warm"
      },
      "geometry_spec": {
        "width": 4,
        "length": 3
      },
      "design_strategy": {},
      "fixture_selection": {},
      "layout_plan": {},
      "quality_report": {},
      "delivery_package": {}
    }
  }'
```

看到返回里的 `stage` 变成下面这样，算成功：

```json
"stage": "geometry"
```

并且能看到：

```json
"requirement_spec": {
  "space_type": "bedroom",
  "style": "warm"
}
```

### 5.4 再次查询确认读回

```bash
curl -s http://127.0.0.1:8000/api/lighting/projects/$PROJECT_ID
```

看到刚才 PATCH 的 `stage=geometry`、`space_type=bedroom`、`style=warm` 仍然存在，说明 `ProjectState` 已经写入 Postgres 并能读回。

### 5.5 使用仓库已有验证脚本

当前仓库已经提供 Step 1A 验证脚本：

```bash
LIGHTING_POSTGRES_DSN="postgresql://postgres:postgres@127.0.0.1:55432/island_agent" \
PYTHONDONTWRITEBYTECODE=1 \
UV_CACHE_DIR=/tmp/island-agent-uv-cache \
uv run python scripts/verify_lighting_step1a.py
```

看到下面输出算成功：

```text
lighting Step 1A verification passed
project_id=...
owner_user_id=...
outsider_get_status=404
```

这个脚本会验证：

1. 创建项目成功。
2. PATCH 更新 `ProjectState` 成功。
3. GET 能读回更新后的 `ProjectState`。
4. owner 用户能访问自己的项目。
5. outsider 用户访问同一个项目返回 `404`。
6. 脚本结束后会清理自己创建的测试数据。

## 6. 直接查询 Postgres 表

进入 Postgres：

```bash
docker exec -it island-agent-postgres psql -U postgres -d island_agent
```

看到下面提示符算成功：

```text
island_agent=#
```

查看表：

```sql
\dt
```

看到 `lighting_projects`，算成功。

查看表结构：

```sql
\d lighting_projects
```

应该能看到这些字段：

```text
id
user_id
session_id
title
project_state
created_at
updated_at
```

其中 `project_state` 类型是 `jsonb`。`JSONB` 可以理解为 Postgres 里保存 JSON 的字段类型，适合保存会逐步扩展的项目状态。

查询最近的项目：

```sql
SELECT id, user_id, session_id, title, project_state
FROM lighting_projects
ORDER BY updated_at DESC
LIMIT 5;
```

看到你刚才创建的项目，算成功。

只查某个项目的 `ProjectState`：

```sql
SELECT project_state
FROM lighting_projects
WHERE id = '21af2172-ce85-42b7-a509-4c3b7b0fee9d';
```

如果看到 PATCH 后的内容，比如：

```json
{
  "stage": "geometry",
  "requirement_spec": {
    "space_type": "bedroom",
    "style": "warm"
  }
}
```

说明数据库持久化正确。

退出 Postgres：

```sql
\q
```

## 7. 常见报错与排查

### 7.1 `DASHSCOPE_API_KEY is not set`

原因：FastAPI 启动时会构建 Agent，需要千问 key。

处理：

```bash
export DASHSCOPE_API_KEY="你的 DashScope API Key"
export AGENT_MODEL="qwen3.6-plus"
uv run uvicorn app.main:app --reload
```

看到 `Uvicorn running on http://127.0.0.1:8000` 算成功。

### 7.2 `lighting store not enabled`

原因：没有配置 `LIGHTING_POSTGRES_DSN` 或 `POSTGRES_DSN`。

处理：

```bash
export LIGHTING_POSTGRES_DSN="postgresql://postgres:postgres@127.0.0.1:55432/island_agent"
uv run uvicorn app.main:app --reload
```

重新调用创建项目接口，能返回项目 JSON 算成功。

### 7.3 `connection refused`

原因：Postgres 没启动，或者 DSN 端口写错。

排查：

```bash
docker ps
docker exec island-agent-postgres pg_isready -U postgres -d island_agent
```

如果容器没运行：

```bash
docker start island-agent-postgres
```

看到 `accepting connections` 算成功。

### 7.4 `port is already allocated`

原因：`55432` 端口被占用。

查看占用：

```bash
lsof -nP -iTCP:55432 -sTCP:LISTEN
```

也可以换一个端口，比如 `55433`：

```bash
docker run --name island-agent-postgres-2 \
  -e POSTGRES_PASSWORD=postgres \
  -e POSTGRES_DB=island_agent \
  -p 55433:5432 \
  -d postgres:16-alpine
```

然后修改 DSN：

```bash
export LIGHTING_POSTGRES_DSN="postgresql://postgres:postgres@127.0.0.1:55433/island_agent"
```

### 7.5 `404 lighting project not found`

常见原因：

1. `PROJECT_ID` 填错了。
2. 项目属于另一个 `user_id`。
3. 你用验证脚本创建的项目已经被脚本清理。

排查：

```bash
echo $PROJECT_ID
```

直接查数据库：

```bash
docker exec -it island-agent-postgres psql -U postgres -d island_agent
```

```sql
SELECT id, user_id, title
FROM lighting_projects
ORDER BY updated_at DESC
LIMIT 10;
```

能看到项目 ID 和 user_id，说明数据在库里。

### 7.6 `422 Unprocessable Entity`

原因：请求 JSON 不符合接口 schema，最常见是 PATCH 时少了 `project_state` 外层。

正确结构：

```json
{
  "project_state": {
    "stage": "geometry",
    "requirement_spec": {},
    "geometry_spec": {},
    "design_strategy": {},
    "fixture_selection": {},
    "layout_plan": {},
    "quality_report": {},
    "delivery_package": {}
  }
}
```

### 7.7 `Cannot connect to the Docker daemon`

原因：Docker Desktop 没启动。

处理：打开 Docker Desktop，等它启动完成后执行：

```bash
docker ps
```

看到类似下面表头，算成功：

```text
CONTAINER ID   IMAGE   COMMAND
```

## 最小联调链路速记

```text
启动 Postgres
-> 配置 LIGHTING_POSTGRES_DSN
-> 配置 DASHSCOPE_API_KEY 和 AGENT_MODEL=qwen3.6-plus
-> 启动 FastAPI
-> POST 创建项目
-> PATCH 更新 ProjectState
-> GET 读回项目
-> psql 查询 lighting_projects 表
```

