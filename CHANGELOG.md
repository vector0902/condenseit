# Changelog

## Unreleased

- **Progressive partial digest output**: After Phase 1 classification completes, pipeline now writes a timestamped partial digest to `digest_<YYYY-MM-DD_HHMM>.md` and updates `latest.md` immediately, before waiting for Phase 2 aggregation. Affected: `orchestrator.py`.

- **Digest output improvements**: Three-layer info-reduction digest now uses LLM aggregate `topic_groups` and `hot_news` (instead of discarding them). Keywords section merges similar topics via synonym map (e.g., "ai agent 架构" + "agent评测" → "AI Agent"). Hot News and Digests sections grouped by semantic domain field (AI/大模型, AI Agent, 云服务/部署, 开源/社区, 硬件/系统, etc.) instead of raw RSS category. Occurrence counts shown prominently `**(N occurrences, M sources)**`.  Affected: `format.py`, `orchestrator.py`.

- **Digest summarization progress (m/n)**: Pipeline now logs `Summarized X/Y articles` after each article completes, visible in docker logs during LLM summarization phase. Affected: `orchestrator.py` `_safe_summarize` loop.
- **Docker build cache optimization**: Dockerfile layers restructured to separate dependency installation from source code COPY. `docker-compose.yml` adds `pip_cache` and `frontend_node_modules` named volumes for pip/npm cache persistence. `cache_from` references in build config for BuildKit cache reuse. New `build-cache.sh` script for local cache export/import.

- **Configurable max_tokens**: `LlmConfig` now has `openai_max_tokens` (default 4096) and `ollama_num_predict` (default 4096), settable in `config.yaml` under `llm:`. Passed through to `OpenAISummarizer` and `OllamaSummarizer`.
- **Fix CJK content destruction in Chinese digests**: `_strip_non_latin_tail` in `base.py` now only strips CJK blocks in the trailing 30% of the string, preserving legitimate Chinese TLDR/takeaways.
- **Debug logging via env vars**: `cli.py` now reads `UVICORN_LOG_LEVEL` (default `"info"`) instead of hardcoding `"info"`; `app.py` reads `CONDENSEIT_LOG_LEVEL` (default `"INFO"`) to control the condenseit logger level. Set both to `DEBUG` in `.env` to enable debug output.
- **Digest progress logging**: Pipeline now prints per-source progress during collection — e.g., `Feed 1/1850`, `YouTube 2/3`, `Collected X articles from Y sources`. Affected: `RSSCollector`, `YouTubeCollector`, and all source loops in `orchestrator.py` (Google News, HackerNews, Reddit, GitHub Releases, Podcast).
- Admin: OPML import/export, HTMX-enhanced sources table, per-source health after collects.
- Admin: Ollama pull/delete from LLM settings (host from config).
- Preferences: TF-IDF style cosine boost from ratings (`relevance.tfidf_preference_weight`).
- OpenRouter: optional cheapest-model picker (`llm.openrouter_pick_cheapest`).
- Digest pipeline: weekly model advisor snapshot stored in settings (at most every 7 days).
- Docs: `docs/` guides, `launchd/` example plist, `scripts/export-config.sh`.
- Repository: MIT `LICENSE`, `CONTRIBUTING.md`, `SECURITY.md`.
