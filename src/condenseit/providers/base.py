"""LLM provider abstraction."""

import json
import logging
import re
from abc import ABC, abstractmethod
from typing import Any, TypedDict

logger = logging.getLogger(__name__)


# Map of ISO 639-1 codes (and common langdetect outputs) to human-readable
# language names suitable for embedding in LLM prompts.
_LANG_NAMES: dict[str, str] = {
    "af": "Afrikaans",
    "ar": "Arabic",
    "bg": "Bulgarian",
    "bn": "Bengali",
    "ca": "Catalan",
    "cs": "Czech",
    "cy": "Welsh",
    "da": "Danish",
    "de": "German",
    "el": "Greek",
    "en": "English",
    "es": "Spanish",
    "et": "Estonian",
    "fa": "Persian",
    "fi": "Finnish",
    "fr": "French",
    "gu": "Gujarati",
    "he": "Hebrew",
    "hi": "Hindi",
    "hr": "Croatian",
    "hu": "Hungarian",
    "hy": "Armenian",
    "id": "Indonesian",
    "it": "Italian",
    "ja": "Japanese",
    "ka": "Georgian",
    "kn": "Kannada",
    "ko": "Korean",
    "lt": "Lithuanian",
    "lv": "Latvian",
    "mk": "Macedonian",
    "ml": "Malayalam",
    "mr": "Marathi",
    "nl": "Dutch",
    "no": "Norwegian",
    "pl": "Polish",
    "pt": "Portuguese",
    "ro": "Romanian",
    "ru": "Russian",
    "sk": "Slovak",
    "sl": "Slovenian",
    "sq": "Albanian",
    "sr": "Serbian",
    "sv": "Swedish",
    "sw": "Swahili",
    "ta": "Tamil",
    "te": "Telugu",
    "th": "Thai",
    "tl": "Filipino",
    "tr": "Turkish",
    "uk": "Ukrainian",
    "ur": "Urdu",
    "vi": "Vietnamese",
    "zh": "Chinese",
    "zh-cn": "Chinese",
    "zh-tw": "Chinese",
}


def _lang_code_to_name(code: str) -> str:
    """Map an ISO 639-1 language code to a human-readable name for LLM prompts."""
    code = code.lower().strip()
    if code in _LANG_NAMES:
        return _LANG_NAMES[code]
    # Unknown code: capitalise and return as-is (e.g. "Eo" for Esperanto).
    return code.capitalize()


def resolve_digest_language(digest_language: str, content: str = "") -> str:
    """Resolve a digest_language config value to a human-readable language name.

    - ``"en"`` (default) → ``"English"``
    - ``"source"`` → auto-detect from ``content`` via langdetect; falls back to
      ``"English"`` if detection fails or content is empty
    - Any other ISO 639-1 code (e.g. ``"fr"``) → mapped name (``"French"``)
    """
    code = digest_language.strip().lower()
    if not code or code == "en":
        return "English"
    if code == "source":
        if not content:
            return "English"
        try:
            from langdetect import detect

            detected = detect(content[:1000])
            return _lang_code_to_name(detected)
        except Exception:
            return "English"
    return _lang_code_to_name(code)


class ArticleSummary(TypedDict):
    """Structured output from a single article summarization call."""

    tldr: str
    key_takeaways: list[str]
    summary: str
    topics: list[str]
    entities: list[str]
    novelty: int
    relevance_to_you: str


class DigestOverview(TypedDict):
    """Output from the final aggregation call."""

    overview: str
    """Overall summary of all articles today."""
    topic_groups: dict[str, list[int]]
    """Keyword -> list of article indices belonging to that topic."""
    hot_news: list[int]
    """Article indices that are hot / covered by multiple sources."""
    priority_order: list[int]
    """Article indices in suggested reading order."""


_EMPTY_SUMMARY = ArticleSummary(
    tldr="",
    key_takeaways=[],
    summary="",
    topics=[],
    entities=[],
    novelty=0,
    relevance_to_you="",
)

