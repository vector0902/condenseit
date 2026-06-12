"""Info-reduction digest markdown: Keywords -> Hot News -> Digests."""

from datetime import UTC, datetime
from typing import Any


def build_digest_markdown(
    categorized: dict[str, list[dict[str, Any]]],
    changes: list[dict[str, str]] | None = None,
    videos: list[dict[str, Any]] | None = None,
    coverage_config: dict | None = None,
) -> str:
    cfg = coverage_config or {}
    stamp = datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC")
    lines: list[str] = [
        "# CondenseIt Digest",
        "",
        f"_{stamp}_",
        "",
    ]

    overview = (cfg.get("overview") or "").strip()
    if overview:
        lines.append(overview)
        lines.append("")

    user_kw, llm_index = _build_keywords_index(
        categorized,
        user_keywords=cfg.get("initial_keywords"),
    )
    if user_kw or llm_index:
        lines.append("## Keywords")
        lines.append("")
        # User keywords in configured order first
        for kw, items in user_kw:
            count = f" ({len(items)} articles)" if len(items) > 1 else ""
            lines.append(f"### {kw}{count}")
            for item in items:
                title = (item.get("title") or "Untitled").strip()
                url = (item.get("url") or "").strip()
                source = (item.get("source") or "").strip()
                link = f"[{title}]({url})" if url else title
                src_str = f" (from {source})" if source else ""
                lines.append(f"- {link}{src_str}")
            lines.append("")
        # LLM-extracted topics in alphabetical order
        for kw, items in sorted(llm_index.items()):
            count = f" ({len(items)} articles)" if len(items) > 1 else ""
            lines.append(f"### {kw}{count}")
            for item in items:
                title = (item.get("title") or "Untitled").strip()
                url = (item.get("url") or "").strip()
                source = (item.get("source") or "").strip()
                link = f"[{title}]({url})" if url else title
                src_str = f" (from {source})" if source else ""
                lines.append(f"- {link}{src_str}")
            lines.append("")

    hot_items = _filter_hot_news(categorized, cfg)
    if hot_items:
        lines.append("## Hot News")
        lines.append("")
        for cat, items in hot_items.items():
            lines.append(f"### {cat}")
            for item in items:
                _add_hot_item(lines, item, cfg)
            lines.append("")

    lines.append("## Digests")
    lines.append("")
    for category in sorted(categorized.keys()):
        items = categorized[category]
        if not items:
            continue
        lines.append(f"### {category}")
        lines.append("")
        for item in items:
            lines.extend(_format_item(item, cfg))
        lines.append("")

    if videos:
        lines.append("### Videos")
        lines.append("")
        for item in videos:
            lines.extend(_format_item(item, cfg))
        lines.append("")

    if changes:
        lines.append("## Website changes")
        lines.append("")
        for change in changes:
            url = change.get("url", "")
            status = change.get("status", "updated")
            lines.append(f"- **[{status}]({url})** -- {url}")
        lines.append("")

    if len(lines) <= 4:
        lines.append("_No new items in this run._")

    return "\n".join(lines).strip() + "\n"


# ---- Keyword index --------------------------------------------------------


