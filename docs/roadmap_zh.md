# 路线图

本文档跟踪 CondenseIt 的计划功能和改进。

## YouTube 和播客转录

### 已完成

- **通过 OpenRouter Whisper 进行远程转录**，当 YouTube 自带的字幕不可用或质量不佳时，CondenseIt 可以使用 `yt-dlp` 下载音轨，并通过 OpenRouter 的 `/api/v1/audio/transcriptions` 端点（默认为 Whisper Large V3 Turbo）进行转录。此为可选功能，会跟踪预算，需要在宿主机/服务器上安装 `yt-dlp`。

### 计划中

- **本地 Whisper 转录**，在宿主机上运行 `faster-whisper`（或 `whisper.cpp`）以实现零成本、离线转录。目标是 Apple Silicon Metal 加速和 Linux 服务器上的 CUDA。用户可以在设置中选择 `local` 和 `remote` 转录模式。

  本地模式的依赖项：
  - `faster-whisper` Python 包（CTranslate2 后端）
  - 已下载的模型文件（`base`、`small` 或 `medium`，取决于硬件）
  - macOS：通过 CTranslate2 的 Metal 支持（仅限 M1+）
  - Linux：CUDA toolkit 用于 GPU 加速（提供 CPU 回退）

- **播客剧集转录**，将相同的 Whisper 管线应用到播客音频附件中。目前播客收集器仅使用 RSS show notes；转录实际语音内容将大幅提升长音频的摘要质量。

- **转录缓存**，按内容 URL 对转录结果进行 SQLite 键控存储，以便重复运行永不重新转录同一剧集/视频。

- **选择性转录**，每个来源的启用/禁用开关（某些频道始终有良好字幕；另一些则从未有过）。

## VPS / 服务器依赖项

在启用 YouTube 转录时部署到 VPS，服务器需要：

- `yt-dlp` 二进制文件（可通过 `pip install yt-dlp` 或系统包管理器安装）
- 用于临时音频文件的足够磁盘空间（约 30 MB/30 分钟视频，转录后立即清理）
- 对 `openrouter.ai` 的网络访问（如果为摘要使用 OpenRouter，则已必需）

对于未来的本地转录模式，VPS 还需要：

- `faster-whisper` 及其 CTranslate2 依赖
- 预下载的 Whisper 模型（`base` 约 150 MB，`small` 约 500 MB）
- 充足的 RAM（模型需要额外 1-2 GB）

## RSS/Atom 输出 feed

### 已完成

- **Atom feed 端点**，`GET /api/feed/atom` 将最新摘要运行时序列化为标准 Atom。每个摘项成为带有 TL;DR 作为 `<summary>` 和完整 LLM 摘要（加上要点和主题）作为 `<content type="html">` 的 `<entry>`。认证使用独立的 feed token，与管理密码分离。

- **管理 > 安全中的 feed token 管理**，用户从安全页面生成和撤销专用的 feed 访问 token。面板显示完整的 feed URL，可直接粘贴到任何 RSS 阅读器（Reeder、NetNewsWire、Miniflux、FreshRSS 等）。撤销 token 会立即使 URL 失效，不影响管理登录密码。

### 计划中

- **Google Reader API（第 2 层）**，实现最小 GReader API 子集（`stream/contents`、`subscription/list`、`mark-all-as-read`、`edit-tag`），以便原生 GReader 客户端可以订阅并将阅读/未读状态同步回偏好引擎。欢迎社区贡献，参见 [issue #4](https://github.com/wildlifechorus/condenseit/issues/4) 中的原始规范和讨论。

## 其他计划功能

_此部分将随着新功能计划的定义而逐步填充。_
