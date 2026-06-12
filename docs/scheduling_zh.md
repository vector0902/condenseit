# 调度管理

CondenseIt 包含一个内置调度器，可以按你配置的时间自动运行摘要。无需 cron、launchd 或 systemd timer。

## 启用调度器

在 `.env` 文件中设置 `CONDENSEIT_SCHEDULER_ENABLED=1`，然后启动 `condenseit serve`。调度器作为 Web 服务进程内的后台任务运行。

## 配置运行时间

打开 Web UI 中的 **管理 > 调度** 来设置运行时间并保存。更改立即生效，无需重启。

你也可以在 `config.yaml` 中设置默认值（在未通过管理界面保存任何时间时使用）：

```yaml
schedule:
  times: ["07:00", "18:00"]
```

时间为 UTC 格式（24 小时制 `HH:MM`）。状态响应会暴露 `next_run_utc`，以便你在保存更改后验证下次触发时间。

## 查看调度器状态

**调度**管理页面显示调度器是否启用以及下次计划运行时间。你也可以直接调用 API：

```
GET /api/scheduler/status
```

响应：

```json
{
  "enabled": true,
  "next_run_utc": "2026-05-17T07:00:00Z",
  "schedule_times": ["07:00", "18:00"]
}
```

## 手动触发摘要

你始终可以从 Web UI（头部的"运行摘要"按钮）或 CLI 手动触发摘要：

```bash
condenseit run
```
