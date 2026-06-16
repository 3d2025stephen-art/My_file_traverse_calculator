"""
tests/test_clipboard_pipeline.py
---------------------------------
Unit tests for clipboard_pipeline.py (mocking actual clipboard I/O)
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from clipboard_pipeline import ClipboardPipeline


# ------------------------------------------------------------------ #
# Fixture — pipeline backed by a temp session file                     #
# ------------------------------------------------------------------ #


@pytest.fixture()
def pipe(tmp_path: Path) -> ClipboardPipeline:
    return ClipboardPipeline(
        session="test",
        session_file=str(tmp_path / "sessions.json"),
    )


# ------------------------------------------------------------------ #
# Basic value manipulation                                             #
# ------------------------------------------------------------------ #


def test_set_value(pipe: ClipboardPipeline) -> None:
    pipe.set("hello")
    assert pipe.value == "hello"


def test_apply_transform(pipe: ClipboardPipeline) -> None:
    pipe.set("  spaces  ").apply(str.strip)
    assert pipe.value == "spaces"


def test_chaining_returns_self(pipe: ClipboardPipeline) -> None:
    result = pipe.set("x").apply(str.upper)
    assert result is pipe
    assert pipe.value == "X"


# ------------------------------------------------------------------ #
# Clipboard read / write (mocked)                                      #
# ------------------------------------------------------------------ #


def test_read_clipboard(pipe: ClipboardPipeline, tmp_path: Path) -> None:
    with patch(
        "clipboard_pipeline._read_clipboard", return_value=str(tmp_path)
    ):
        pipe.read_clipboard()
    assert pipe.value == str(tmp_path)


def test_write_clipboard(pipe: ClipboardPipeline) -> None:
    written = []
    with patch("clipboard_pipeline._write_clipboard", side_effect=written.append):
        pipe.set("output text").write_clipboard()
    assert written == ["output text"]


# ------------------------------------------------------------------ #
# Traverse + summarise / file_list                                     #
# ------------------------------------------------------------------ #


@pytest.fixture()
def tree(tmp_path: Path) -> Path:
    (tmp_path / "file1.txt").write_bytes(b"a" * 100)
    (tmp_path / "file2.py").write_bytes(b"b" * 200)
    return tmp_path


def test_traverse_and_summarise(pipe: ClipboardPipeline, tree: Path) -> None:
    pipe.set(str(tree)).traverse().summarise()
    assert "Files" in pipe.value
    assert "Total" in pipe.value


def test_traverse_and_file_list(pipe: ClipboardPipeline, tree: Path) -> None:
    pipe.set(str(tree)).traverse().file_list()
    assert "file1.txt" in pipe.value
    assert "file2.py" in pipe.value


def test_traversal_result_accessible(pipe: ClipboardPipeline, tree: Path) -> None:
    pipe.set(str(tree)).traverse()
    assert pipe.traversal_result is not None
    assert pipe.traversal_result.total_files == 2


def test_traverse_bad_path_raises(pipe: ClipboardPipeline) -> None:
    pipe.set("/no/such/path")
    with pytest.raises(FileNotFoundError):
        pipe.traverse()


# ------------------------------------------------------------------ #
# Session save / load                                                  #
# ------------------------------------------------------------------ #


def test_save_and_load_session(pipe: ClipboardPipeline) -> None:
    pipe.set("my saved content").save_to_session()
    pipe.set("")  # wipe
    pipe.load_from_session()
    assert pipe.value == "my saved content"


def test_save_and_load_pinned(pipe: ClipboardPipeline) -> None:
    pipe.set("pinned content").save_to_session(label="bookmark")
    pipe.set("")
    pipe.load_from_session(label="bookmark")
    assert pipe.value == "pinned content"


def test_load_missing_label(pipe: ClipboardPipeline) -> None:
    pipe.set("original")
    pipe.load_from_session(label="nonexistent")
    # value should be unchanged when label is missing
    assert pipe.value == "original"


# ------------------------------------------------------------------ #
# Full pipeline integration (no real clipboard)                        #
# ------------------------------------------------------------------ #


def test_full_pipeline(pipe: ClipboardPipeline, tree: Path) -> None:
    written = []
    with patch("clipboard_pipeline._write_clipboard", side_effect=written.append):
        (
            pipe
            .set(str(tree))
            .traverse()
            .summarise()
            .write_clipboard()
        )
    assert len(written) == 1
    assert "Files" in written[0]
