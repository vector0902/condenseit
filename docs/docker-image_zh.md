# 预构建 Docker 镜像

CondenseIt 在每个 GitHub release 上发布一个 **仅 Web UI** 镜像。容器在端口 **8899** 上提供摘要阅读器和面板。摘要运行和 Ollama 保留在宿主机上（与 [deploy-local.md](deploy-local.md) 中的本地 Docker 设置相同）。

## 快速开始（拉取镜像）

宿主机上无需 Node.js 或 Python 构建。

```bash
git clone https://github.com/wildlifechorus/condenseit
cd condenseit
cp config.example.yaml config.yaml
cp .env.example .env
# 根据需要编辑 config.yaml 和 .env。

docker compose pull
docker compose up -d
```

打开 [http://localhost:8899](http://localhost:8899)。

在宿主机上运行摘要（Ollama 本地时使用 Metal GPU）：

```bash
./scripts/run-with-ollama.sh
# 或：condenseit run   （需要 CLI 的原生安装）
```

停止容器：

```bash
docker compose down
```

## 镜像注册表

两个注册表在每次 release 时接收相同的标签（稳定版 `2.7.5`、`2.7`、`latest`）：

| 注册表 | 镜像 |
|----------|-------|
| GitHub Container Registry | `ghcr.io/wildlifechorus/condenseit` |
| Docker Hub | `docker.io/wildlifechorus/condenseit` |

拉取特定版本：

```bash
docker pull ghcr.io/wildlifechorus/condenseit:2.7.5
docker pull docker.io/wildlifechorus/condenseit:2.7.5
```

## Compose 环境变量

[`docker-compose.yml`](../docker-compose.yml) 默认使用 GHCR `latest`：

```yaml
image: ${CONDENSEIT_IMAGE:-ghcr.io/wildlifechorus/condenseit:${CONDENSEIT_IMAGE_TAG:-latest}}
```

示例：

```bash
# 固定 GHCR 上的版本（默认注册表）
export CONDENSEIT_IMAGE_TAG=2.7.5
docker compose pull && docker compose up -d

# 改用 Docker Hub
export CONDENSEIT_IMAGE=docker.io/wildlifechorus/condenseit:latest
docker compose pull && docker compose up -d
```

当同时设置了 `image` 和 `build` 时，`docker compose up --build` 仍会本地构建并以配置的镜像名称标记结果（适合贡献者）。

## 镜像包含什么

- Python 后端和已构建的 Preact 前端（多阶段 [`Dockerfile`](../Dockerfile)）
- 系统依赖：`ffmpeg`、`libxml2`、`libxslt1.1`

你仍需从宿主机挂载：

- `config.yaml`、feed、LLM 提供程序、调度
- `./data/`、SQLite 数据库和渲染的摘要

## 维护者设置（一次性）

首次发布前，在 GitHub 仓库和注册表中完成这些步骤。

### 1. Docker Hub

1. 在 Docker Hub 上创建仓库 `wildlifechorus/condenseit`（如果不存在）。
2. 创建 Docker Hub **访问令牌**（账户设置 → 安全）。
3. 添加 GitHub 仓库密钥：
   - `DOCKERHUB_USERNAME`，你的 Docker Hub 用户名
   - `DOCKERHUB_TOKEN`，访问令牌（非你的账户密码）

### 2. GitHub Container Registry

GHCR 登录使用工作流 `GITHUB_TOKEN`（`packages: write` 权限）。不需要额外的密钥。

**首次成功工作流运行后**：

1. 在 GitHub → **Packages** 上打开仓库。
2. 选择 `condenseit` 容器包。
3. **包设置** → 将可见性更改为 **Public**，以便匿名 `docker pull` 可用。

### 3. 发布工作流

镜像由 [`.github/workflows/docker-publish.yml`](../.github/workflows/docker-publish.yml) 构建：

- **自动**：在 GitHub **release 发布时**运行（标签 `vX.Y.Z`）。
- **手动回填**：Actions → *发布 Docker 镜像* → *运行工作流*，带标签 `vX.Y.Z` 和可选的 `push_latest`。

平台：`linux/amd64`、`linux/arm64`。

每个稳定版的标签：`X.Y.Z`、`X.Y` 和 `latest`。预发行版仅获得版本标签（无 `latest`）。