# Matches an optional ```json ... ``` or ``` ... ``` fence around JSON.
_FENCE_RE = re.compile(
    r"```(?:json)?\s*(\{.*?\})\s*```",
    re.DOTALL | re.IGNORECASE,
)

# Greedily matches the outermost {...} object in a raw response.
_BRACE_RE = re.compile(r"\{.*\}", re.DOTALL)

# Strips an opening code fence (e.g. ```json\n or ```\n) so we can work on
# the raw JSON content even when the closing fence was never emitted.
_FENCE_OPEN_RE = re.compile(r"^```(?:json)?\s*", re.IGNORECASE)

# Detects the start of a Chinese LLM refusal phrase that some multilingual
# models append mid-response (e.g. "作为一个人工智能语言模型...").
# We strip from the first run of consecutive CJK characters onward when that
# run comprises the majority of the remaining text, so we don't accidentally
# truncate article titles that legitimately contain a single CJK character.
_CJK_BLOCK_RE = re.compile(r"[\u4e00-\u9fff\u3040-\u30ff\uac00-\ud7af]{4,}")

# Regex patterns for partial-field extraction from truncated JSON.
# These only match *complete* string values (closed quote, then comma/newline).
_PARTIAL_STR_FIELD_RE = {
    field: re.compile(
        r'"' + re.escape(field) + r'"\s*:\s*"((?:[^"\\]|\\.)*)"',
        re.DOTALL,
    )
    for field in ("tldr", "summary", "relevance_to_you")
}
# key_takeaways: match a fully-closed JSON array value.
_PARTIAL_ARRAY_FIELD_RE = {
    field: re.compile(
        r'"' + re.escape(field) + r'"\s*:\s*(\[[^\[\]]*\])',
        re.DOTALL,
    )
    for field in ("key_takeaways", "topics", "entities")
}
_PARTIAL_INT_FIELD_RE = re.compile(r'"novelty"\s*:\s*(\d+)')


def _strip_non_latin_tail(value: str) -> str:

    # this logic breaks feeds in CJK, so disable it.
    if True:
        return value

    """Remove a trailing CJK/non-Latin injection appended by the LLM.

    Some cheap multilingual models start answering in English, then switch
    to a Chinese refusal phrase mid-field.  This function finds a CJK run
    in the trailing portion of the text that makes up more than 30% of the
    remaining tail and truncates there, returning a clean Latin-script prefix.

    A CJK block that appears before the last 30 % of the string is assumed
    to be the legitimate content (e.g. when the digest language is Chinese)
    and is left untouched.
    """
    threshold = len(value) * 0.7
    for m in _CJK_BLOCK_RE.finditer(value):
        if m.start() < threshold:
            continue
        tail = value[m.start() :]
        non_ascii_in_tail = sum(1 for c in tail if ord(c) > 127)
        if len(tail) > 0 and non_ascii_in_tail / len(tail) > 0.3:
            return value[: m.start()].rstrip()
    return value


