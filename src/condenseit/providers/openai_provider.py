"""OpenAI-compatible endpoint provider (v1/chat/completions)."""

import logging
import time
from typing import Any

import httpx
import httpcore

from condenseit.digest.format import build_digest_markdown
from condenseit.providers.base import (
    ArticleSummary,
    DigestOverview,
    SummarizerProvider,
    build_aggregate_digest_prompt,
    build_batch_summarize_prompt,
    build_chat_system_prompt,
    build_chat_user_prompt,
    parse_aggregate_digest_response,
    parse_batch_summarize_response,
    parse_summary_response,
    resolve_digest_language,
)
from condenseit.providers.shared_utils import log_llm_message

logger = logging.getLogger(__name__)

_RETRY_WAITS = [5, 15, 30]
_TIMEOUT_RETRIES = 2


class OpenAISummarizer(SummarizerProvider):
    """Summarizer that calls any OpenAI-compatible /v1/chat/completions endpoint.

    Works with Ollama's OpenAI compat layer, LM Studio, vLLM, llama.cpp,
    text-generation-inference, and real OpenAI / Azure OpenAI endpoints.
    """

    def __init__(
        self,
        model: str,
        base_url: str,
        api_key: str = "",
        max_key_takeaways: int = 5,
        max_summary_paragraphs: int = 5,
        digest_language: str = "en",
        max_tokens: int = 4096,
    ) -> None:
        self.model = model
        # Normalise: strip trailing slash so we can always append /chat/completions.
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.max_key_takeaways = max_key_takeaways
        self.max_summary_paragraphs = max_summary_paragraphs
        self.digest_language = digest_language
        self.max_tokens = max_tokens

    @property
    def model_name(self) -> str:
        return self.model

    def _chat(
        self,
        messages: list[dict[str, str]],
        max_tokens: int = 4096,
    ) -> str:
        url = f"{self.base_url}/chat/completions"
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "temperature": 0.3,
            "max_tokens": max_tokens,
        }
        headers: dict[str, str] = {}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        # Log prompt for debugging
        conv_id = f"openai:{self.model}:{url}"
        for msg in messages:
            log_llm_message(conv_id, msg["role"], msg.get("content", ""))

        resp: httpx.Response | None = None
        with httpx.Client(timeout=120.0) as client:
            for attempt in range(len(_RETRY_WAITS) + 1):
                try:
                    resp = client.post(url, json=payload, headers=headers)
                    if resp.status_code != 429:
                        resp.raise_for_status()
                        break
                    if attempt >= len(_RETRY_WAITS):
                        resp.raise_for_status()
                    wait = int(resp.headers.get("Retry-After") or _RETRY_WAITS[attempt])
                    logger.warning(
                        "OpenAI-compat 429 rate limit; retrying in %ds (attempt %d/%d)",
                        wait,
                        attempt + 1,
                        len(_RETRY_WAITS),
                    )
                    time.sleep(wait)
                except (httpx.ReadTimeout, httpx.ConnectTimeout, httpcore.ReadTimeout, httpcore.ConnectTimeout) as exc:
                    if attempt < len(_RETRY_WAITS) + _TIMEOUT_RETRIES - 1:
                        wait = _RETRY_WAITS[min(attempt, len(_RETRY_WAITS) - 1)]
                        logger.warning(
                            "OpenAI-compat timeout (%s); retrying in %ds (attempt %d/%d)",
                            type(exc).__name__,
                            wait,
                            attempt + 1,
                            len(_RETRY_WAITS) + _TIMEOUT_RETRIES,
                        )
                        time.sleep(wait)
                        continue
                    raise

        data = resp.json()  # type: ignore[union-attr]
        choices = data.get("choices", [])
        if not choices:
            return ""
        choice = choices[0]
        raw_response = str(choice["message"]["content"]).strip()
        
        # Log response for debugging
        log_llm_message(conv_id, "RESPONSE", raw_response)
        
        if choice.get("finish_reason") == "length":
            logger.warning(
                "OpenAI-compat response truncated (finish_reason=length) for model=%s; "
                "consider raising max_tokens",
                self.model,
            )
        return raw_response

    def summarize_article(
        self,
        article: dict[str, Any],
    ) -> ArticleSummary:
        content = (article.get("content") or "")[:4000]
        title = article.get("title", "Untitled")
        language = resolve_digest_language(self.digest_language, content)
        messages = [
            {"role": "system", "content": build_chat_system_prompt(language)},
            {
                "role": "user",
                "content": build_chat_user_prompt(
                    title,
                    content,
                    self.max_key_takeaways,
                    self.max_summary_paragraphs,
                    language=language,
                ),
            },
        ]
        raw = self._chat(messages, max_tokens=self.max_tokens)
        return parse_summary_response(raw)

    def batch_summarize(
        self,
        articles: list[dict[str, Any]],
        max_tokens: int = 8192,
    ) -> list[ArticleSummary]:
        if not articles:
            return []
        sample_content = (articles[0].get("content") or articles[0].get("description") or "")
        language = resolve_digest_language(self.digest_language, sample_content)
        user_prompt = build_batch_summarize_prompt(
            articles,
            max_key_takeaways=min(3, self.max_key_takeaways),
            max_summary_paragraphs=min(2, self.max_summary_paragraphs),
            language=language,
        )
        messages = [
            {"role": "system", "content": build_chat_system_prompt(language)},
            {"role": "user", "content": user_prompt},
        ]
        raw = self._chat(messages, max_tokens=max_tokens)
        results = parse_batch_summarize_response(raw, len(articles))
        # Fallback: if too many results are empty, retry per-article
        filled = sum(1 for r in results if r.get("tldr"))
        if filled < len(articles) * 0.5:
            logger.warning(
                "batch_summarize: only %d/%d articles parsed; falling back to per-article",
                filled, len(articles),
            )
            return [self.summarize_article(a) for a in articles]
        return results

    def aggregate_digest(
        self,
        entries: list[dict[str, Any]],
        initial_keywords: dict[str, list[str]] | None = None,
        max_tokens: int = 4096,
        digest_language: str = "Chinese",
    ) -> dict | None:
        if not entries:
            return None
        user_prompt, sys_prompt = build_aggregate_digest_prompt(
            entries,
            initial_keywords=initial_keywords,
            language=digest_language,
        )
        messages = [
            {"role": "system", "content": sys_prompt},
            {"role": "user", "content": user_prompt},
        ]
        raw = self._chat(messages, max_tokens=max_tokens)
        parsed = parse_aggregate_digest_response(raw)
        return dict(parsed) if parsed else None

    def generate_digest(
        self,
        categorized: dict[str, list[dict[str, Any]]],
        changes: list[dict[str, str]] | None = None,
        videos: list[dict[str, Any]] | None = None,
        coverage_config: dict | None = None,
    ) -> str:
        return build_digest_markdown(categorized, changes, videos, coverage_config=coverage_config)
