# Progress

## 2026-06-17

### Digest 输出 3 层降维改造

**问题**: 之前 digest 输出存在以下问题：
1. 关键词碎片化：60+ 组关键词（每篇文章 3 个 topic 直接作为关键词组）
2. LLM aggregate 的 `topic_groups` 和 `hot_news` 被计算后直接丢弃，未使用
3. Hot News / Digests 仅按 RSS 原始 category 分组（"General"），无语义领域分组
4. 覆盖度计数不明显

**改动**:
1. `format.py`:
   - 新增 `_KEYWORD_SYNONYMS` 同义词映射表（~70 条规则），将类似主题合并为规范关键词组
   - 新增 `_merge_keyword()` 使用同义词映射
   - 新增 `_keywords_from_topic_groups()` 处理 LLM aggregate 返回的 topic_groups
   - 新增 `_DOMAIN_RULES` 语义领域定义（11 个领域），包含 AI/大模型、AI Agent、云服务/部署、开源/社区等
   - 新增 `_assign_domain()` 基于 topics/title/tldr 智能分配领域
   - 新增 `_group_by_domain()` 将条目按领域分组
   - 新增 `_all_articles()` 展平 categorized dict
   - `build_digest_markdown()` 优先使用 topic_groups（LLM aggregate）构建关键词索引；支持 hot_news_entries
   - 无 topic_groups 时 fallback 到 per-article topics + 同义词合并
   - `_add_hot_item()` 覆盖度计数加粗显示 `**(N occurrences, M sources)**`
   - Digests 区在有 topic_groups 时按语义领域分组

2. `orchestrator.py`:
   - 解析 LLM aggregate 返回的 topic_groups（index → entry dict）
   - 解析 hot_news indices → hot_entries
   - 传入 coverage_config 供 format.py 使用

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

### Digest Job 超时容错修复

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
