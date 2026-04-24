from __future__ import annotations

"""
bot/ui/messages.py
───────────────────
i18n-ready string helper stub.

Currently returns the key formatted with the provided kwargs.
When i18n is added, replace the body of `t()` with a lookup
against a locale catalogue (e.g. gettext, fluent, or a YAML bundle).
"""


def t(key: str, **kwargs) -> str:
    """Return translated string. Currently returns key formatted with kwargs."""
    return key.format(**kwargs)
