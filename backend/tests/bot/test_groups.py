"""Tests for bot group identity resolution."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))


def test_managers_group_recognized(monkeypatch):
    monkeypatch.setenv("MANAGERS_CHAT_ID", "-1001111")
    monkeypatch.setenv("ENGINEERS_CHAT_ID", "-1002222")
    monkeypatch.setenv("TECHNICIANS_CHAT_ID", "-1003333")
    import importlib
    import bot.groups as groups_mod
    importlib.reload(groups_mod)
    from bot.groups import get_group
    assert get_group(-1001111) == "managers"


def test_engineers_group_recognized(monkeypatch):
    monkeypatch.setenv("MANAGERS_CHAT_ID", "-1001111")
    monkeypatch.setenv("ENGINEERS_CHAT_ID", "-1002222")
    monkeypatch.setenv("TECHNICIANS_CHAT_ID", "-1003333")
    import importlib
    import bot.groups as groups_mod
    importlib.reload(groups_mod)
    from bot.groups import get_group
    assert get_group(-1002222) == "engineers"


def test_technicians_group_recognized(monkeypatch):
    monkeypatch.setenv("MANAGERS_CHAT_ID", "-1001111")
    monkeypatch.setenv("ENGINEERS_CHAT_ID", "-1002222")
    monkeypatch.setenv("TECHNICIANS_CHAT_ID", "-1003333")
    import importlib
    import bot.groups as groups_mod
    importlib.reload(groups_mod)
    from bot.groups import get_group
    assert get_group(-1003333) == "technicians"


def test_unknown_chat_returns_none(monkeypatch):
    monkeypatch.setenv("MANAGERS_CHAT_ID", "-1001111")
    monkeypatch.setenv("ENGINEERS_CHAT_ID", "-1002222")
    monkeypatch.setenv("TECHNICIANS_CHAT_ID", "-1003333")
    import importlib
    import bot.groups as groups_mod
    importlib.reload(groups_mod)
    from bot.groups import get_group
    assert get_group(-9999999) is None