def _extract_partial_fields(text: str) -> ArticleSummary | None:
    """Try to extract individual fields from a truncated JSON string.

    When the LLM response is cut off mid-value (max_tokens hit), the JSON
    object is invalid as a whole, but earlier fields that were fully written
    can still be rescued with targeted regex extraction.

    Returns an :class:`ArticleSummary` if at least ``tldr`` was found,
    otherwise returns ``None`` so the caller can keep trying other strategies.
    """
    # Strip opening code fence if present.
    body = _FENCE_OPEN_RE.sub("", text).strip()
    # Only attempt on text that looks like it started as a JSON object.
    if not body.startswith("{"):
        return None

    result: dict[str, Any] = {}

    for field, pat in _PARTIAL_STR_FIELD_RE.items():
        m = pat.search(body)
        if m:
            try:
                # json.loads the quoted value to handle escape sequences.
                result[field] = json.loads('"' + m.group(1) + '"')
            except (json.JSONDecodeError, ValueError):
                result[field] = m.group(1)

    for field, pat in _PARTIAL_ARRAY_FIELD_RE.items():
        m = pat.search(body)
        if m:
            try:
                result[field] = json.loads(m.group(1))
            except (json.JSONDecodeError, ValueError):
                logger.debug("Could not parse partial array field %s", field)

    m_nov = _PARTIAL_INT_FIELD_RE.search(body)
    if m_nov:
        try:
            result["novelty"] = max(1, min(5, int(m_nov.group(1))))
        except (TypeError, ValueError):
            logger.debug("Could not parse novelty score from partial JSON")

    # Require at least tldr to have been found; otherwise not useful.
    if not result.get("tldr"):
        return None

    takeaways = result.get("key_takeaways", [])
    if isinstance(takeaways, str):
        takeaways = [t.strip() for t in takeaways.splitlines() if t.strip()]
    elif not isinstance(takeaways, list):
        takeaways = []

    raw_topics = result.get("topics", [])
    topics = (
        [str(t).lower().strip() for t in raw_topics if t]
        if isinstance(raw_topics, list)
        else []
    )
    raw_entities = result.get("entities", [])
    entities = (
        [str(e).strip() for e in raw_entities if e]
        if isinstance(raw_entities, list)
        else []
    )

    return ArticleSummary(
        tldr=_strip_non_latin_tail(str(result.get("tldr", "") or "").strip()),
        key_takeaways=[_strip_non_latin_tail(str(t)) for t in takeaways if t],
        summary=_strip_non_latin_tail(str(result.get("summary", "") or "").strip()),
        topics=topics,
        entities=entities[:10],
        novelty=result.get("novelty") or 0,
        relevance_to_you=_strip_non_latin_tail(
            str(result.get("relevance_to_you", "") or "").strip()
        ),
    )


def _looks_like_json(text: str) -> bool:
    """Return True if text looks like raw JSON (starts with { or a code fence)."""
    stripped = _FENCE_OPEN_RE.sub("", text.strip()).strip()
    return stripped.startswith("{")


def parse_summary_response(raw: str) -> ArticleSummary:
    """Parse a JSON article-summary response produced by an LLM.

    Attempts several strategies in order:
      1. Strip whitespace and parse as bare JSON.
      2. Extract JSON from a markdown code fence (complete fence).
      3. Grab the first ``{...}`` substring and parse it.
      4. Partial-field extraction from a truncated JSON response.
      5. Fall back: treat the whole response as the ``summary`` field,
         but only if it doesn't look like raw JSON (refuse to store garbage).

    Always returns a fully-populated :class:`ArticleSummary` dict.
    """
    text = (raw or "").strip()

    candidates: list[str] = [
        text,
        text.rstrip(",") + "}",
        text + "}",
    ]
    # Code-fence extraction (only fires when the closing fence was emitted)
    m = _FENCE_RE.search(text)
    if m:
        chunk = m.group(1).strip()
        candidates = [chunk, chunk.rstrip(",") + "}", chunk + "}"] + candidates
    # Raw brace extraction (broader, try last)
    m2 = _BRACE_RE.search(text)
    if m2:
        chunk2 = m2.group(0)
        candidates += [chunk2, chunk2.rstrip(",") + "}", chunk2 + "}"]

    for candidate in candidates:
        try:
            data = json.loads(candidate)
            if not isinstance(data, dict):
                continue
            return _parse_single_summary_dict(data)
        except (json.JSONDecodeError, ValueError):
            continue

    # Partial-field recovery for truncated responses (max_tokens hit).
    partial = _extract_partial_fields(text)
    if partial is not None:
        logger.debug(
            "parse_summary_response: recovered partial fields from truncated JSON"
        )
        return partial

    if text:
        non_ascii = sum(1 for c in text if ord(c) > 127)
        if non_ascii / len(text) > 0.2:
            return _EMPTY_SUMMARY

        if _looks_like_json(text):
            logger.warning(
                "parse_summary_response: response looks like raw/truncated JSON "
                "but could not be parsed; discarding to avoid storing garbage"
            )
            return _EMPTY_SUMMARY

    return ArticleSummary(
        tldr="",
        key_takeaways=[],
        summary=text,
        topics=[],
        entities=[],
        novelty=0,
        relevance_to_you="",
    )


