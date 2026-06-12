# Changelog

## Unreleased

- **Cluster Digest bug fixes**: Fixed four bugs in cluster digest implementation: (1) `zip(members, summaries)` in all 3 providers skipped iteration when `summaries=[]` (cluster digest mode) — replaced with direct `enumerate(members)` with safe index lookup; (2) Missing `import re` and `import json` in `openai_provider.py` caused `NameError` in `_parse_cluster_response`; (3) Truncation (`max_articles_per_digest`) was applied BEFORE `_summarize_clusters`, causing `cluster_map` (containing ALL articles) to be summarized while `ranked` only contained truncated subset — restructured so cluster summarization runs before truncation, with post-truncation filtering of cluster_digests; (4) Non-Hot-News cluster members were marked `_independent=True` and rendered in BOTH Hot News and Digests sections, causing duplication — removed `_independent` flag logic for cluster_digest mode, all articles in cluster_digest are in clusters so no independent articles exist. Affected: `openai_provider.py`, `ollama_provider.py`, `openrouter_provider.py`, `orchestrator.py`.

- **Cluster Digest**: New `cluster_digest` config section with `enabled`, `min_cluster_size`, `min_sources`, `max_hot_news_count`, `max_digest_count`. When enabled, pipeline groups articles by title similarity, skips per-article LLM summaries, and produces a single aggregated summary per cluster. Output format: "Hot News" (multi-source covered stories with aggregated summary) + "Digests" (independent articles, title + link only). Affected: `config.py`, `orchestrator.py`, `format.py`, all provider files (`openai_provider.py`, `ollama_provider.py`, `openrouter_provider.py`, `base.py`).
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
