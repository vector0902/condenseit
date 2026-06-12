# 本地部署（你自己的机器）

CondenseIt 完全运行在你的本地机器上。这是默认模式，不需要云服务账户或付费服务。

## 两种本地设置

|              | 原生（推荐）                          | Docker Web UI                                    |
| -            | ----------------------                | ---------------                                  |
| **LLM**      | Ollama（Mac 上的 Metal）或 OpenRouter | 宿主机上的 Ollama（通过 `host.docker.internal`） |
| **摘要运行** | condenseit run 或内置调度器           | 宿主机上的 condenseit run                        |
| **Web UI**   | condenseit serve                      | Docker 容器                                      |
| **数据**     | repo 中的 ./data/                     | ./data/ 共享卷                                   |
| **要求**     | Python 3.11+，uv，Node.js             | Docker Desktop                                   |

两者共享 `./data/condenseit.db` 中的同一个 SQLite 数据库，因此你可以随时在它们之间切换。

---

## 选项 A：原生安装（推荐）

### 前置条件

| 工具    | 版本   | 安装方式                                                     |
|---------|--------|--------------------------------------------------------------|
| Python  | 3.11+  | [python.org](https://python.org) 或 `brew install python`    |
| uv      | 最新版 | `pip install uv` 或 `brew install uv`                        |
| Node.js | 18+    | [nodejs.org](https://nodejs.org) 或 `brew install node`      |
| Ollama  | 最新版 | [ollama.ai](https://ollama.ai)（仅使用 OpenRouter 时可跳过） |

### 1. 克隆并安装

```bash
git clone https://github.com/wildlifechorus/condenseit
cd condenseit
uv sync
```

### 2. 拉取语言模型（Ollama）

```bash
ollama pull llama3.2:3b
```

M 系列 Mac 上，3B 模型运行良好。如需更强大的模型：

```bash
ollama pull llama3.2
```

如果计划使用 OpenRouter 作为 LLM 提供程序，可跳过此步骤。

### 3. 复制配置文件

```bash
cp config.example.yaml config.yaml
cp .env.example .env
```

编辑 `config.yaml`：
- 在相关部分添加你的 RSS feed、YouTube 频道或监控 URL。
- `llm.provider` 默认为示例文件中的 `"openrouter"`。如果完成了第 2 步安装了 Ollama，将其改为 `"ollama"`；或保持为 `"openrouter"` 并在 `.env` 中设置 `OPENROUTER_API_KEY`。

编辑 `.env`：
- 如果 Ollama 不在默认端口上，设置 `OLLAMA_HOST`。
- 如果使用 OpenRouter，设置 `OPENROUTER_API_KEY`。

### 4. 构建前端

```bash
cd frontend && npm ci && npm run build && cd ..
```

### 5. 启动 Web UI

```bash
condenseit serve
```

或使用 uv：

```bash
uv run condenseit serve
```

打开 [http://localhost:8899](http://localhost:8899)。

移动端布局在窄屏上保留了相同的摘要操作。此屏幕截图使用生成的演示数据。

![使用生成演示数据的移动端摘要阅读器](assets/demo/mobile-digest.png)

### 6. 运行摘要

从 Web UI 头部，点击 **运行摘要**。或在第二个终端中：

```bash
condenseit run
```

### 7. 启用内置调度器（可选）

添加到 `.env`：

```
CONDENSEIT_SCHEDULER_ENABLED=1
```

然后重启服务器。摘要将按 `config.schedule.times` 中设置的时间自动运行（默认 `07:00` 和 `18:00`）。不需要 cron 或 launchd 条目。

### 更改端口

```bash
condenseit serve --port 9000
```

更新浏览器书签和在 `frontend/vite.config.ts` 中更新的 `proxy` 目标（如果你开发前端）。

---

## 选项 B：Docker（仅 Web UI）

Docker 在容器中运行网页界面。摘要运行和 Ollama 保留在宿主机上，以便 Metal GPU 加速得以保留。

### 前置条件

- Docker Desktop 4.x 或更高版本。
- 宿主机上运行的 Ollama。

### 1. 复制配置文件

```bash
cp config.example.yaml config.yaml
cp .env.example .env
```

### 2. 启动容器

**预构建镜像（推荐试用 CondenseIt）：**

```bash
docker compose pull
docker compose up -d
```

无需本地 Node.js 或 Python 构建。每次 release 时镜像发布到 [GHCR 和 Docker Hub](docker-image.md)。如需固定版本或使用 Docker Hub，参见 [docker-image.md#compose-environment-variables](docker-image_zh.md#compose-environment-variables)。

**从源码构建（贡献者）：**

```bash
CONDENSEIT_DOCKER_BUILD=1 ./scripts/docker-up.sh
# 或：CONDENSEIT_DOCKER_BUILD=1 make docker-up
# 或：docker compose up -d --build
```

打开 [http://localhost:8899](http://localhost:8899)。

容器与宿主机共享 `./data/`，因此原生运行的摘要立即反映在 UI 中。

### 3. 在宿主机上运行摘要

容器运行时，在宿主机上运行摘要（使用 Metal GPU）：

```bash
./scripts/run-with-ollama.sh
# 或：condenseit run
```

### 停止容器

```bash
make docker-down
# 或：./scripts/docker-down.sh
```

---

## LLM 提供程序比较

| 提供程序       | 费用                 | 隐私                 | 需要 GPU          |
|----------------|----------------------|----------------------|-------------------|
| Ollama（本地） | 免费                 | 所有数据保留在设备上 | 是（否则 CPU 慢） |
| OpenRouter     | 按 token 付费        | 将文章文本发送到云端 | 否                |
| 回退           | 首次免费，错误时云端 | 混合                 | 可选              |

在 `config.yaml` 中设置：

```yaml
llm:
  provider: "ollama"        # 仅本地
  # provider: "openrouter"  # 仅云端
  # provider: "fallback"    # ollama 优先，openrouter 出错时回退
```

---

## 不使用 Ollama 而使用 OpenRouter

如果你没有 GPU 或未安装 Ollama：

1. 创建免费的 [OpenRouter](https://openrouter.ai) 账户并生成密钥。
2. 添加到 `.env`：
   ```
   OPENROUTER_API_KEY=sk-or-...
   ```
3. 在 `config.yaml` 中设置：
   ```yaml
   llm:
     provider: "openrouter"
     openrouter_model: "qwen/qwen3.5-flash-02-23"
     openrouter_daily_budget_usd: 0.50
     openrouter_monthly_budget_usd: 5.0
   ```
4. 启动服务器并正常运行摘要。

管理面板中的预算页面跟踪支出。

---

## 数据目录

所有持久数据位于 `./data/`（或 `CONDENSEIT_DATA_DIR`）下：

```
data/
  condenseit.db       SQLite 数据库（评分、阅读状态、摘要）
  digests/            每次摘要运行的已渲染 HTML 和 JSON
```

卸载或清理 repo 前备份此目录：

```bash
cp -r data/ ~/condenseit-backup-$(date +%Y%m%d)
```

---

## 更新

```bash
git pull
uv sync
cd frontend && npm ci && npm run build && cd ..
# 重启 condenseit serve
```

---

## 卸载

```bash
# 停止服务器（Ctrl-C 或杀死进程）

# 移除虚拟环境和构建产物
rm -rf .venv frontend/dist frontend/node_modules dist

# 可选：移除你的数据（不可逆）
rm -rf data/
```
