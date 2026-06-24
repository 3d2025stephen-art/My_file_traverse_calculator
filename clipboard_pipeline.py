"""
clipboard_pipeline.py
---------------------
Clipboard read/write helpers and a composable pipeline for
My_file_traverse_calculator.

The pipeline works as a simple chain:
  ClipboardPipeline().read_clipboard().traverse().summarise().write_clipboard()

Each step transforms an internal ``_value`` string and returns ``self``
so calls can be fluently chained.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Callable, List, Optional

from file_traverser import TraversalResult, traverse
from session_manager import SessionManager


# ------------------------------------------------------------------ #
# Low-level clipboard I/O                                              #
# ------------------------------------------------------------------ #


def _read_clipboard() -> str:
    """Return the current clipboard text (cross-platform, best-effort)."""
    try:
        import pyperclip  # type: ignore
        return pyperclip.paste() or ""
    except Exception:
        pass

    if sys.platform == "win32":
        try:
            import subprocess
            result = subprocess.run(
                ["powershell", "-Command", "Get-Clipboard"],
                capture_output=True, text=True, timeout=5,
            )
            return result.stdout.strip()
        except Exception:
            pass

    if sys.platform == "darwin":
        try:
            import subprocess
            result = subprocess.run(
                ["pbpaste"], capture_output=True, text=True, timeout=5,
            )
            return result.stdout
        except Exception:
            pass

    # Linux / fallback
    try:
        import subprocess
        for tool in (["xclip", "-selection", "clipboard", "-o"],
                     ["xsel", "--clipboard", "--output"]):
            try:
                result = subprocess.run(
                    tool, capture_output=True, text=True, timeout=5,
                )
                if result.returncode == 0:
                    return result.stdout
            except FileNotFoundError:
                continue
    except Exception:
        pass

    return ""


def _write_clipboard(text: str) -> None:
    """Write *text* to the system clipboard (cross-platform, best-effort)."""
    try:
        import pyperclip  # type: ignore
        pyperclip.copy(text)
        return
    except Exception:
        pass

    if sys.platform == "win32":
        try:
            import subprocess
            subprocess.run(
                ["powershell", "-Command",
                 f"Set-Clipboard -Value @'\n{text}\n'@"],
                timeout=5,
            )
            return
        except Exception:
            pass

    if sys.platform == "darwin":
        try:
            import subprocess
            proc = subprocess.Popen(["pbcopy"], stdin=subprocess.PIPE)
            proc.communicate(text.encode())
            return
        except Exception:
            pass

    try:
        import subprocess
        for tool in (["xclip", "-selection", "clipboard"],
                     ["xsel", "--clipboard", "--input"]):
            try:
                proc = subprocess.Popen(tool, stdin=subprocess.PIPE)
                proc.communicate(text.encode())
                return
            except FileNotFoundError:
                continue
    except Exception:
        pass


# ------------------------------------------------------------------ #
# Pipeline                                                             #
# ------------------------------------------------------------------ #


class ClipboardPipeline:
    """
    Fluent pipeline that threads a string value through a sequence of
    transformations, with optional clipboard read/write at either end.

    Example
    -------
    ::

        result = (
            ClipboardPipeline(session="work")
            .read_clipboard()           # pull a directory path from clipboard
            .traverse()                  # walk that directory
            .summarise()                 # convert TraversalResult → summary text
            .write_clipboard()           # push summary back to clipboard
            .value                       # retrieve final string
        )
    """

    def __init__(
        self,
        initial_value: str = "",
        session: str = "default",
        session_file: Optional[str] = None,
    ) -> None:
        self._value: str = initial_value
        self._result: Optional[TraversalResult] = None
        self._session_mgr = SessionManager(session_file=session_file)
        self._session = session

    # ------------------------------------------------------------------ #
    # Value access                                                         #
    # ------------------------------------------------------------------ #

    @property
    def value(self) -> str:
        return self._value

    @property
    def traversal_result(self) -> Optional[TraversalResult]:
        """The last TraversalResult produced by :meth:`traverse`, if any."""
        return self._result

    # ------------------------------------------------------------------ #
    # Pipeline steps                                                       #
    # ------------------------------------------------------------------ #

    def set(self, text: str) -> "ClipboardPipeline":
        """Manually set the pipeline value."""
        self._value = text
        return self

    def read_clipboard(self) -> "ClipboardPipeline":
        """Replace the current value with the system clipboard contents."""
        self._value = _read_clipboard().strip()
        return self

    def write_clipboard(self) -> "ClipboardPipeline":
        """Copy the current value to the system clipboard."""
        _write_clipboard(self._value)
        return self

    def traverse(
        self,
        *,
        max_depth: Optional[int] = None,
        include_hidden: bool = False,
        extensions: Optional[List[str]] = None,
    ) -> "ClipboardPipeline":
        """
        Treat the current value as a directory path and traverse it.

        After this step, :attr:`traversal_result` holds the
        :class:`~file_traverser.TraversalResult` and the pipeline value
        is set to the root path of that result.
        """
        path = self._value.strip().strip('"').strip("'")
        self._result = traverse(
            path,
            max_depth=max_depth,
            include_hidden=include_hidden,
            extensions=extensions,
        )
        self._value = self._result.root
        return self

    def summarise(self) -> "ClipboardPipeline":
        """
        Replace the current value with the human-readable summary of the
        last traversal result.  If no traversal has been performed the
        value is left unchanged.
        """
        if self._result is not None:
            self._value = self._result.summary()
        return self

    # alias for British/American spelling
    summarize = summarise

    def file_list(self) -> "ClipboardPipeline":
        """
        Replace the current value with a newline-separated list of file
        paths from the last traversal result.
        """
        if self._result is not None:
            self._value = self._result.file_list()
        return self

    def apply(self, fn: Callable[[str], str]) -> "ClipboardPipeline":
        """Apply an arbitrary transformation function to the current value."""
        self._value = fn(self._value)
        return self

    def save_to_session(self, label: Optional[str] = None) -> "ClipboardPipeline":
        """
        Persist the current value to the session history (and optionally
        pin it under *label*).
        """
        self._session_mgr.push(self._session, self._value)
        if label:
            self._session_mgr.pin(self._session, label, self._value)
        return self

    def load_from_session(self, label: Optional[str] = None) -> "ClipboardPipeline":
        """
        Load the most-recent (or pinned *label*) value from the session.
        """
        if label:
            content = self._session_mgr.get_pinned(self._session, label)
        else:
            content = self._session_mgr.latest(self._session)
        if content is not None:
            self._value = content
        return self

    def print(self, prefix: str = "") -> "ClipboardPipeline":
        """Print the current value to stdout (non-destructive)."""
        if prefix:
            print(prefix)
        print(self._value)
        return self

    # ------------------------------------------------------------------ #
    # Session manager access                                               #
    # ------------------------------------------------------------------ #

    @property
    def session_manager(self) -> SessionManager:
        return self._session_mgr