def _parse_single_summary_dict(data: dict[str, Any]) -> ArticleSummary:
    """Convert a parsed JSON dict into an ArticleSummary."""
    takeaways = data.get("key_takeaways", [])
    if isinstance(takeaways, str):
        takeaways = [t.strip() for t in takeaways.splitlines() if t.strip()]
    elif not isinstance(takeaways, list):
        takeaways = []
    raw_topics = data.get("topics", [])
    topics = (
        [str(t).lower().strip() for t in raw_topics if t]
        if isinstance(raw_topics, list)
        else []
    )
    raw_entities = data.get("entities", [])
    entities = (
        [str(e).strip() for e in raw_entities if e]
        if isinstance(raw_entities, list)
        else []
    )
    try:
        novelty = max(1, min(5, int(data.get("novelty", 0) or 0)))
    except (TypeError, ValueError):
        novelty = 0
    return ArticleSummary(
        tldr=_strip_non_latin_tail(str(data.get("tldr", "") or "").strip()),
        key_takeaways=[_strip_non_latin_tail(str(t)) for t in takeaways if t],
        summary=_strip_non_latin_tail(str(data.get("summary", "") or "").strip()),
        topics=topics,
        entities=entities[:10],
        novelty=novelty,
        relevance_to_you=_strip_non_latin_tail(
            str(data.get("relevance_to_you", "") or "").strip()
        ),
    )


def build_batch_summarize_prompt(
    articles: list[dict[str, Any]],
    max_key_takeaways: int = 3,
    max_summary_paragraphs: int = 2,
    language: str = "English",
) -> str:
    """Build a batch summarization prompt for multiple articles.

    Returns a prompt that asks the LLM to produce a JSON array of article
    summaries, one per article in the same order.
    """
    takeaway_placeholders = ", ".join(
        f'"<takeaway {i + 1}>"' for i in range(max_key_takeaways)
    )
    para_word = "paragraph" if max_summary_paragraphs == 1 else "paragraphs"

    struct_lines = [
        "{",
        f'  "tldr": "<one sentence in {language}: what happened and why it matters>",',
        f'  "key_takeaways": [{takeaway_placeholders}],',
        f'  "summary": "<brief summary in {language}, {max_summary_paragraphs} {para_word}>",',
        '  "topics": ["<topic-1>", "<topic-2>", "<topic-3>"],',
        '  "entities": ["<person-org-product-1>", "<entity-2>"],',
        '  "novelty": <integer 1-5, how surprising vs mainstream coverage>',
        "}",
    ]

    lines = [
        f"You are a concise news analyst. Below are {len(articles)} articles.",
        f"For each article, provide a JSON object with its analysis.",
        f"Respond ONLY with a JSON array of {len(articles)} objects, one per article,",
        f"in the SAME ORDER as listed below. No markdown, no code fences, no extra text.",
        f"Write all JSON field values in {language} regardless of the article's language.",
        "",
        "Each object must use this exact structure:",
        *struct_lines,
        "",
    ]
    for i, article in enumerate(articles, 1):
        title = article.get("title", "Untitled")
        content = (article.get("content") or article.get("description") or "")[:2000]
        lines.extend([f"Article {i}:", f"Title: {title}", f"Content: {content}", ""])

    return "\n".join(lines)


