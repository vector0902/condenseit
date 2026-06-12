# 本地安装

本指南涵盖使用 [uv](https://docs.astral.sh/uv/)（推荐）的**原生**安装，使你匹配 `requires-python` 和 [`pyproject.toml`](../pyproject.toml) 中的依赖项（`>=3.11`）。

Docker 仅运行 Web UI；使用本地 LLM 的摘要仍在宿主机上运行。如需预构建镜像，参见 [docker-image.md](docker-image.md)。如需 `scripts/*.sh` 和 Make 目标的完整映射，参见 [scripts.md](scripts.md)。

## 前置条件

- **Python 3.11+**（3.12 也可以）。
- **uv**（安装：参见 [uv 安装](https://docs.astral.sh/uv/getting-started/installation/)）。
- **Git**（用于克隆仓库）。
- **Ollama**，如果要在运行 `condenseit run` 的机器上使用默认的 `ollama` 提供程序（干跑或仅 OpenRouter 设置不需要）。

## 克隆并同步

```bash
git clone https://github.com/wildlifechorus/condenseit
cd condenseit
uv sync
```

可选开发工具（mypy、pytest、ruff）：

```bash
uv sync --extra dev
```

## 配置文件

1. 将示例 YAML 复制到仓库根目录旁边（或稍后设置 `CONDENSEIT_CONFIG`）：

   ```bash
   cp config.example.yaml config.yaml
   ```

2. 复制环境模板并编辑值（git 中没有真实密钥）：

   ```bash
   cp .env.example .env
   ```

根据需要调整 `config.yaml` 中的 feed，并在 `.env` 中设置 `OLLAMA_HOST`、`OLLAMA_MODEL` 和任何 API 密钥。参见 [configuration.md](configuration.md)。

## 首次运行

从仓库根目录，依赖安装完成后：

```bash
uv run condenseit run
```

启动 Web UI：

```bash
uv run condenseit serve
```

CLI 入口点声明在 `pyproject.toml` 中为 `condenseit = "condenseit.cli:cli"`。

## 交互式安装器（配置 + 调度片段）

> **提示：** 如果在 `.env` 中设置 `CONDENSEIT_SCHEDULER_ENABLED=1`，内置调度器会按照 `config.schedule.times` 中的时间自动运行摘要。你可以在此情况下完全跳过安装器。

检查前置条件，可选地从示例创建 `config.yaml` / `.env`，并输出**可用于直接粘贴**的 cron 行和 **launchd** plist 模板供你选择的运行时间和频率使用：

```bash
bash scripts/install.sh
```

从仓库根目录也可以运行：

```bash
bash install.sh
```

用于自动化或冒烟测试（无提示、默认仓库根目录、`09:00`、每天一次）：

```bash
INSTALLER_NONINTERACTIVE=1 bash scripts/install.sh
```

可选环境变量（非交互式或稍后扩展脚本时跳过提示）：`INSTALL_DIR`、`INSTALLER_FIRST_TIME`、`INSTALLER_CADENCE`（`1`、`2` 或 `3`）、`INSTALLER_SKIP_COPY`（`1` 跳过配置复制提示）。

生成的行使用你解析的 `cd` 路径和 `uv` 位置，以便你可以直接本地粘贴；分享输出时请清理路径。

参见 [scheduling.md](scheduling.md) 了解手动 cron、systemd 和 LaunchAgent 设置。**Windows** 不受安装器覆盖；在宿主机上使用任务计划程序或在 **WSL** 下运行 CondenseIt 并遵循 [scheduling.md](scheduling.md) 中的 Linux 部分。
