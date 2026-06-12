# 脚本参考

## 部署脚本

### `scripts/deploy.sh`

构建前端 SPA，打包 condenseit wheel，rsync 所有内容到 VPS，在停止服务后对生产 SQLite 数据库运行 `condenseit migrate`，然后重启 `condenseit-web` systemd 服务。

```bash
./scripts/deploy.sh              # 完整构建 + 部署
./scripts/deploy.sh --skip-build # 仅 rsync，不重新构建
```

需要在 `.env`（或 `config.yaml` 的 `vps` 部分）中设置 `DIGEST_PWA_SSH_HOST` 和 `DIGEST_PWA_DOMAIN`。

### `scripts/bootstrap-server.sh`

一次性 VPS 初始化脚本。提示输入 OpenRouter API 密钥和应用程序密码，创建 Python venv，安装 condenseit，在 VPS 上写入 `~/condenseit/.env`，使用 `EnvironmentFile` 安装 systemd 单元，并配置 nginx。

```bash
./scripts/bootstrap-server.sh
```

### `scripts/provision-ubuntu.sh`

在运行 bootstrap 之前准备一台全新的 Ubuntu 24.04 VPS：安装 nginx、python3、certbot、ufw、fail2ban、rsync，创建交换文件，并启用无人值守安全更新。

```bash
ssh digest-vps 'bash -s' < scripts/provision-ubuntu.sh
```

在 `bootstrap-server.sh` 之前运行此脚本一次。详见 [deploy-vps.md](deploy-vps.md) 的完整分步指南。

### `scripts/firebase-deploy.sh`

将完整栈部署到 Firebase Hosting + Cloud Run。启用 GCP API，首次运行时创建 Artifact Registry 仓库和 GCS 存储桶，构建前端，构建并推送 Docker 镜像，部署 Cloud Run 服务，然后将 SPA 部署到 Firebase Hosting。

```bash
./scripts/firebase-deploy.sh
./scripts/firebase-deploy.sh --skip-build  # 不重新构建直接重新部署
```

需要在 `.env` 中设置 `FIREBASE_PROJECT_ID` 以及本地安装 `gcloud`、`firebase` 和 `docker` CLI。详见 [deploy-firebase.md](deploy-firebase.md) 的完整设置指南。

## Docker 脚本

### `scripts/docker-up.sh` / `scripts/docker-down.sh`

启动或停止 Docker Web UI 容器。默认情况下，`docker-up.sh` 先运行 `docker compose pull`（尽力而为），然后运行 `docker compose up -d`，因此会使用 [docker-image.md](docker-image.md) 中发布的服务端镜像（如果可用）。设置 `CONDENSEIT_DOCKER_BUILD=1` 从源码构建。

```bash
./scripts/docker-up.sh
CONDENSEIT_DOCKER_BUILD=1 ./scripts/docker-up.sh   # 本地构建
./scripts/docker-down.sh
```

### `scripts/docker-run.sh`

在 Docker 辅助容器中运行摘要（Ollama 必须在宿主机上以 `host.docker.internal` 运行）。

### `scripts/docker-ui-digest.sh`

组合辅助脚本：启动 Web UI 容器，在宿主机上运行摘要，然后停止容器。

### `scripts/docker-dry-run.sh`

通过 Docker 约定运行的 `run-without-ollama.sh` 别名（仅收集，不使用 LLM）。

## 本地 Ollama 脚本

### `scripts/run-with-ollama.sh`

使用本地 Ollama 实例在宿主机上运行完整摘要（Apple Silicon 上使用 Metal）。

```bash
./scripts/run-with-ollama.sh
```

### `scripts/run-without-ollama.sh`

干跑：仅收集和排名 feed，不使用 LLM 摘要。适合快速测试来源和配置。

```bash
./scripts/run-without-ollama.sh
```

### `scripts/native-dry-run.sh`

`run-without-ollama.sh` 的别名。

### `scripts/native-setup.sh`

一次性本地设置：创建 Python venv，拉取配置的 Ollama 模型，并构建前端。

```bash
./scripts/native-setup.sh
```

### `scripts/native-serve.sh`

原生启动 Web UI（不使用 Docker）。如果首次运行时 `frontend/dist` 缺失则自动构建前端。

```bash
./scripts/native-serve.sh
PORT=8080 ./scripts/native-serve.sh
```

## 安装辅助工具

### `scripts/install.sh`

交互式辅助工具，检查前置条件，可选复制 `config.example.yaml` 和 `.env.example`，并输出可用于直接粘贴的 cron 行和 launchd plist 片段，供你选择的运行时间和频率使用。

```bash
bash scripts/install.sh
INSTALLER_NONINTERACTIVE=1 bash scripts/install.sh
```

> **注意：** 如果你使用 `CONDENSEIT_SCHEDULER_ENABLED=1`，内置调度器会按照 `config.schedule.times` 中设置的时间自动运行摘要。`install.sh` 仅在你偏好 cron 或 launchd 进行调度时需要。

## 维护

### `scripts/cleanup-condenseit-logs.sh`

清理旧日志文件。

```bash
./scripts/cleanup-condenseit-logs.sh all-safe
```

### `scripts/export-config.sh`

打印 sanitized 的 `config.yaml` 视图，密钥值（API 密钥、密码）已被隐藏。适合在调试时分享配置。

```bash
./scripts/export-config.sh
```

### `scripts/teardown-after-digest.sh`

在定时摘要运行后停止 Docker Web UI 栈和 Ollama Homebrew launch agent。用于在每个运行前后启动和停止服务的自动化设置中。

```bash
./scripts/teardown-after-digest.sh
```

## Makefile 快捷命令

```bash
make serve            # 本地启动 Web UI
make run              # 运行一次摘要
make dry-run          # 收集不使用 LLM
make setup            # 一次性本地设置（native-setup 的别名）
make native-setup     # 一次性本地设置
make native-serve     # 启动 Web UI（如果前端缺失则构建）
make run-with-ollama  # 使用本地 Ollama 运行完整摘要
make run-without-ollama # 干跑
make docker-up        # 启动 Docker Web UI
make docker-down      # 停止 Docker Web UI
make docker-run       # 通过 Docker 辅助运行摘要
make build-frontend   # 构建 frontend/dist
make deploy           # 构建并部署到 VPS
make bootstrap        # 一次性 VPS 初始化
make logs-clean       # 清理日志文件
make test             # 运行 pytest
make lint             # 运行 ruff
```
