# Progress

## 2026-06-12 (Cluster Digest)

### 实现 Cluster Digest 功能
- 修改 pipeline 做 cluster 聚合摘要（Hot News），替代每篇文章单独的 AI 总结
- 修改 `_deduplicate_stories` 返回 tuple(list, dict): 幸存文章 + cluster 映射
- 新增 `summarize_cluster` 方法（三个 provider: openai, ollama, openrouter）
- 新增 `build_cluster_digest_markdown` 函数（format.py）
- 新增 `_build_cluster_digest_items` 方法（orchestrator.py）
- 新增 `_generate_topic_label` 方法（orchestrator.py）

### Bug 修复
1. **`zip(members, summaries)` 在 summaries=[] 时不迭代**
   - 三个 provider 文件中都使用了 `zip(members, summaries)`
   - 修复：直接遍历 members，通过 summaries[i] 按索引访问（有边界检查）

2. **openai_provider.py 缺少 `import re` 和 `import json`**
   - `_parse_cluster_response` 使用了 `re.match` 和 `json.loads` 但未导入模块
   - 修复：在文件头部添加 `import json` 和 `import re`

3. **Truncation 在 cluster summarization 之前执行**
   - `ranked[:max_n]` 在 `_summarize_clusters` 之前执行
   - 但 `_summarize_clusters` 遍历的是 `cluster_map`（包含所有文章）
   - 结果：`cluster_map` 有 14 个 clusters，但 `ranked` 只有 5 篇文章
   - 修复：重新组织结构，先执行 cluster summarization，再 truncation，最后过滤 cluster_digests

4. **文章重复出现在 Hot News 和 Digests 两个 section**
   - 非 Hot News 的 cluster 成员被标记 `_independent=True`，同时出现在两个 section
   - 修复：移除 cluster_digest 模式下的 `_independent` 标志逻辑，所有文章都在 cluster 里，不应有 independent 文章

### 测试结果（4 个 sample feeds）
- 15 篇文章 → Jaccard dedup 后 14 篇（1 个 cluster 有 2 个成员）
- 14 个 clusters 全部是 singleton（1 member, 1 source）
- 没有 cluster 满足 Hot News 条件（需要 min_sources >= 3）
- 所有 14 clusters 都生成了聚合摘要
- 测试截断到 5 篇后，5 个 clusters 正确输出
- API 调用：SiliconFlow (nex-agi/Nex-N2-Pro) 正常响应 (200 OK)

## 2026-06-12

### 问题排查
- TL;DR 仅显示 "Harness"，Key Takeaways 为空或碎片

### 根因分析

1. **`_strip_non_latin_tail` 破坏中文内容**（`providers/base.py`）
   - 该函数设计用于去除英文中追加的 CJK 拒绝/注入文本
   - 但 `digest_language=zh` 时，整个返回内容都是中文，函数找到最早 CJK 块后直接截断到只剩 "Harness"
   - 修复：只在文本末尾 30% 范围内的 CJK 块才截断

2. **max_tokens 硬编码不可配置**
   - 之前 `openai_provider.py` `_chat` 默认 4096，不可调
   - 现已做成 config.yaml 可配：`llm.openai_max_tokens` / `llm.ollama_num_predict`

### 改动
- `config.py`: `LlmConfig` 新增 `openai_max_tokens` (default 4096) 和 `ollama_num_predict` (default 4096)
- `providers/base.py`: `_strip_non_latin_tail` 只处理末尾 30% 的 CJK 块
- `providers/openai_provider.py`: 接受 `max_tokens` 参数并使用
- `providers/ollama_provider.py`: 接受 `num_predict` 参数并使用
- `providers/factory.py`: 从 config 传入参数

## 2026-06-12

### Docker Build 缓存优化

### 问题
- `docker compose build` 每次全量构建，耗时过长

### 优化措施
1. **Dockerfile 分层优化**：将 `pyproject.toml` 和 `src/` 分离 COPY，依赖安装层独立，源码变动不触发 pip reinstall
2. **docker-compose.yml 添加缓存卷**：
   - `pip_cache:/root/.cache/pip` — 缓存 Python 包
   - `frontend_node_modules:/app/frontend/node_modules` — 缓存 node_modules
3. **BuildKit 缓存引用**：`cache_from` 引用已有镜像和本地缓存目录
4. **build-cache.sh 脚本**：支持 export/import 本地缓存目录

### 改动
- `Dockerfile`: 重构分层结构，依赖层与源码层分离
- `docker-compose.yml`: 添加 pip_cache 和 frontend_node_modules 卷，添加 cache_from
- `build-cache.sh`: 新增，本地缓存导出/导入/清理脚本

## 2026-06-12 (续)

### Cluster Digest 设计文档 + 示例更新

