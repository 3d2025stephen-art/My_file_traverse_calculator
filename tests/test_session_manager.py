"""
tests/test_session_manager.py
-----------------------------
Unit tests for session_manager.py
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from session_manager import SessionManager


# ------------------------------------------------------------------ #
# Fixture — in-memory / temp-file session                              #
# ------------------------------------------------------------------ #


@pytest.fixture()
def mgr(tmp_path: Path) -> SessionManager:
    return SessionManager(session_file=str(tmp_path / "sessions.json"))


# ------------------------------------------------------------------ #
# History                                                              #
# ------------------------------------------------------------------ #


def test_push_and_latest(mgr: SessionManager) -> None:
    mgr.push("s1", "hello")
    assert mgr.latest("s1") == "hello"


def test_push_multiple_latest_returns_last(mgr: SessionManager) -> None:
    mgr.push("s1", "first")
    mgr.push("s1", "second")
    assert mgr.latest("s1") == "second"


def test_latest_empty_session(mgr: SessionManager) -> None:
    assert mgr.latest("nonexistent") is None


def test_history_length(mgr: SessionManager) -> None:
    for i in range(5):
        mgr.push("s1", f"item{i}")
    assert len(mgr.history("s1", n=3)) == 3
    assert len(mgr.history("s1", n=10)) == 5


def test_clear_history(mgr: SessionManager) -> None:
    mgr.push("s1", "data")
    mgr.clear_history("s1")
    assert mgr.history("s1") == []


# ------------------------------------------------------------------ #
# Pinned snippets                                                      #
# ------------------------------------------------------------------ #


def test_pin_and_get(mgr: SessionManager) -> None:
    mgr.pin("s1", "mydir", "/some/path")
    assert mgr.get_pinned("s1", "mydir") == "/some/path"


def test_unpin(mgr: SessionManager) -> None:
    mgr.pin("s1", "label", "content")
    removed = mgr.unpin("s1", "label")
    assert removed is True
    assert mgr.get_pinned("s1", "label") is None


def test_unpin_nonexistent(mgr: SessionManager) -> None:
    assert mgr.unpin("s1", "missing") is False


def test_list_pinned(mgr: SessionManager) -> None:
    mgr.pin("s1", "a", "A")
    mgr.pin("s1", "b", "B")
    pinned = mgr.list_pinned("s1")
    assert pinned == {"a": "A", "b": "B"}


# ------------------------------------------------------------------ #
# Session CRUD                                                         #
# ------------------------------------------------------------------ #


def test_list_sessions(mgr: SessionManager) -> None:
    mgr.push("alpha", "x")
    mgr.push("beta", "y")
    sessions = mgr.list_sessions()
    assert "alpha" in sessions
    assert "beta" in sessions


def test_delete_session(mgr: SessionManager) -> None:
    mgr.push("s1", "data")
    deleted = mgr.delete_session("s1")
    assert deleted is True
    assert "s1" not in mgr.list_sessions()


def test_delete_nonexistent(mgr: SessionManager) -> None:
    assert mgr.delete_session("ghost") is False


# ------------------------------------------------------------------ #
# Persistence                                                          #
# ------------------------------------------------------------------ #


def test_persists_to_disk(tmp_path: Path) -> None:
    path = str(tmp_path / "sessions.json")
    m1 = SessionManager(session_file=path)
    m1.push("s1", "persisted")

    m2 = SessionManager(session_file=path)
    assert m2.latest("s1") == "persisted"


def test_summary_contains_session_name(mgr: SessionManager) -> None:
    mgr.push("mySession", "some content")
    summary = mgr.summary("mySession")
    assert "mySession" in summary
