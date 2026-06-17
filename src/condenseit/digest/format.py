"""Info-reduction digest markdown: Keywords -> Hot News -> Digests."""

from datetime import UTC, datetime
from typing import Any


# Synonym map: merge similar LLM topics into canonical keyword groups.
_KEYWORD_SYNONYMS: dict[str, str] = {
    "ai": "AI / 大模型",
    "llm": "AI / 大模型",
    "大模型": "AI / 大模型",
    "人工智能": "AI / 大模型",
    "ai agent": "AI Agent",
    "agent": "AI Agent",
    "ai智能体": "AI Agent",
    "ai 智能体": "AI Agent",
    "agent技术": "AI Agent",
    "agent评测": "AI Agent",
    "agent skill": "AI Agent",
    "ai agent 架构": "AI Agent",
    "ai agent 自动化": "AI Agent",
    "ai agent开发": "AI Agent",
    "多agent架构": "AI Agent",
    "多智能体": "AI Agent",
    "自进化机制": "AI Agent",
    "harness工程": "AI Agent",
    "ai native": "AI Native",
    "ai native 架构": "AI Native",
    "ai 编程": "AI 工具",
    "ai 自动化": "AI / 大模型",
    "ai 工程化": "AI / 大模型",
    "ai 辅助": "AI / 大模型",
    "ai 桌面": "AI 应用",
    "ai 绘画": "AI 创作",
    "comfyui": "AI 创作",
    "stable diffusion": "AI 创作",
    "节点工作流": "AI 创作",
    "openclaw": "AI 工具",
    "claude code": "AI 工具",
    "qwen": "AI / 大模型",
    "多模态": "AI / 大模型",
    "企业级ai": "AI / 大模型",
    "研发自动化": "AI / 大模型",
    "知识库管理": "AI / 大模型",
    "钉钉机器人": "AI 工具",
    "云原生": "云服务/部署",
    "云计算": "云服务/部署",
    "云服务": "云服务/部署",
    "云存储": "云服务/部署",
    "cloudflare": "云服务/部署",
    "serverless": "云服务/部署",
    "docker": "云服务/部署",
    "kubernetes": "云服务/部署",
    "缓存架构": "云服务/部署",
    "阿里云": "云服务/部署",
    "域名": "安全/网络",
    "数字版权": "安全/网络",
    "网络隐私": "安全/网络",
    "漏洞": "安全/网络",
    "cve": "安全/网络",
    "开源": "开源/社区",
    "github": "开源/社区",
    "独立开发": "开源/社区",
    "mac": "硬件/系统",
    "macos": "硬件/系统",
    "windows": "硬件/系统",
    "系统工具": "效率工具",
    "效率工具": "效率工具",
    "开发者工具": "效率工具",
    "命令行工具": "效率工具",
    "浏览器扩展": "效率工具",
    "软件更新": "效率工具",
    "软件工程": "技术综合",
    "低代码": "技术综合",
    "数据工程": "技术综合",
    "sdk 改造": "技术综合",
    "本地部署": "技术综合",
    "技术演进": "技术综合",
    "高德地图": "技术综合",
}


def _merge_keyword(kw: str) -> str:
    """Merge a topic keyword into its canonical group if a synonym exists."""
    lower = kw.lower().strip()
    return _KEYWORD_SYNONYMS.get(lower, kw)


def _keywords_from_topic_groups(
    topic_groups: dict[str, list[dict[str, Any]]],
) -> list[tuple[str, list[dict[str, Any]]]]:
    """Convert topic_groups dict to sorted list, merging similar groups."""
    merged: dict[str, list[dict[str, Any]]] = {}
    for kw, items in topic_groups.items():
        canonical = _merge_keyword(kw)
        seen_titles = set()
        for item in items:
            title = str(item.get("title", ""))
            if title and title not in seen_titles:
                seen_titles.add(title)
                merged.setdefault(canonical, []).append(item)
    # Sort by number of articles (descending), then alphabetically
    return sorted(
        merged.items(),
        key=lambda x: (-len(x[1]), x[0]),
    )


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

    topic_groups = cfg.get("topic_groups")
    if topic_groups:
        # Use LLM aggregate topic_groups as the primary keyword index.
        kw_groups = _keywords_from_topic_groups(topic_groups)
        user_kw, llm_index = [], {}
    else:
        kw_groups = None
        user_kw, llm_index = _build_keywords_index(
            categorized,
            user_keywords=cfg.get("initial_keywords"),
        )

    if kw_groups or user_kw or llm_index:
        lines.append("## Keywords")
        lines.append("")
        if kw_groups:
            for kw, items in kw_groups:
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
        else:
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
            # LLM-extracted topics, merged via synonym map
            merged_topics: dict[str, list[dict[str, Any]]] = {}
            for kw, items in sorted(llm_index.items()):
                canonical = _merge_keyword(kw)
                for item in items:
                    if item not in merged_topics.setdefault(canonical, []):
                        merged_topics[canonical].append(item)
            for kw, items in sorted(
                merged_topics.items(),
                key=lambda x: (-len(x[1]), x[0]),
            ):
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

    llm_hot = cfg.get("hot_news_entries")
    if llm_hot:
        hot_items = _group_by_domain(llm_hot)
    else:
        hot_items = _filter_hot_news(categorized, cfg)
    if hot_items:
        lines.append("## Hot News")
        lines.append("")
        for cat, items in hot_items.items():
            if not items:
                continue
            lines.append(f"### {cat}")
            for item in items:
                _add_hot_item(lines, item, cfg)
            lines.append("")

    lines.append("## Digests")
    lines.append("")
    grouped = _group_by_domain(_all_articles(categorized, videos)) if topic_groups else categorized
    for category in sorted(grouped.keys()):
        items = grouped[category]
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


