# 入门指南

如需完整**本地安装**（uv、`config.yaml`、`.env`、首次运行），参见 [installation.md](installation.md)。要自动运行摘要，在 `.env` 中设置 `CONDENSEIT_SCHEDULER_ENABLED=1` — 无需 cron 或 launchd。详见 [scheduling.md](scheduling.md) 及相关的外部调度选项。

快速路径：

1. 将 `config.example.yaml` 复制到 `config.yaml` 并调整 feed 和频道。
2. 选择 LLM 后端：
   - **Ollama（本地）**：在宿主机上安装 Ollama（Mac：Metal GPU），拉取模型（`ollama pull llama3.2:3b`），并在 `config.yaml` 中设置 `llm.provider: "ollama"`。
   - **OpenRouter（云端）**：设置 `llm.provider: "openrouter"` 并在 `.env` 中添加 `OPENROUTER_API_KEY`。
   - **OpenAI 兼容服务器**（LM Studio、vLLM、llama.cpp 等）：设置 `llm.provider: "openai"`，`llm.openai_base_url` 为你的服务器的基础 URL，并在 `.env` 中设置 `OPENAI_API_KEY`。
3. 安装依赖：`uv sync`（参见 [installation.md](installation.md)）或使用带 `pip install -e ".[dev]"` 的 venv。
4. 运行 Web UI：`condenseit serve`（或 `make docker-up` 仅 Docker UI）。
5. 运行摘要：使用头部中的 **运行摘要**，或 `uv run condenseit run`（如果你的 shell 使用项目 venv，则为 `condenseit run`）。

Web UI 在一个地方为你提供摘要阅读器、评分控制、稍后阅读操作和管理页面。此屏幕截图使用生成的演示数据。

要在手机上将 CondenseIt 打开为原生应用，参见 [add-to-home-screen.md](add-to-home-screen.md)。

![使用演示数据的桌面摘要阅读器](assets/demo/desktop-digest.png)

参见 [configuration.md](configuration.md) 了解 YAML 和环境变量。

如需 **Docker UI + 宿主机摘要**、干跑以及每个脚本的作用，参见 [scripts.md](scripts.md)。

可选：`bash scripts/install.sh`（或从仓库根目录运行 `bash install.sh`）输出你选择的运行时间和频率的 cron 和 LaunchAgent 片段（参见 [installation.md](installation.md)）。