def parse_batch_summarize_response(
    raw: str, expected_count: int
) -> list[ArticleSummary]:
    """Parse a JSON array response from batch summarization.

    Falls back gracefully: if the array is shorter than expected, pads with
    empty summaries; if the array is longer, truncates.
    """
    text = (raw or "").strip()

    candidates: list[str] = [text]
    # Try extracting from code fence
    m = re.search(r"```(?:json)?\s*(\[.*?\])\s*```", text, re.DOTALL | re.IGNORECASE)
    if m:
        candidates.insert(0, m.group(1).strip())

    for candidate in candidates:
        try:
            data = json.loads(candidate)
            if isinstance(data, list):
                results = []
                for item in data:
                    if isinstance(item, dict):
                        results.append(_parse_single_summary_dict(item))
                    else:
                        results.append(ArticleSummary(
                            tldr="", key_takeaways=[], summary="",
                            topics=[], entities=[], novelty=0, relevance_to_you="",
                        ))
                while len(results) < expected_count:
                    results.append(ArticleSummary(
                        tldr="", key_takeaways=[], summary="",
                        topics=[], entities=[], novelty=0, relevance_to_you="",
                    ))
                return results[:expected_count]
        except (json.JSONDecodeError, ValueError):
            continue

    # Fallback: try to find individual JSON objects in the text
    brace_matches = list(re.finditer(r"\{(?:[^{}]|(?:\{[^{}]*\}))*\}", text, re.DOTALL))
    results = []
    for m in brace_matches:
        try:
            item = json.loads(m.group(0))
            if isinstance(item, dict) and item.get("tldr"):
                results.append(_parse_single_summary_dict(item))
                if len(results) >= expected_count:
                    break
        except (json.JSONDecodeError, ValueError):
            continue

    while len(results) < expected_count:
        results.append(ArticleSummary(
            tldr="", key_takeaways=[], summary="",
            topics=[], entities=[], novelty=0, relevance_to_you="",
        ))
    return results[:expected_count]


def build_aggregate_digest_prompt(
    entries: list[dict[str, Any]],
    initial_keywords: dict[str, list[str]] | None = None,
    language: str = "English",
) -> tuple[str, str]:
    """Build aggregate digest prompt.

    Returns (user_prompt, system_prompt).  The final LLM call takes all
    article summaries and produces a structured overview.
    """
    sys_prompt = (
        "You are a senior news editor creating a daily digest. "
        "Respond ONLY with a JSON object. No markdown, no code fences."
    )

    kw_hints = ""
    if initial_keywords:
        high = initial_keywords.get("high", [])
        medium = initial_keywords.get("medium", [])
        if high:
            kw_hints += f"\nHigh-priority keywords (must use): {', '.join(high)}"
        if medium:
            kw_hints += f"\nMedium-priority keywords (use if relevant): {', '.join(medium)}"

    article_lines = []
    for idx, entry in enumerate(entries):
        title = (entry.get("title") or "").strip()
        source = (entry.get("source") or "").strip()
        category = (entry.get("category") or "General").strip()
        tldr = (entry.get("tldr") or "").strip()
        topics = (entry.get("topics") or [])
        topics_str = ", ".join(str(t) for t in topics) if topics else "(none)"
        article_lines.append(
            f"[{idx}] Category: {category} | Source: {source}\n"
            f"    Title: {title}\n"
            f"    TLDR: {tldr}\n"
            f"    Topics: {topics_str}"
        )

    user_prompt = (
        f"Below are {len(entries)} articles collected today, each with its "
        f"TLDR summary and topics. Your job: produce a final digest.\n"
        f"1. Write an overall {language} overview paragraph (\"today's digest\").\n"
        f"2. Group articles into topical keyword sections (use Initial Keywords when applicable).\n"
        f"3. Identify hot news articles (stories covered across multiple sources).\n"
        f"4. Suggest a priority reading order.\n"
        f"{kw_hints}\n\n"
        f"Respond with this JSON structure:\n"
        f"{{\n"
        f'  "overview": "<3-5 sentence overall summary of today in {language}>",\n'
        f'  "topic_groups": {{"keyword1": [article_indices], "keyword2": [...]}},\n'
        f'  "hot_news": [article_indices of hot stories],\n'
        f'  "priority_order": [all article indices in suggested order]\n'
        f"}}\n\n"
        f"Articles:\n"
        + "\n".join(article_lines)
    )

    return user_prompt, sys_prompt


