"""
session_manager.py
------------------
Persists clipboard history and named sessions to a local JSON file so
that clipboard contents survive across terminal/script restarts.
"""

from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional


_DEFAULT_SESSION_FILE = Path.home() / ".my_file_calc_sessions.json"
_MAX_HISTORY = 100  # keep at most this many history entries per session


class SessionManager:
    """
    Manages named clipboard sessions stored in a JSON file on disk.

    Each session holds:
      - ``history`` : list of (timestamp, content) pairs
      - ``pinned``  : a dict of label → content for frequently used snippets
    """

    def __init__(self, session_file: Optional[str] = None) -> None:
        self._path = Path(session_file) if session_file else _DEFAULT_SESSION_FILE
        self._data: Dict = self._load()

    # ------------------------------------------------------------------ #
    # Persistence                                                          #
    # ------------------------------------------------------------------ #

    def _load(self) -> Dict:
        if self._path.exists():
            try:
                with open(self._path, "r", encoding="utf-8") as fh:
                    return json.load(fh)
            except (json.JSONDecodeError, OSError):
                pass
        return {}

    def save(self) -> None:
        """Write the in-memory session data back to disk."""
        self._path.parent.mkdir(parents=True, exist_ok=True)
        with open(self._path, "w", encoding="utf-8") as fh:
            json.dump(self._data, fh, indent=2, ensure_ascii=False)

    # ------------------------------------------------------------------ #
    # Session helpers                                                      #
    # ------------------------------------------------------------------ #

    def _session(self, name: str) -> Dict:
        """Return (creating if necessary) the dict for *name*."""
        if name not in self._data:
            self._data[name] = {"history": [], "pinned": {}}
        return self._data[name]

    def list_sessions(self) -> List[str]:
        """Return the names of all stored sessions."""
        return sorted(self._data.keys())

    def delete_session(self, name: str) -> bool:
        """Delete a session. Returns True if it existed."""
        if name in self._data:
            del self._data[name]
            self.save()
            return True
        return False

    # ------------------------------------------------------------------ #
    # History                                                              #
    # ------------------------------------------------------------------ #

    def push(self, name: str, content: str) -> None:
        """Append *content* to the history of session *name*."""
        session = self._session(name)
        session["history"].append(
            {
                "timestamp": datetime.now().isoformat(timespec="seconds"),
                "content": content,
            }
        )
        # trim to max history
        if len(session["history"]) > _MAX_HISTORY:
            session["history"] = session["history"][-_MAX_HISTORY:]
        self.save()

    def latest(self, name: str) -> Optional[str]:
        """Return the most recently pushed content for session *name*."""
        history = self._session(name).get("history", [])
        return history[-1]["content"] if history else None

    def history(self, name: str, n: int = 10) -> List[Dict]:
        """Return the last *n* history entries for session *name*."""
        entries = self._session(name).get("history", [])
        return entries[-n:]

    def clear_history(self, name: str) -> None:
        """Erase the history list for session *name*."""
        self._session(name)["history"] = []
        self.save()

    # ------------------------------------------------------------------ #
    # Pinned snippets                                                      #
    # ------------------------------------------------------------------ #

    def pin(self, name: str, label: str, content: str) -> None:
        """Pin *content* under *label* in session *name*."""
        self._session(name)["pinned"][label] = content
        self.save()

    def unpin(self, name: str, label: str) -> bool:
        """Remove the pinned entry *label* from session *name*."""
        pinned = self._session(name).get("pinned", {})
        if label in pinned:
            del pinned[label]
            self.save()
            return True
        return False

    def get_pinned(self, name: str, label: str) -> Optional[str]:
        """Return the content pinned under *label* in session *name*."""
        return self._session(name).get("pinned", {}).get(label)

    def list_pinned(self, name: str) -> Dict[str, str]:
        """Return all pinned entries for session *name*."""
        return dict(self._session(name).get("pinned", {}))

    # ------------------------------------------------------------------ #
    # Display                                                              #
    # ------------------------------------------------------------------ #

    def summary(self, name: str) -> str:
        session = self._session(name)
        history = session.get("history", [])
        pinned = session.get("pinned", {})
        lines = [
            f"Session  : {name}",
            f"History  : {len(history)} item(s)"
            f" (last: {history[-1]['timestamp'] if history else 'n/a'})",
            f"Pinned   : {len(pinned)} item(s)",
        ]
        if pinned:
            for label, content in pinned.items():
                preview = content[:60].replace("\n", " ")
                lines.append(f"  [{label}]  {preview!r}")
        return "\n".join(lines)
