# 部署到 Firebase

CondenseIt 可以部署到 Google 的 Firebase / Cloud Run 平台。前端 SPA 从 Firebase Hosting（全球 CDN）提供，Python FastAPI 后端在 Cloud Run 上运行。

## 架构

```
浏览器 → Firebase Hosting（CDN）
                │
                ├── /api/** → Cloud Run（condenseit-api）
                │               FastAPI + Uvicorn + SQLite
                │               GCS bucket 用于数据持久化
                └── /** → Preact SPA（frontend/dist）
```

- **Firebase Hosting** 通过静态 CDN 站点提供 `frontend/dist`。
- **Cloud Run** 运行容器化的 Python 后端（参见 `Dockerfile.cloudrun`）。
  - Firebase Hosting 将 `/api/**` 透明地重写为 Cloud Run 服务。
  - 你也可以直接通过其自己的 URL 访问 Cloud Run 服务。
- **GCS bucket** 通过 Cloud Storage FUSE 作为文件系统卷挂载到 Cloud Run 容器内，为 SQLite 数据库提供跨容器重启和新部署的持久化存储。

## 前置条件

### 本地机器

| 工具           | 用途               | 安装                                                              |
|----------------|--------------------|-------------------------------------------------------------------|
| `gcloud` CLI   | GCP 操作           | [cloud.google.com/sdk](https://cloud.google.com/sdk/docs/install) |
| `firebase` CLI | Hosting 部署       | `npm install -g firebase-tools`                                   |
| Docker         | 构建容器镜像       | [docs.docker.com](https://docs.docker.com/get-docker/)            |
| Node.js 18+    | 构建前端           | [nodejs.org](https://nodejs.org)                                  |
| `uv`           | 可选，用于本地开发 | `pip install uv`                                                  |

### Google Cloud / Firebase 项目

1. 在 [console.firebase.google.com](https://console.firebase.google.com) 创建项目。
2. 启用 **Blaze（按量付费）** 计费计划（Cloud Run 必需）。
3. 记录你的 **项目 ID**（在控制台头部分显示）。

## 一次性设置

### 1. 认证

```bash
gcloud auth login
gcloud auth application-default login
firebase login
```

### 2. 设置项目 ID

添加到 `.env`：

```
FIREBASE_PROJECT_ID=your-project-id
```

或在你的 shell 中导出：

```bash
export FIREBASE_PROJECT_ID=your-project-id
```

### 3. 配置密钥和密钥

将你的密钥添加到 `.env`（参见 `.env.example` 获取完整列表）：

```
# 云端 LLM 必需（如果仅需要 UI + 本地 Ollama 同步则跳过）
OPENROUTER_API_KEY=sk-or-...

# 任何面向公网的部署强烈建议
CONDENSEIT_AUTH_PASSWORD=your-strong-password

# 首次部署时自动生成；设置以避免会话重置
DIGEST_PWA_SESSION_SECRET=
```

`DIGEST_PWA_AUTH_PASSWORD` 仍被旧版部署接受，但新安装应使用 `CONDENSEIT_AUTH_PASSWORD`。

### 4. 复制 `.firebaserc`

```bash
cp .firebaserc.example .firebaserc
# 编辑 .firebaserc 并将 YOUR_FIREBASE_PROJECT_ID 替换为你的项目 ID
```

### 5. 部署

```bash
./scripts/firebase-deploy.sh
```

脚本将：

1. 启用所需的 GCP APIs（Cloud Run、Artifact Registry、Cloud Storage）。
2. 创建 Artifact Registry 仓库以存储 Docker 镜像。
3. 创建用于持久化数据的 GCS 存储桶。
4. 构建前端 SPA。
5. 构建并推送 Docker 镜像（`Dockerfile.cloudrun`）。
6. 部署 Cloud Run 服务并将 GCS 卷挂载到 `/app/data`。
7. 将 SPA 部署到 Firebase Hosting。
8. 打印实时 URL。

## 自定义域名

1. 打开 **Firebase Console > Hosting > Add custom domain**。
2. 遵循 DNS 验证步骤。
3. Firebase 自动配置 TLS 证书。

如果使用自定义域名，更新 `firebase.json` 以匹配 Cloud Run 区域的 rewrite（参见 `scripts/firebase-deploy.sh` 中的说明）。

## 部署更新

修改代码、feed 或配置后重新运行部署脚本：

```bash
./scripts/firebase-deploy.sh
```

如果仅更改 Cloud Run 环境变量，可以跳过构建步骤：

```bash
./scripts/firebase-deploy.sh --skip-build
```

## 数据持久化

GCS 存储桶（默认 `<project>-condenseit-data`）通过 Cloud Storage FUSE 挂载在 Cloud Run 容器内的 `/app/data`。SQLite 数据库、摘要和配置存储在那里。

注意：Cloud Storage FUSE 的延迟高于本地磁盘。对于非常频繁的摘要运行，这是可接受的；对于读密集型工作负载，考虑 Cloud SQL（需要模式迁移）。

## 内置调度器

部署脚本默认启用 `CONDENSEIT_SCHEDULER_ENABLED=1`。服务将按 `config.schedule.times`（默认 `07:00` 和 `18:00`）中的 UTC 时间运行摘要。启用调度器时，部署脚本保持一个 Cloud Run 实例热启动以便进程内的调度器可以准时触发。

禁用调度器：

```
CONDENSEIT_SCHEDULER_ENABLED=0  # 在部署前的 .env 中
```

## 查看日志

```bash
gcloud run services logs read condenseit-api --region us-central1 --limit 100
```

或实时流式传输：

```bash
gcloud beta run services logs tail condenseit-api --region us-central1
```

## 成本估算（2026 年）

Cloud Run 和 Firebase Hosting 有慷慨的免费层。对于每日两次运行并有偶发 Web 流量的个人摘要：

| 服务              | 典型成本                   |
|-------------------|----------------------------|
| Firebase Hosting  | 免费（包含 10 GB/月 传输） |
| Cloud Run         | 免费层覆盖大部分个人使用   |
| Artifact Registry | 镜像约 $0.10/GB/月         |
| GCS bucket        | SQLite 可忽略（< 50 MB）   |

## 拆除

```bash
# 删除 Cloud Run 服务
gcloud run services delete condenseit-api --region us-central1

# 删除 Firebase Hosting 部署
firebase hosting:disable

# 删除 GCS bucket（警告：删除所有摘要数据）
gcloud storage rm --recursive gs://YOUR_PROJECT-condenseit-data

# 删除 Artifact Registry 仓库
gcloud artifacts repositories delete condenseit --location us-central1
```

## 故障排除

**Firebase Hosting 部署失败，提示 "not logged in"**

```bash
firebase login
```

**Cloud Run 部署失败，提示 "gcloud CLI version" 错误**

更新 gcloud：

```bash
gcloud components update
```

**Cloud Run 上的卷挂载失败**

Cloud Storage FUSE 需要 **2 代执行环境** 和 Cloud Run API v2。确保你运行了 `gcloud services enable run.googleapis.com` 且你的 `gcloud` CLI 是最新的。

**Firebase Hosting 的 API 返回 404，但在 Cloud Run URL 上直接工作**

检查 `firebase.json` 中的 `serviceId` 和 `region` 是否与你的 Cloud Run 服务匹配。`firebase.json` 中的区域必须与 `CLOUD_RUN_REGION` 匹配。

**每次重新部署后会话注销**

在 `.env` 中设置固定的 `DIGEST_PWA_SESSION_SECRET` 并重新部署。
