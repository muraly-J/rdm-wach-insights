"""
llm/client_factory.py
─────────────────────
Returns the active LLM chat client (QwenClient via LM Studio).
"""

from llm.qwen_client import QwenClient


def get_chat_client() -> QwenClient:
    """Return the configured LLM client instance."""
    return QwenClient()
