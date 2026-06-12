**显式评分设置**（管理 > Digest 中，或在 `config.yaml` 中设置）：

| Setting                                 | Default | Description                    |
|-----------------------------------------|---------|--------------------------------|
| `relevance.min_ratings_for_learning`    | `5`     | 引擎激活前需要的评分数量       |
| `relevance.tfidf_preference_weight`     | `0.35`  | TF-IDF 余弦相似度权重          |
| `relevance.category_preference_weight`  | `0.6`   | 每类别平均评分权重             |
| `relevance.source_preference_weight`    | `0.3`   | 每来源平均评分权重             |
| `relevance.rating_decay_half_life_days` | `30`    | 评分年龄衰减的指数半衰期（天） |

**隐式信号设置：**

| Setting                            | Default | Description                              |
|------------------------------------|---------|------------------------------------------|
| `relevance.implicit_signal_weight` | `0.5`   | 隐式信号与显式评分的比例因子。`0` = 禁用 |

隐式操作被视为虚拟评分：

| Action         | Virtual rating        |
|----------------|-----------------------|
| Mark as read   | 3.8 stars（轻度正面） |
| Save for later | 4.5 stars（强烈正面） |
| Dismiss        | 1.5 stars（轻度负面） |

### Disliked topics（不喜欢的主题）

你永远不想阅读的主题在评分时被惩罚并被展示给 LLM reranker。Onboarding 将这些写入数据库（`bootstrap_dislikes`）；你也可以在 `config.yaml` 中列出：

```yaml
relevance:
  disliked_keywords: ["crypto", "sports", "celebrity news"]
```

单词使用子串匹配；多词短语仅当每个词都出现在标题或内容中时才匹配（所以 `celebrity news` 惩罚同时包含这两个词的文章，而不仅是 `news`）。

### Category balancing gate（类别平衡门）

类别平衡通常保证每个类别至少一个槽位以保持摘要多样化。一旦你对某个类别评分足够多次，该门将停止强制推送你始终不喜爱的类别。每类别的分数以 mean-rating-minus-3 单位学习，正值表示喜欢、负值表示不喜欢。

| Setting                                | Default | Description                                                                                             |
|----------------------------------------|---------|---------------------------------------------------------------------------------------------------------|
| `relevance.category_exclude_threshold` | `-5.0`  | 低于此分数的类别从摘要中完全丢弃。默认 −5.0 有效禁用排除；向 0 提升以激活                               |
| `relevance.category_demote_threshold`  | `-5.0`  | 低于此分数的类别失去其保证槽位并被限制在 `category_demote_cap`。默认 −5.0 有效禁用降级；向 0 提升以激活 |
| `relevance.category_demote_cap`        | `1`     | 降级的类别可保留的最大文章数                                                                            |
| `relevance.category_min_ratings`       | `8`     | 类别在被门控前需要的最小显式评分数                                                                      |

`category_min_ratings` 保护意味着只有少量早期差评的兴趣类别（例如，几个 1 星 FPV 视频）在获得公平机会前永远不会被埋没，它保持正常行为直到积累足够证据。作为安全网，如果门将移除每篇文章，返回按分数排序的前几篇文章以确保摘要永远不会被静默清空。

### Time decay（时间衰减）

所有评分（显式和隐式）以指数方式衰减，因此新近行为主导过时偏好。在 `rating_decay_half_life_days` 天后，一个评分的贡献是首次记录时的一半。你最旧评分的当前衰减权重显示在 **管理 > Preferences** 中。

### Topic synonyms（主题同义词）

同义词组让引擎在不分开评分的情况下跨相关术语传播档案权重。在 `config.yaml` 中定义：

```yaml
relevance:
  topic_synonyms:
    kubernetes: ["k8s", "helm", "kubectl"]
    security:   ["infosec", "cybersecurity", "appsec"]
```

当文章提到 `k8s` 时，引擎查找 `kubernetes` 档案条目，反之亦然。同义词提升以 `synonym_boost` 形式出现在 score breakdown 中。

### AI-powered ranking（AI 驱动排名）

三层可选 AI 层位于经典评分之上。每层独立控制、默认关闭、fail-open（损坏的 LLM 或网络错误静默回退到经典排名）。

所有 AI 设置在 **管理 > Digest** 的 AI Ranking 部分，或在 `config.yaml` 的 `relevance.*` 下。

#### Layer 1: Semantic embeddings（语义嵌入）

文章被编码为固定长度向量。引擎构建你喜爱文章的衰减加权质心和你不喜欢文章的质心。每个候选者按以下方式评分：

```
embedding_similarity = cosine(article, liked_centroid)
                     - 0.5 * cosine(article, disliked_centroid)
```

