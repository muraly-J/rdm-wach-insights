"""
core/query_classifier.py
────────────────────────
Heuristic classifier: decides whether a user query needs Qwen3 chain-of-thought
reasoning (/think) or can be answered quickly (/no_think).

Returns "think" or "fast". Adds ~1ms. No external calls.
"""
import re
from typing import Literal

_THINK_KEYWORDS = re.compile(
    r"\b(why|cause|causes|reason|reasons|explain|analyse|analyze|analysis|"
    r"compare|versus|\bvs\b|trend|over time|pattern|recommend|recommendation|"
    r"should i|what should|root cause|diagnose|investigate|worsening|"
    r"worsen|deteriorat|forecast|predict|prediction|next week|next month|"
    r"breakdown|deep.?dive|summary of)\b",
    re.IGNORECASE,
)

_FAST_PATTERNS = [
    re.compile(r"^what (is|are) (the )?(health|status|score|tier)", re.IGNORECASE),
    re.compile(r"^(show|list|give) me .{0,50}$", re.IGNORECASE),
    re.compile(r"^is e\d{4}", re.IGNORECASE),
    re.compile(r"^how many", re.IGNORECASE),
    re.compile(r"^(what|which) (level|floor|department)", re.IGNORECASE),
]

_DEVICE_ID_RE = re.compile(r"\be\d{4}\b")
_LEVEL_RE = re.compile(r"\blevel\s*\d+\b", re.IGNORECASE)


def classify_query_complexity(
    message: str,
    history: list,
) -> Literal["think", "fast"]:
    """
    Classify a user query as needing deep reasoning or a fast response.

    Args:
        message: The raw user message.
        history: Full conversation history (list of {"role": ..., ...} dicts).

    Returns:
        "think" or "fast"
    """
    msg = message.strip()
    msg_lower = msg.lower()

    # Short messages with no think keywords → fast
    if len(msg) < 60 and not _THINK_KEYWORDS.search(msg_lower):
        return "fast"

    # Fast regex patterns — check before think keywords
    for pattern in _FAST_PATTERNS:
        if pattern.match(msg):
            return "fast"

    # Think keywords present
    if _THINK_KEYWORDS.search(msg_lower):
        return "think"

    # Three or more device IDs → comparative analysis
    if len(_DEVICE_ID_RE.findall(msg)) >= 3:
        return "think"

    # Two or more level references → cross-level comparison
    if len(_LEVEL_RE.findall(msg)) >= 2:
        return "think"

    # Mid-deep conversation + long message → likely a follow-up analysis
    if len(history) >= 6 and len(msg) > 80:
        return "think"

    return "fast"
