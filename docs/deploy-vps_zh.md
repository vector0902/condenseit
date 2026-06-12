# 部署到 VPS（Ubuntu 24.04 / Hetzner）

CondenseIt 在小尺寸的 Ubuntu 24.04 VPS 上运行良好。本指南以 Hetzner Cloud 为提供商示例，但步骤同样适用于任何 Ubuntu 24.04 服务器（DigitalOcean、Linode、AWS EC2 等）。

## 架构

```
浏览器 → nginx（80/443，通过 Certbot 的 TLS）
              │
              ├── /api/** → 127.0.0.1:8765 上的 uvicorn（condenseit-web.service）
              └── /** → /var/www/your.domain（frontend/dist，静态文件）
```

- **nginx** 终止 TLS 并直接从磁盘提供静态 SPA。
- **condenseit-web.service**（systemd）在本地端口上运行 uvicorn。
- SQLite 位于 VPS 上的 `~/condenseit/data/condenseit.db`。
- 如果使用内置调度器，则处理摘要运行。

## 前置条件

| 项目                           | 说明                                                   |
|--------------------------------|--------------------------------------------------------|
| Hetzner Cloud 账户             | [console.hetzner.cloud](https://console.hetzner.cloud) |
| SSH 密钥                       | 如尚未有，请在本地生成一个                             |
| 域名                           | 通过 A 记录指向 VPS IP                                 |
| 本地工具：`uv`、`rsync`、`ssh` | macOS 已预装                                           |

## 第 1 步：创建和连接到服务器

### 通过 Hetzner Cloud 控制台

1. 前往 **New Server**。
2. 选择 **Ubuntu 24.04** 作为镜像。
3. 选择类型：**CX22**（2 vCPU，4 GB RAM）对于个人使用已足够。
4. 选择你的 SSH 密钥（或粘贴公钥）。
5. 创建服务器并记录 IP 地址。

### 通过 hcloud CLI（可选）

```bash
# 安装 hcloud
brew install hcloud   # macOS

# 创建服务器
hcloud server create \
  --name condenseit \
  --type cx22 \
  --image ubuntu-24.04 \
  --ssh-key ~/.ssh/id_ed25519.pub \
  --location nbg1
```

### 添加 SSH 别名

在本地机器的 `~/.ssh/config` 中添加：

```
Host digest-vps
    HostName 203.0.113.10      # 替换为你的实际 IP
    User root
    IdentityFile ~/.ssh/id_ed25519
```

测试连接：

```bash
ssh digest-vps 'echo ok'
```

## 第 2 步：配置服务器（一次性运行）

预置脚本在全新的 Ubuntu 24.04 服务器上安装系统依赖。从你的本地机器运行：

```bash
ssh digest-vps 'bash -s' < scripts/provision-ubuntu.sh
```

或复制到服务器并直接运行：

```bash
scp scripts/provision-ubuntu.sh digest-vps:/tmp/
ssh digest-vps 'sudo bash /tmp/provision-ubuntu.sh'
```

这将安装：nginx、python3、certbot、ufw、fail2ban、rsync、curl。还创建 2 GB 交换文件并启用无人值守安全更新。

## 第 3 步：配置本地 `.env`

在仓库根目录的 `.env` 中添加：

```
DIGEST_PWA_SSH_HOST=digest-vps       # 匹配你的 ~/.ssh/config 别名
DIGEST_PWA_DOMAIN=your.domain        # 例如 digest.example.com
CONDENSEIT_AUTH_PASSWORD=strong-password
```

`DIGEST_PWA_AUTH_PASSWORD` 仍被旧版部署接受，但新安装应使用 `CONDENSEIT_AUTH_PASSWORD`。

可选：

```
OPENROUTER_API_KEY=sk-or-...
CONDENSEIT_VPS_PORT=8765             # 默认值，如有需要可更改
CONDENSEIT_SCHEDULER_ENABLED=1      # 自动运行摘要
```

## 第 4 步：复制 nginx 模板

```bash
cp scripts/nginx/digest.example.com.conf scripts/nginx/your.domain.conf
```

编辑新文件并将 `digest.example.com` 的所有出现替换为你的实际域名。也可以更新日志路径（如需要）。

## 第 5 步：引导 VPS（一次性运行）

从你的本地机器，以项目根目录为工作目录：

```bash
./scripts/bootstrap-server.sh
```

这将：

1. 构建 Python wheel 并上传到 VPS。
2. 提示输入 OpenRouter API 密钥、应用密码和调度偏好。
3. 在 VPS 上写入 `~/condenseit/.env`（密钥保留在服务器上，不在 git 中）。
4. 安装 `condenseit-web` systemd 服务并启动它。
5. 安装并启用 nginx vhost。

## 第 6 步：部署

```bash
./scripts/deploy.sh
```

这构建前端、打包新 wheel、rsync 所有内容到 VPS，并重启服务。

## 第 7 步：启用 TLS

一旦域名的 DNS A 记录指向 VPS IP：

```bash
ssh digest-vps 'sudo certbot --nginx -d your.domain'
```

Certbot 将编辑 nginx 配置并启用带自动续期的 HTTPS。

验证续期是否有效：

```bash
ssh digest-vps 'sudo certbot renew --dry-run'
```

## 部署更新

修改代码、配置或 feed 后：

```bash
./scripts/deploy.sh
```

`deploy.sh` 停止 `condenseit-web`，可选同步数据库（`--sync-db`），在 VPS 上运行 `condenseit migrate`（应用从新安装 wheel 来的模式更改），rsync 前端，然后重新启动服务。

仅 Python 代码变更时可跳过前端构建：

```bash
./scripts/deploy.sh --skip-build
```

## 服务管理

```bash
# 查看实时日志
ssh digest-vps 'journalctl -u condenseit-web -f'

# 最后 50 行
ssh digest-vps 'journalctl -u condenseit-web -n 50'

# 状态
ssh digest-vps 'sudo systemctl status condenseit-web'

# 重启
ssh digest-vps 'sudo systemctl restart condenseit-web'

# 停止
ssh digest-vps 'sudo systemctl stop condenseit-web'
```

## 更新配置

VPS 读取 `~/condenseit/.env` 和 `~/condenseit/config.yaml`。`deploy.sh` 同步新 wheel 后，也可以推送新配置：

```bash
# 仅推送配置（不重建代码）
ssh digest-vps 'cat > ~/condenseit/config.yaml' < config.yaml
ssh digest-vps 'sudo systemctl restart condenseit-web'
```

## 备份

SQLite 数据库位于 VPS 上的 `~/condenseit/data/condenseit.db`。在重大更新前备份：

```bash
ssh digest-vps 'cp ~/condenseit/data/condenseit.db ~/condenseit/data/condenseit.db.bak'
```

或拉到本地：

```bash
rsync -avz digest-vps:~/condenseit/data/condenseit.db ./data/condenseit.db.remote
```

## 故障排除

**无法 SSH 到 VPS**

检查 `~/.ssh/config` 中的 IP 是否与 Hetzner 控制台匹配，且 SSH 密钥已添加到服务器。

**Bootstrap 失败："No nginx config found"**

按照第 4 步复制并编辑模板，然后重新运行 `./scripts/bootstrap-server.sh`。

**服务启动但域名返回 502**

systemd 服务可能在 nginx 预期的不同端口上。验证 `CONDENSEIT_VPS_PORT` 与 nginxt conf 中的 `proxy_pass` 端口匹配（默认 `8765`）。

**Certbot 失败："Connection refused"或超时**

DNS 尚未传播。等待并重试。使用
`dig +short your.domain @8.8.8.8` 检查。

**小 VPS（CX11）内存不足**

`provision-ubuntu.sh` 创建的交换文件（2 GB）应能处理此问题。或者升级到 CX22 或减少 `config.yaml` 中的 `max_articles_per_digest`。