Embeddings 每篇文章计算一次并缓存在 SQLite 中（按 URL、内容哈希和模型键控），因此重新运行摘要不会重新嵌入已知文章。

| Setting                                 | Default              | Description                                       |
|-----------------------------------------|----------------------|---------------------------------------------------|
| `relevance.embedding_provider`          | `"off"`              | `"ollama"`、`"openrouter"`、`"openai"` 或 `"off"` |
| `relevance.embedding_model`             | `"nomic-embed-text"` | 嵌入模型名称                                      |
| `relevance.embedding_preference_weight` | `0.5`                | 最终分数中嵌入信号的权重                          |

推荐模型：
- **Ollama（免费）**：`nomic-embed-text` - 快速、质量强，需要首次拉取模型
- **OpenRouter**：`openai/text-embedding-3-small` - $0.02/百万 token，高质量；一次完整摘要运行通常低于 $0.001
- **OpenAI-compatible**：设置 `embedding_provider: "openai"` 以使用任何暴露 `/v1/embeddings` 的服务器。复用 `llm.openai_base_url` 和 `llm.openai_api_key`，无需额外配置。

##### Semantic duplicate detection（语义重复检测）

当嵌入提供程序激活时，管线在现有 title-similarity filter 之后运行第二次去重过滤。跨越不同来源覆盖相同事件的按余弦相似度聚类的文章；每个簇中排名最高的文章进入摘要。

| Setting                              | Default | Description                                                  |
|--------------------------------------|---------|--------------------------------------------------------------|
| `relevance.semantic_dedup_enabled`   | `true`  | 启用基于嵌入的故事去重（需要 `embedding_provider != "off"`） |
| `relevance.semantic_dedup_threshold` | `0.85`  | 两条文章被视为同一故事的余弦相似度阈值                       |

阈值指导：

- **0.90+**：仅移除几乎相同排版的文章；最低假阳性风险
- **0.85（默认）**：捕获跨来源的同一事件重复，极少假阳性
- **0.80**：激进；可能合并主题相关但真正不同的故事

两个设置均可在 **管理 > Settings** 的 "Semantic embeddings" 卡片中实时调整，无需重启服务器。

#### Layer 2: LLM topic enrichment（LLM 主题丰富）

每篇文章摘要调用现在也从相同 JSON 响应中提取结构化元数据——不需要额外 LLM 调用：

- `topics` - 3-7 小写语义主题标签（例如 `["open-source", "llm", "security"]`）
- `entities` - 提到的命名人物、组织和产品
- `novelty` - 1-5 整数评分，表示这个故事与主流报道的意外程度

这些数据存储在 `article_enrichment` 表中。引擎从你的评分构建主题偏好档案：喜欢的主题获得提升，不喜欢的主题被惩罚。Topics 和 "novel" 徽章显示在每篇文章卡片上。

| Setting                        | Default | Description                  |
|--------------------------------|---------|------------------------------|
| `relevance.topic_score_weight` | `0.3`   | topic-profile 重叠信号的权重 |

一旦你对已摘要的文章进行评分，主题丰富自动激活。除了设置非零权重外无需配置。

#### Layer 3: LLM reranker（LLM 重新排序器）

经典和嵌入评分后，引擎从你 top 喜欢/不喜欢术语、类别、来源和主题构建紧凑档案叙事。一次 LLM 调用对 top-K 候选者按你的配置文件的相关性评分并返回每个的简短原因。LLM 分数与经典分数融合：

```
final_score = (1 - blend) * classical_score + blend * llm_relevance_score
```

原因字符串存储在 `score_breakdown.llm_reason` 中，显示在每篇文章卡片的 "Why ranked here?" 面板上。

| Setting                        | Default | Description                            |
|--------------------------------|---------|----------------------------------------|
| `relevance.llm_rerank_enabled` | `false` | 启用重新排序阶段                       |
| `relevance.llm_rerank_model`   | `""`    | 重新排序模型。空 = 使用摘要器模型      |
| `relevance.llm_rerank_top_k`   | `30`    | 发送给 LLM 的候选者（1-200）           |
| `relevance.llm_rerank_blend`   | `0.3`   | LLM 分数权重（0 = 忽略，1 = 替换经典） |

**成本**：每次摘要运行一次调用，约 5K 输入 token、约 500 输出 token。在 OpenRouter 上使用便宜模型如 `deepseek/deepseek-v3` 每运行成本低于 $0.005。`llm_rerank_blend: 0.3` 是安全起点；质量满意后增加它。

**Provider selection**：重新排序器遵循与摘要相同的优先级顺序，OpenRouter（如果存在 API 密钥），然后是 OpenAI-compatible endpoint（如果 `llm.provider: "openai"` 且设置了 `llm.openai_base_url`），然后是本地 Ollama。不需要单独的 reranker-provider 配置。

