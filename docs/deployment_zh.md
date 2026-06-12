# 部署

CondenseIt 以两种模式运行：本地（在你的机器上）或远程（在 VPS 上）。两者使用相同的 Web UI、API 和管理面板。

## 本地部署

在你的机器上启动 Web UI 和管理面板：

```bash
condenseit serve --port 8899
```

打开 `http://localhost:8899`。从 UI 或 `condenseit run` 运行摘要。

启用内置调度器以使摘要自动运行：

```
CONDENSEIT_SCHEDULER_ENABLED=1  # 在 .env 中
```

调度器读取 `config.schedule.times`（默认 `["07:00", "18:00"]`）。

## 远程部署（VPS）

### 一次性服务器设置

1. 复制 nginx 模板并编辑以匹配你的域名：

   ```bash
   cp scripts/nginx/digest.example.com.conf scripts/nginx/your.domain.conf
   # 在文件中替换 digest.example.com 为你的域名
   ```

2. 在 `.env` 中设置 SSH 连接：

   ```
   DIGEST_PWA_SSH_HOST=your-ssh-alias   # 或 user@ip
   DIGEST_PWA_DOMAIN=your.domain
   ```

3. 运行引导脚本（提示输入密钥）：

   ```bash
   ./scripts/bootstrap-server.sh
   ```

   这将安装 condenseit、systemd 服务、nginx vhost，并在 VPS 上写入 `~/condenseit/.env`，包含你的 OpenRouter 密钥和应用密码。

4. 获取 TLS 证书（DNS 指向 VPS 后）：

   ```bash
   ssh your-vps 'sudo certbot --nginx -d your.domain'
   ```

### 部署更新

```bash
./scripts/deploy.sh
```

这构建前端、打包 wheel、rsync 所有内容到 VPS，并重启 `condenseit-web` 服务。

### 服务管理

```bash
# 日志
ssh your-vps 'journalctl -u condenseit-web -f'

# 状态
ssh your-vps 'sudo systemctl status condenseit-web'

# 重启
ssh your-vps 'sudo systemctl restart condenseit-web'
```

## 环境变量

参见 [`.env.example`](../.env.example) 中所有带注释的变量。
参见 [`configuration.md`](configuration.md) 中的 YAML 配置选项。