def parse_aggregate_digest_response(raw: str) -> DigestOverview | None:
    """Parse the aggregate digest JSON response."""
    text = (raw or "").strip()
    candidates: list[str] = [text]
    m = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL | re.IGNORECASE)
    if m:
        candidates.insert(0, m.group(1).strip())
    m2 = re.compile(r"\{.*\}", re.DOTALL).search(text)
    if m2:
        candidates.append(m2.group(0))

    for candidate in candidates:
        try:
            data = json.loads(candidate)
            if not isinstance(data, dict):
                continue
            return DigestOverview(
                overview=str(data.get("overview", "") or ""),
                topic_groups={
                    str(k): [int(i) for i in v if isinstance(i, (int, float))]
                    for k, v in (data.get("topic_groups") or {}).items()
                    if isinstance(v, list)
                },
                hot_news=[int(i) for i in (data.get("hot_news") or []) if isinstance(i, (int, float))],
                priority_order=[int(i) for i in (data.get("priority_order") or []) if isinstance(i, (int, float))],
            )
        except (json.JSONDecodeError, ValueError, TypeError):
            continue
    return None


def build_chat_system_prompt(language: str = "English") -> str:
    """Return the system prompt for chat-completions providers.

    ``language`` is a human-readable language name such as ``"English"`` or
    ``"French"``.  All JSON field values in the response will be written in
    that language.
    """
    return (
        "You are a concise news analyst. Respond ONLY with a JSON object — "
        "no markdown, no code fences, no additional text. "
        f"Write all JSON field values in {language} "
        "regardless of the article's language."
    )


# Backward-compatible alias for the default English system prompt.
CHAT_SYSTEM_PROMPT = build_chat_system_prompt("English")


def build_chat_user_prompt(
    title: str,
    content: str,
    max_key_takeaways: int = 5,
    max_summary_paragraphs: int = 5,
    language: str = "English",
) -> str:
    """Build the per-article user prompt for chat-completions providers.

    ``language`` is a human-readable language name such as ``"English"`` or
    ``"French"``.
    """
    takeaway_placeholders = ", ".join(
        f'"<takeaway {i + 1}>"' for i in range(max_key_takeaways)
    )
    para_word = "paragraph" if max_summary_paragraphs == 1 else "paragraphs"

    return (
        "Analyze this article and respond with a JSON object "
        f"in exactly this structure. All values must be written in {language}:\n"
        f"{{\n"
        f'  "tldr": "<one sentence in {language}: what happened and why it matters>",\n'
        f'  "key_takeaways": [{takeaway_placeholders}],\n'
        f'  "summary": "<detailed summary in {language}, {max_summary_paragraphs} {para_word}>",\n'  # noqa: E501
        f'  "topics": ["<topic-1>", "<topic-2>", "<topic-3>"],\n'
        f'  "entities": ["<person-org-product-1>", "<entity-2>"],\n'
        f'  "novelty": <integer 1-5: how surprising or novel vs mainstream coverage>\n'
        f"}}\n\n"
        f"Title: {title}\n"
        f"Content: {content}"
    )


class SummarizerProvider(ABC):
    @abstractmethod
    def summarize_article(
        self,
        article: dict[str, Any],
    ) -> ArticleSummary:
        """Summarize ``article`` and return a structured result."""
        ...

    def batch_summarize(
        self,
        articles: list[dict[str, Any]],
    ) -> list[ArticleSummary]:
        """Summarize multiple articles in a single LLM call.

        Default implementation falls back to per-article calls.
        Subclasses should override with a batched prompt for efficiency.
        """
        return [self.summarize_article(a) for a in articles]

    def aggregate_digest(
        self,
        entries: list[dict[str, Any]],
        initial_keywords: dict[str, list[str]] | None = None,
        digest_language: str = "English",
    ) -> dict | None:
        """One LLM call to produce an overall digest overview.

        Takes all per-article summaries and produces a structured result
        with overall summary, topic groups, hot news, and priority order.
        Returns None if aggregation is not supported (pipeline falls back
        to existing format.py logic).
        """
        return None

    @abstractmethod
    def generate_digest(
        self,
        categorized: dict[str, list[dict[str, Any]]],
        changes: list[dict[str, str]] | None = None,
        videos: list[dict[str, Any]] | None = None,
        coverage_config: dict | None = None,
    ) -> str: ...

    @property
    def model_name(self) -> str:
        return "unknown"