### Cold-start bootstrap（冷启动引导）

AI 层和经典评分器都从初始偏好档案中受益。如果你少于 `min_ratings_for_learning` 个评分，访问 **管理 > Preferences** 并用纯文本描述你的兴趣。LLM 将你的描述转换为：

- `high_keywords` - 5-10 高优先级兴趣术语
- `medium_keywords` - 5-10 次级兴趣术语
- `dislikes` - 3-5 需要降低优先级的主题
- `synonyms` - 2-4 扩展关键词覆盖的同义词组
- `profile_summary` - 你作为读者的一到两句描述

这些数据保存到数据库并立即使用。来自 `config.yaml` 的 YAML 关键字优先；bootstrap 值填充间隙。即使学习激活后，你也可以随时从 **管理 > Preferences** 使用状态栏中的 "Re-seed with AI" 链接重新运行 bootstrap。

通过 API 可用：`POST /api/preferences/bootstrap` 带 body `{"interests": "..."}`。

### Score breakdown（分数分解）

每篇排名文章都有一个 `score_breakdown` dict，显示精确驱动其位置的因素。可见于每篇文章卡片的 "Why ranked here?" 可折叠面板。

| Key                    | Type   | Description                          |
|------------------------|--------|--------------------------------------|
| `keyword_high`         | float  | 高优先级关键字命中的贡献             |
| `keyword_medium`       | float  | 中优先级关键字命中的贡献             |
| `term_overlap`         | float  | 与你喜爱的词的 bag-of-words 重叠     |
| `bigram_overlap`       | float  | 两词短语重叠                         |
| `tfidf_cosine`         | float  | 与喜爱文章向量的 TF-IDF 余弦相似度   |
| `category`             | float  | 每类别平均评分偏差                   |
| `source`               | float  | 每来源平均评分偏差                   |
| `implicit_content`     | float  | 来自隐式信号的内容档案               |
| `implicit_category`    | float  | 来自隐式互动的类别信号               |
| `implicit_source`      | float  | 来自隐式互动的来源信号               |
| `synonym_boost`        | float  | 同义词组传播                         |
| `embedding_similarity` | float  | 嵌入质心余弦相似度（禁用时为 0）     |
| `topic_score`          | float  | LLM topic-profile 重叠（禁用时为 0） |
| `llm_rerank`           | float  | LLM reranker 融合贡献（禁用时为 0）  |
| `llm_reason`           | string | LLM reranker 的人类可读原因          |

### Learning profile（学习档案）

**管理 > Preferences** 显示完整学习状态：

- Learning status（active/inactive）和评分数
- 嵌入质心构建后的 "Semantic profile active" 徽章
- 评分分布直方图（1-5 星）
- Engagement 信号计数（read、saved、dismissed）
- Time decay info（半衰期和最旧评分权重）
- Per-category score bars
- Per-source score bars
- Content terms cloud（TF-IDF 关键字档案，按权重大小）
- Keyword phrases cloud（bigram 档案）
- AI-extracted topics cloud（来自 LLM 丰富，可用时）

![Learning profile page with generated demo data](assets/demo/desktop-preferences.png)

## Scheduling（调度管理）

在 `.env` 中设置 `CONDENSEIT_SCHEDULER_ENABLED=1` 并启动 `condenseit serve`。内置调度器按 **管理 > Schedule** 配置的时间运行摘要（存储在数据库中，覆盖 `config.schedule.times`）。无需 cron、systemd timer 或 launchd entry。详见 [scheduling.md](scheduling_zh.md)。

### Timezone（时区）

默认情况下所有计划时间视为 UTC。在 **管理 > Schedule** 或 `config.yaml` 的 `schedule.timezone` 下设置你的时区：

```yaml
schedule:
  timezone: "America/New_York"  # IANA 时区名称
  times: ["07:00", "18:00"]
```

可以使用任何 [IANA timezone name](https://en.wikipedia.org/wiki/List_of_tz_database_time_zones)（例如 `Europe/London`、`Asia/Tokyo`、`America/Los_Angeles`）。通过 UI 保存时设置存储在数据库中，覆盖 YAML 值。管理面板中显示的下次运行时间同时以你的本地时区和 UTC 显示。

> **Docker users**：`TZ=UTC` 环境变量在 `docker-compose.yml` 中默认设置，因此容器时钟匹配默认计划时区。如果你更改 `schedule.timezone`，可能还想更新 `docker-compose.yml` 中的 `TZ` 以保持日志时间戳一致。

如果你偏好外部调度（cron、systemd、launchd），`bash scripts/install.sh` 辅助工具可以为您选择的运行时间和频率输出可用于直接粘贴的片段（参见 [installation.md](installation_zh.md)）。
