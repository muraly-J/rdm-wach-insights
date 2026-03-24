import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from routes.chat import _build_gemini_history, _MAX_HISTORY


def _make_item(role: str, content: str):
    """Create a ChatHistoryItem. Import path may vary — adjust if needed."""
    try:
        from models.schemas import ChatHistoryItem
    except ImportError:
        # Fallback: create a simple namespace object
        from types import SimpleNamespace
        return SimpleNamespace(role=role, content=content)
    return ChatHistoryItem(role=role, content=content)


def test_max_history_is_six():
    """Only last 6 turns are passed to the LLM."""
    items = [_make_item("user", f"msg {i}") for i in range(20)]
    result = _build_gemini_history(items)
    assert len(result) == 6
    assert result[-1]["parts"][0] == "msg 19"


def test_bot_reply_truncated_to_400_chars():
    """Long bot replies in history are trimmed to prevent data dump pollution."""
    long_reply = "e0301: 0.9%\n" * 50  # 600+ chars
    items = [_make_item("model", long_reply)]
    result = _build_gemini_history(items)
    assert len(result[0]["parts"][0]) <= 403  # 400 + "…"
    assert result[0]["parts"][0].endswith("…")


def test_short_reply_not_truncated():
    """Replies under 400 chars are passed through unchanged."""
    short = "The health score is 85/100."
    items = [_make_item("model", short)]
    result = _build_gemini_history(items)
    assert result[0]["parts"][0] == short


def test_user_messages_not_truncated():
    """User messages are never truncated."""
    long_user = "x" * 600
    items = [_make_item("user", long_user)]
    result = _build_gemini_history(items)
    assert result[0]["parts"][0] == long_user