def _build_keywords_index(
    categorized: dict[str, list[dict[str, Any]]],
    user_keywords: dict[str, list[str]] | None = None,
) -> tuple[list[tuple[str, list[dict[str, Any]]]], dict[str, list[dict[str, Any]]]]:
    """Build keyword index with user keywords first, then LLM topics.
    
    Returns (user_keyword_list, llm_topic_dict) where:
    - user_keyword_list preserves the configured order with matched articles
    - llm_topic_dict maps extracted topics to articles (sorted alphabetically later)
    """
    articles = [a for cat in categorized.values() for a in cat]

    user_kw: list[tuple[str, list[dict[str, Any]]]] = []
    if user_keywords:
        ordered_keys = user_keywords.get("high", []) + user_keywords.get("medium", [])
        seen_titles: set[tuple[str, str]] = set()
        for kw in ordered_keys:
            kw_lower = kw.strip().lower()
            if not kw_lower:
                continue
            matched: list[dict[str, Any]] = []
            for a in articles:
                title = (a.get("title") or "").strip()
                if (kw_lower, title) in seen_titles:
                    continue
                topics = [t.lower() for t in (a.get("topics") or [])]
                title_lower = title.lower()
                if any(kw_lower in t for t in topics) or kw_lower in title_lower:
                    matched.append(a)
                    seen_titles.add((kw_lower, title))
            if matched:
                user_kw.append((kw.strip(), matched))

    # Build LLM topic index (exclude keys already matched by user keywords)
    user_kw_keys = set(k.lower() for k, _ in user_kw)
    llm_index: dict[str, list[dict[str, Any]]] = {}
    for a in articles:
        for topic in (a.get("topics") or []):
            t = str(topic).strip()
            if len(t) < 2 or t.lower() in user_kw_keys:
                continue
            if t not in llm_index:
                llm_index[t] = []
            if a not in llm_index[t]:
                llm_index[t].append(a)

    return user_kw, llm_index


# ---- Hot News section -----------------------------------------------------


def _filter_hot_news(
    categorized: dict[str, list[dict[str, Any]]],
    cfg: dict,
) -> dict[str, list[dict[str, Any]]]:
    """Filter articles by coverage percentile and return as category->items map.

    Items are sorted by coverage (descending) within each category.
    """
    min_pct = cfg.get("hot_news_min_percentile", 90.0)
    top_n = cfg.get("hot_news_top_n", 15)

    candidates: list[tuple[str, dict[str, Any]]] = []
    for cat, items in categorized.items():
        for item in items:
            meta = item.get("coverage_meta", {})
            pct = meta.get("coverage_percentile", 0)
            if pct >= min_pct:
                candidates.append((cat, item))

    candidates.sort(
        key=lambda x: (
            -x[1].get("coverage_meta", {}).get("num_sources", 0),
            -x[1].get("coverage_meta", {}).get("coverage_percentile", 0),
        ),
    )

    result: dict[str, list[dict[str, Any]]] = {}
    for cat, item in candidates[:top_n]:
        result.setdefault(cat, []).append(item)
    return result


def _add_hot_item(
    lines: list[str],
    item: dict[str, Any],
    cfg: dict,
) -> None:
    show = cfg.get("show_in_digest", True)
    title = (item.get("title") or "Untitled").strip()
    url = (item.get("url") or "").strip()
    meta = item.get("coverage_meta", {})
    n = meta.get("num_merged", 1)
    src_count = meta.get("num_sources", 1)
    sources = meta.get("sources", [])
    tldr = (item.get("tldr") or "").strip()

    link = f"[{title}]({url})" if url else title
    coverage_tag = f" ({n} occurrences, {src_count} sources)" if show and n > 1 else ""
    sources_str = f" -- via {', '.join(sources[:4])}" if show and sources else ""

    bullet = f"- **{link}**{coverage_tag}{sources_str}"
    lines.append(bullet)
    if tldr:
        lines.append(f"  {tldr}")
    lines.append("")


# ---- Per-item formatting --------------------------------------------------


def _format_item(
    item: dict[str, Any],
    cfg: dict | None = None,
) -> list[str]:
    title = (item.get("title") or "Untitled").strip()
    url = (item.get("url") or "").strip()
    tldr = (item.get("tldr") or "").strip()
    summary = (item.get("summary") or "").strip()
    source = (item.get("source") or "").strip()
    meta = item.get("coverage_meta", {})
    n = meta.get("num_merged", 1)
    show = (cfg or {}).get("show_in_digest", True)

    link = f"[{title}]({url})" if url else title
    cov_str = f" ({n} occurrences)" if show and n > 1 else ""

    out: list[str] = []
    desc = ""
    if tldr:
        desc = f" -- {tldr}"
    out.append(f"- **{link}**{cov_str}{desc}")
    if source:
        out.append(f"  _via {source}_")
    if summary:
        out.append(f"  {summary}")
    return out
