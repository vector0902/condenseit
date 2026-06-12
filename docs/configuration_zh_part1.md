# 配置

## 文件

- `config.yaml`（或来自 `CONDENSEIT_CONFIG` 的路径）保存 feed、YouTube 频道、LLM 提供程序、预算和 VPS 设置。
- `CONDENSEIT_DATA_DIR`（默认 `./data`）保存 SQLite、磁盘上的摘要和密钥。
- `CONDENSEIT_FRONTEND_DIST`（可选）：包含 Vite SPA 输出（`index.html` 和资源）的目录。Docker Compose 将其设置为 `/app/frontend/dist`，以便当软件包安装在 `site-packages` 下时应用不会回退到传统的 Jinja 页面。

## 来源

所有来源均在 Web UI 中的 **管理 > Sources** 中管理。更改在下次摘要运行时生效，无需重启。支持以下来源类型。

![Admin sources page with generated demo data](assets/demo/desktop-admin-sources.png)

### Per-source filter rules（每个来源的过滤规则）

每个来源都可以在 **管理 > Sources**（添加或编辑来源时的 **Filter rules** 部分）中定义关键字规则。规则存储在 SQLite 中来源的 `extra_json` 中，在下次摘要运行时生效，无需重启。

匹配对文章 **标题** 加上其正文的 **前 500 个字符**（或 feed 摘要）不区分大小写。你可以使用 `*` 作为通配符：`*` 之间的每个非空段必须出现在文本中。例如：`CVE-*` 匹配包含 `cve-` 的任何字符串；`GHSA-*` 匹配 `ghsa-`；`*patch*` 匹配 `patch`。

| Rule                   | UI label             | Effect                                                                                        |
|------------------------|----------------------|-----------------------------------------------------------------------------------------------|
| **Show only if**       | `require_keywords`   | Allowlist。如果列表非空，不匹配其中任何关键字的文章在收集时被丢弃（存储前）。                 |
| **Hide keywords**      | `hide_keywords`      | Blocklist。匹配任何关键字的文章被丢弃。                                                       |
| **Highlight keywords** | `highlight_keywords` | 匹配任何关键字的文章保留，排名后获得 +2.0 偏好分数提升，并在摘要中显示 **Highlighted** 徽章。 |

规则按顺序评估：hide、show-only、highlight。Hide 和 show-only 都从管线中移除文章；highlight 仅影响排名和显示。

