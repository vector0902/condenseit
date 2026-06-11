"""Shared utilities for CondenseIt providers."""

import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)

# Global singleton for LLM conversation logger
_llm_logger_instance = None
_llm_log_dir_path = None


def get_llm_conversation_logger():
    """Ensure a dedicated logger for LLM conversations exists.

    Log file is created at <CONDENSEIT_DATA_DIR>/llm_conversations.log.
    Only the first call creates the logger; subsequent calls return the same instance.
    """
    global _llm_logger_instance, _llm_log_dir_path

    if _llm_logger_instance is not None:
        return _llm_logger_instance

    data_dir = Path(os.environ.get("CONDENSEIT_DATA_DIR", "data"))
    _llm_log_dir_path = data_dir / "llm_conversations.log"

    _llm_logger_instance = logging.getLogger(f"{__name__}.llm")
    _llm_logger_instance.setLevel(logging.INFO)

    if not _llm_logger_instance.handlers:
        handler = logging.FileHandler(_llm_log_dir_path, encoding="utf-8")
        formatter = logging.Formatter("%(asctime)s [LLM] %(message)s", datefmt="%Y-%m-%d %H:%M:%S")
        handler.setFormatter(formatter)
        _llm_logger_instance.addHandler(handler)

    return _llm_logger_instance


def log_llm_message(conversation_id: str, role: str, content: str):
    """Log a single message (prompt or response) in the LLM conversation.

    Args:
        conversation_id: Identifier for this article's conversation (e.g. title + content length).
        role: "PROMPT" or "RESPONSE".
        content: Full text of the message. Truncated to 2000 chars in log output.
    """
    llm_log = get_llm_conversation_logger()
    preview = content[:2000] + ("\n...(truncated)" if len(content) > 2000 else "")
    llm_log.info("[%s] %s:\n%s", conversation_id, role.upper(), preview)