### 背景
- 用户指出 `2026-06-12-cluster-sample.md` 缺少 `req.md` 中要求的 `## Keywords` 部分
- 初始修复：手动添加 Keywords 分组（AI/大模型、开源/免费/限免、机器人/具身智能、世界杯）

### 规模认知转折
- 用户指出实际有 1848 个 feeds（完整版 OPML），而非 3 个 sample feeds
- 完整版 OPML：**1848 feeds**，30+ 个分类（`1.bili1ITTech`, `9.IT-updates`, `Blogs`, `ITFun`...）
- Trim 版：93 feeds（仅 jiqizhixin/liangziwei/xinzhiyuan）

### 设计变更
1. **Keywords → 自动主题标签**：大规模 feeds 下手动关键字分组不可行
   - 方案 A：OPML 分类作为先验信号
   - 方案 B：LLM 自动生成主题标签
   - 推荐 A+B 混合：OPML 粗分组 + LLM 跨分类打标签
2. **min_sources 阈值提高**：从 2 提升到 3-5（更多 feeds 意味着更高跨源率）
3. **输出截断**：限制 Hot News 和 Digests 条目数，避免信息过载
4. **集群优先级排序**：综合覆盖度 + 用户偏好 + 集群大小

### 改动
- `condenseit_cluster_digest_design.md`: 新增第十章 "Scale-1000：大规模 feeds 场景"
- `2026-06-12-cluster-sample.md`: 移除 Keywords 部分，改为 LLM 自动生成主题标签；添加 Digests 截断说明

### 问题
- LLM API 调用超时（ReadTimeout 120s）导致整个 digest job 失败
- `openai_provider.py` 只处理 429 重试，不处理超时
- `orchestrator.py` 使用 `pool.map()`，一个 worker 异常 → 全部中断
- 一次超时 = 整个 digest 丢失

### 修复
1. **`openai_provider.py`**: 添加超时重试逻辑
   - 捕获 `httpx.ReadTimeout`/`httpx.ConnectTimeout`/`httpcore.ReadTimeout`/`httpcore.ConnectTimeout`
   - 超时后最多重试 2 次（共 3 次尝试）
   - 重试间隔使用现有 `_RETRY_WAITS` 列表

2. **`orchestrator.py`**: 添加单篇文章容错
   - 新增 `_safe_summarize()` 包装器，捕获单个文章 summarization 异常
   - 失败的文章记录日志并返回 None，不影响其他文章
   - 处理循环跳过 None 结果的文章

### 效果
- 单个文章超时不会中断整个 digest job
- 超时文章被记录日志并跳过，其余文章正常处理
- 最多 3 次超时重试后才放弃该文章

## 2026-06-12 (Cluster Digest 实现)

### 实现
1. **config.py**: 新增 `ClusterDigestConfig` 类
   - `enabled=False` (默认关闭)
   - `min_cluster_size=2`, `min_sources=3`
   - `max_hot_news_count=10`, `max_digest_count=30`

2. **providers/base.py**: 新增 `summarize_cluster()` 抽象方法
   - 签名: `summarize_cluster(members, summaries, language) -> dict`
   - 返回: `{combined_summary, key_points, source_list}`

3. **providers/openai_provider.py**: 实现 `summarize_cluster()` + `_parse_cluster_response()`
   - 构建聚合 prompt，调用 LLM API
   - 支持 code fence 提取和 fallback

4. **providers/ollama_provider.py**: 同上，使用 ollama API

5. **providers/openrouter_provider.py**: 同上，使用 OpenRouter API

6. **digest/format.py**: 新增 `build_cluster_digest_markdown()`
   - 输出格式: Hot News (聚合摘要) + Digests (标题+链接)
   - 支持按主题标签分组

7. **pipeline/orchestrator.py**: 集成 cluster flow
   - `_deduplicate_stories` 已返回 `(survived, cluster_map)` tuple
   - 新增 `_summarize_clusters()` 方法
   - 新增 `_rebuild_clusters()` 和 `_generate_topic_label()` 辅助方法
   - 新增 `_build_cluster_digest_items()` 方法
   - 当 `cluster_digest.enabled=True` 时，跳过 per-article summary
   - 使用 `build_cluster_digest_markdown()` 替代 `generate_digest()`
   - stats 中新增 `cluster_digest` 字段

### 4 WeChat Feeds 测试（2026-06-12）
- 使用 `config_cluster_test.yaml`（4个真实微信 RSS: 机器之心、量子位、新智元、小众软件）
- 16 篇文章（小众软件6篇、量子位4篇、机器之心3篇、新智元3篇）
- 16 个 singleton clusters（所有文章主题不同，无跨源重复）
- 0 Hot News（min_sources=3，4个feeds无法达到）
- 16 Digests 正确生成
- **结论**: Cluster Digest 功能在真实 feeds 上运行正常；Hot News 需要更大规模 feeds（1848+）才有意义