# ---- Domain field mapping --------------------------------------------------


# Semantic domain definitions based on topic/content matching keywords.
# Each entry is (field_name, [matching_substrings]).
_DOMAIN_RULES: list[tuple[str, list[str]]] = [
    ("AI / \u5927\u6a21\u578b", ["ai", "llm", "\u5927\u6a21\u578b", "agent", "qwen", "claude", "openai", "gpt", "\u591a\u6a21\u6001", "\u81ea\u8fdb\u5316"]),
    ("AI Agent", ["ai agent", "ai\u667a\u80fd\u4f53", "\u591a\u667a\u80fd\u4f53", "harness", "skill\u81ea\u8fdb\u5316"]),
    ("AI \u5de5\u5177", ["openclaw", "claude code", "ai \u7f16\u7a0b", "ai \u5de5\u5177", "verify-data"]),
    ("AI \u521b\u4f5c", ["ai \u7ed8\u753b", "comfyui", "stable diffusion", "\u8282\u70b9\u5de5\u4f5c\u6d41"]),
    ("\u4e91\u670d\u52a1/\u90e8\u7f72", ["\u4e91", "cloudflare", "serverless", "docker", "kubernetes", "tair", "sglang", "\u90e8\u7f72", "\u7f13\u5b58"]),
    ("\u5f00\u6e90/\u793e\u533a", ["\u5f00\u6e90", "github", "\u72ec\u7acb\u5f00\u53d1", "z-library", "mit", "\u793e\u533a"]),
    ("\u5b89\u5168/\u7f51\u7edc", ["\u5b89\u5168", "cve", "\u6f0f\u6d1e", "\u57df\u540d", "\u9690\u79c1", "\u7248\u6743", "\u5c01\u9501"]),
    ("\u786c\u4ef6/\u7cfb\u7edf", ["mac", "windows", "linux", "\u7cfb\u7edf", "power toys"]),
    ("\u6548\u7387\u5de5\u5177", ["\u6548\u7387", "\u63d2\u4ef6", "\u6269\u5c55", "power toys", "rclone", "aria2"]),
    ("\u751f\u6d3b/\u6742\u8c08", ["\u53e6\u5916\u4e24\u4ef6\u4e8b", "\u4eb2\u5b50", "\u8db3\u7403", "\u4f53\u80b2", "\u65e5\u5e38"]),
    ("\u6280\u672f\u7efc\u5408", []),
]


def _assign_domain(
    item: dict[str, Any],
) -> str:
    """Assign a semantic domain field to an article based on its topics/title."""
    topics = [str(t).lower() for t in (item.get("topics") or [])]
    title = str(item.get("title") or "").lower()
    tldr = str(item.get("tldr") or "").lower()
    combined = title + " " + tldr + " " + " ".join(topics)
    for field, keywords in _DOMAIN_RULES:
        if not keywords:
            continue
        for kw in keywords:
            if kw in combined:
                return field
    return "\u6280\u672f\u7efc\u5408"


def _group_by_domain(
    entries: list[dict[str, Any]],
) -> dict[str, list[dict[str, Any]]]:
    """Group a flat list of entries by their semantic domain field."""
    grouped: dict[str, list[dict[str, Any]]] = {}
    for entry in entries:
        domain = _assign_domain(entry)
        grouped.setdefault(domain, []).append(entry)
    return grouped


def _all_articles(
    categorized: dict[str, list[dict[str, Any]]],
    videos: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    """Flatten categorized dict + videos into a single list."""
    articles = [a for cat_list in categorized.values() for a in cat_list]
    if videos:
        articles.extend(videos)
    return articles


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


def _sort_by_coverage(
    items: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Sort items by coverage (num_sources desc, num_merged desc)."""
    return sorted(
        items,
        key=lambda x: (
            -x.get("coverage_meta", {}).get("num_sources", 0),
            -x.get("coverage_meta", {}).get("num_merged", 0),
        ),
    )


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
    if show and n > 1:
        coverage_tag = f" **({n} occurrences, {src_count} sources)**"
    else:
        coverage_tag = ""
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