示例：跟踪 [Next.js releases Atom feed](https://github.com/vercel/next.js/releases.atom) 但仅展示与安全相关的发行版。将 **Show only if** 设置为诸如 `security`、`vulnerability`、`CVE-*`、`GHSA-*`、`patch`、`advisory`、`disclosure` 等术语。没有这些术语的常规版本发行版被过滤掉；一个 CVE advisory 发行版保留，可以在 **Highlight keywords** 下进一步用 `vulnerability` 高亮。

支持 RSS（包括通过 Lemmy RSS 路由的 Reddit 来源）、Google News、Hacker News、Reddit、GitHub Releases、Podcast 和 YouTube collecting 器。

### RSS / Atom

任何公共 RSS 或 Atom feed URL。大多数新闻站点和博客发布一个。

```yaml
feeds:
  - url: "https://www.example.com/rss"
    category: "General News"
    priority: 2
```

### YouTube

收集频道的最新视频。需要频道的 `channel_id`（在频道的 About 页面中找到）。

内容使用三步回退机制获取：

1. **YouTube captions**，通过 `youtube-transcript-api`，免费、即时、无需下载。
2. **Whisper transcription**（可选），如果字幕不可用，使用 `yt-dlp` 下载音频并通过 [OpenRouter Whisper API](#youtube-transcription) 转录。需要 OpenRouter API 密钥和在服务器上安装 `yt-dlp`。
3. **RSS description**，回退到作者在视频描述中编写的文本。

```yaml
youtube_channels:
  - handle: "@example"
    channel_id: "UCxxxxxxxxxxxxxxxxxxxxxxxxx"
    category: "Tech"
```

频道 feed 的瞬态 `5xx`/`429` 响应会自动重试。

> **在 VPS 上 YouTube 返回 404/500？**YouTube 经常封锁数据中心 IP 范围的频道 feed（`/feeds/videos.xml`），因此从你的笔记本电脑工作的相同 `channel_id` 可能从服务器 404。仅通过 `CONDENSEIT_YOUTUBE_PROXY` 环境变量将 YouTube 请求路由到代理（例如 `CONDENSEIT_YOUTUBE_PROXY=http://user:pass@host:port`）。也尊重标准 `HTTP_PROXY` / `HTTPS_PROXY` 变量。其他收集器不受影响。

#### YouTube transcription（YouTube 转录）

基于音频的转录大幅提升没有字幕的视频的摘要质量。在 **管理 > Digest** 下的 "YouTube transcription" 卡片中启用和配置，或在 `config.yaml` 中：

```yaml
youtube_transcription:
  enabled: false                          # 默认关闭；启用以激活
  model: "openai/whisper-large-v3-turbo"  # 快速且便宜；见下文
  max_duration_seconds: 1800              # 跳过超过 30 分钟的视频（默认）
```

| Setting                | Default                         | Description                        |
|------------------------|---------------------------------|------------------------------------|
| `enabled`              | `false`                         | 在没有字幕时启用音频转录           |
| `model`                | `openai/whisper-large-v3-turbo` | 通过 OpenRouter 的 Whisper 模型    |
| `max_duration_seconds` | `1800`                          | 跳过超过此时间的视频（60-7200 秒） |

**OpenRouter 上可用的 Whisper 模型：**

| Model                           | Speed               | Quality                     | Notes          |
|---------------------------------|---------------------|-----------------------------|----------------|
| `openai/whisper-large-v3-turbo` | 非常快（216x 实时） | 良好（12% WER）             | 推荐默认值     |
| `openai/whisper-large-v3`       | 快                  | 最佳（10.3% WER，99+ 语言） | 用于更高准确性 |

**成本**：通过你现有的 OpenRouter 密钥按音频秒数计费。一段典型的 15 分钟视频使用 `whisper-large-v3-turbo` 成本约 $0.036。支出在 **管理 > Budget** 中与摘要成本一起跟踪，并尊重你的每日/每月限制。

**服务器要求**：必须安装 `yt-dlp` 和 `ffmpeg`。两者都包含在 Docker 镜像和 VPS 预置脚本（`scripts/provision-ubuntu.sh`）中。对于现有 VPS，手动安装一次：

```bash
pip install yt-dlp
apt-get install -y ffmpeg
```

### Website watch

每次摘要运行时获取页面并报告有意义的更改。适用于没有 feed 的页面（changelogs、status pages、release notes pages）。

```yaml
watch_urls:
  - url: "https://example.com/changelog"
    category: "Developer News"
    selector: null        # CSS selector（获取器尚未使用）
    change_threshold: 0.05  # 必须改变的行比例以触发
```

### Google News search

查询 Google News 公共 RSS 搜索端点。支持所有标准 Google 搜索运算符：`site:`、`when:`、`intitle:`、`source:`、`inurl:` 等。不需要 API 密钥。

示例查询：

| Query                                      | What it returns                  |
|--------------------------------------------|----------------------------------|
| `site:reuters.com when:1d`                 | 过去 24 小时内发布的路透社文章   |
| `CVE intitle:critical when:7d`             | 过去一周的关键 CVE 头条          |
| `"supply chain" site:bleepingcomputer.com` | Bleeping Computer 上的供应链文章 |

通过 **管理 > Sources** 添加，选择类型 **Google News search**，并输入查询字符串。RSS URL 自动构造并预览。

### Hacker News

从 [官方 HN Firebase JSON API](https://hacker-news.firebaseio.com/v0/) 获取故事。不需要身份验证。

可配置选项（在添加来源表单中）：

| Field     | Default | Description                           |
|-----------|---------|---------------------------------------|
| Feed      | `top`   | `top`、`best`、`new`、`ask` 或 `show` |
| Min score | `50`    | 跳过低于此点赞数的故事                |
| Max items | `20`    | 每次摘要运行的最大故事数              |

### Reddit

从任何公共 subreddit 通过 Reddit 的公共 `.json` 端点获取帖子。不需要 API 密钥。

可配置选项：

| Field       | Default  | Description                                                    |
|-------------|----------|----------------------------------------------------------------|
| Subreddit   | （必需） | 不带 `r/` 的名称，例如 `netsec`                                |
| Sort        | `hot`    | `hot`、`new`、`top` 或 `rising`                                |
| Time filter | `day`    | 对于 `top` 排序：`hour`、`day`、`week`、`month`、`year`、`all` |
| Min score   | `10`     | 跳过低于此点赞数的帖子                                         |
| Max items   | `20`     | 每次摘要运行的最大帖子数                                       |

### GitHub Releases

通过其公共 Atom feed（`https://github.com/{owner}/{repo}/releases.atom`）跟踪任何公共 GitHub 仓库的新发布。不需要身份验证。

以 `owner/repo` 格式输入仓库，例如 `astral-sh/uv` 或 `ollama/ollama`。

### Podcasts

通过公共播客 RSS feed 跟踪新播客剧集。添加来源表单可以搜索 iTunes podcast catalog 并自动填充 feed URL，或者你直接粘贴 feed URL。不需要 API 密钥。

剧集摘要从 RSS feed 中的播客 show notes 生成。如果 feed 提供剧集或频道插图则使用。

## LLM

- `llm.provider`：`ollama`、`openrouter`、`fallback`（本地然后云端）或 `openai`。
- `llm.openrouter_pick_cheapest`：当为 `true` 时，从公共 OpenRouter 目录中选择最便宜的合适文本模型（缓存约一小时）。你仍然需要 API 密钥进行请求。
- `llm.openrouter_daily_budget_usd` / `openrouter_monthly_budget_usd`：支出上限。

### OpenAI-compatible endpoint（`provider: "openai"`）

将 CondenseIt 指向实现 `/v1/chat/completions` 端点的任何服务器。这包括 Ollama 的内置 OpenAI 兼容层、LM Studio、vLLM、llama.cpp server、text-generation-inference、真实 OpenAI、Azure OpenAI 和许多其他服务。

| Setting               | Env var               | Description                                                                   |
|-----------------------|-----------------------|-------------------------------------------------------------------------------|
| `llm.openai_base_url` | `OPENAI_API_BASE_URL` | 完整基础 URL，例如 `http://localhost:11434/v1` 或 `https://api.openai.com/v1` |
| `llm.openai_model`    | `OPENAI_MODEL`        | 服务器期望的模型名称。如果未设置则回退到顶级 `model` 字段。                   |
| `llm.openai_api_key`  | `OPENAI_API_KEY`      | API 密钥。可以为不使用身份验证的本地服务器的任何非空字符串。                  |

本地 vLLM 或 LM Studio 服务器的最小配置示例：

```yaml
llm:
  provider: "openai"
  openai_base_url: "${OPENAI_API_BASE_URL:-http://localhost:8000/v1}"
  openai_model: "gemma4-e4b-q4_m"
```

在 `.env` 中设置 `OPENAI_API_KEY`（如果服务器强制执行身份验证需要；对不需要认证的服务使用任意占位符值）。

`openai_base_url` 和 `openai_model` 也可以在 **管理 > LLM** 中实时更改，无需重启服务器。

## Digest settings（摘要设置）

以下设置可以在 **管理 > Settings** 页面实时编辑或在 `config.yaml` 中设置：

- `max_articles_per_digest`（默认 `50`）：每次摘要运行的总文章数。
- `max_articles_per_category`（默认 `5`）：平衡时每类别的容量。
- `max_article_age_hours`（默认 `36`）：排除超过此小时数的旧文章。设置为 `0` 禁用年龄过滤。
- `balance_digest_categories`（默认 `true`）：在按排名填充剩余槽位之前为每类别预留一个槽位。
- `max_key_takeaways`（默认 `5`，范围 1-10）：LLM 为每篇文章生成的要点子弹点数。
- `max_summary_paragraphs`（默认 `5`，范围 1-10）：LLM 生成的文章摘要中的段落数。
- `preferred_languages`：ISO 639-1 代码（例如 `["en", "pt"]`)。留空以接受所有语言。语言检测使用 `langdetect`。这控制收集哪些文章；不影响输出语言。
- `digest_language`（默认 `"en"`）：摘要输出的语言。设置为 ISO 639-1 代码（例如 `"fr"`、`"de"`、`"es"`）以用该语言生成摘要，或 `"source"` 以自动检测每篇文章的语言并用与文章相同的语言编写摘要。可在 **管理 > Settings** 中更改，无需重启服务器。
- `youtube_transcription.enabled`（默认 `false`）：为没有字幕的 YouTube 视频启用 Whisper 音频转录。参见 [YouTube transcription](#youtube-transcription)。

## Preferences and ranking（偏好与排名）

CondenseIt 使用多层排名引擎，融合经典信号与可选 AI 层。所有权重可在 **管理 > Digest** 中实时调整，无需重启服务器。

### Ranking pipeline（排名管线）

每次摘要运行时按以下顺序处理文章：

1. **Collect** - 从所有启用来源拉取
2. **Filter** - 年龄过滤、已读过滤、语言过滤、排除关键字
3. **Classical score** - 使用偏好引擎对每个候选者评分
4. **Embedding score** - 添加到你的评分文章中心的语义相似度（可选）
5. **Story deduplication** - 保留近重复故事中最高评分的版本
6. **LLM rerank** - 一次 LLM 调用对 top-K 候选者重新排序（可选）
7. **Category balance** - 为每类别预留槽位，然后按评分填充
8. **Summarise** - 逐篇文章的 LLM 调用，同时提取主题、实体和新颖度
9. **Persist** - 保存摘要条目和丰富数据供后续排名使用

### Classical scoring（经典评分）

经典评分器为每篇文章分配一个 `preference_score`，最多十一个命名信号的总和。所有权重默认为合理值，可以设置为 `0` 完全禁用特定信号。

| Signal            | `score_breakdown` key | What drives it                                |
|-------------------|-----------------------|-----------------------------------------------|
| Keyword high      | `keyword_high`        | 匹配 `relevance.initial_keywords.high` 术语   |
| Keyword medium    | `keyword_medium`      | 匹配 `relevance.initial_keywords.medium` 术语 |
| Keyword negative  | `keyword_negative`    | 对你永远不想要的主题的惩罚                    |
| Term overlap      | `term_overlap`        | 与你喜爱的词的 bag-of-words 重叠              |
| Bigram overlap    | `bigram_overlap`      | 与你喜爱的二元组的两词短语重叠                |
| TF-IDF cosine     | `tfidf_cosine`        | 文章与喜爱文章 TF-IDF 向量之间的余弦相似度    |
| Category          | `category`            | 文章的类别的平均评分偏差                      |
| Source            | `source`              | 文章的来源的平均评分偏差                      |
| Implicit content  | `implicit_content`    | 从 read/save/dismissed 信号构建的内容档案     |
| Implicit category | `implicit_category`   | 来自隐式互动的类别信号                        |
| Implicit source   | `implicit_source`     | 来自隐式互动的来源信号                        |
| Synonym boost     | `synonym_boost`       | 通过 `relevance.topic_synonyms` 组传播的权重  |
