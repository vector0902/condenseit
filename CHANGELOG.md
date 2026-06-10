# Changelog

## Unreleased

- **Debug logging via env vars**: `cli.py` now reads `UVICORN_LOG_LEVEL` (default `"info"`) instead of hardcoding `"info"`; `app.py` reads `CONDENSEIT_LOG_LEVEL` (default `"INFO"`) to control the condenseit logger level. Set both to `DEBUG` in `.env` to enable debug output.
- Admin: OPML import/export, HTMX-enhanced sources table, per-source health after collects.
- Admin: Ollama pull/delete from LLM settings (host from config).
- Preferences: TF-IDF style cosine boost from ratings (`relevance.tfidf_preference_weight`).
- OpenRouter: optional cheapest-model picker (`llm.openrouter_pick_cheapest`).
- Digest pipeline: weekly model advisor snapshot stored in settings (at most every 7 days).
- Docs: `docs/` guides, `launchd/` example plist, `scripts/export-config.sh`.
- Repository: MIT `LICENSE`, `CONTRIBUTING.md`, `SECURITY.md`.
