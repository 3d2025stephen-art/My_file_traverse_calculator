"""
tests/test_file_traverser.py
----------------------------
Unit tests for file_traverser.py
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

import pytest

# Make sure the package root is on sys.path when running from the repo root
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from file_traverser import traverse, TraversalResult


# ------------------------------------------------------------------ #
# Fixtures                                                             #
# ------------------------------------------------------------------ #


@pytest.fixture()
def tmp_tree(tmp_path: Path) -> Path:
    """
    Creates a small directory tree:

        tmp_path/
          a.txt  (10 bytes)
          b.py   (20 bytes)
          sub/
            c.txt (5 bytes)
            .hidden (3 bytes)
    """
    (tmp_path / "a.txt").write_bytes(b"x" * 10)
    (tmp_path / "b.py").write_bytes(b"x" * 20)
    sub = tmp_path / "sub"
    sub.mkdir()
    (sub / "c.txt").write_bytes(b"x" * 5)
    (sub / ".hidden").write_bytes(b"x" * 3)
    return tmp_path


# ------------------------------------------------------------------ #
# Basic traversal                                                      #
# ------------------------------------------------------------------ #


def test_total_files(tmp_tree: Path) -> None:
    result = traverse(str(tmp_tree))
    # .hidden is excluded by default
    assert result.total_files == 3


def test_total_size(tmp_tree: Path) -> None:
    result = traverse(str(tmp_tree))
    assert result.total_size_bytes == 35  # 10 + 20 + 5


def test_total_dirs(tmp_tree: Path) -> None:
    result = traverse(str(tmp_tree))
    assert result.total_dirs == 1  # only 'sub'


def test_include_hidden(tmp_tree: Path) -> None:
    result = traverse(str(tmp_tree), include_hidden=True)
    assert result.total_files == 4
    assert result.total_size_bytes == 38  # 10 + 20 + 5 + 3


# ------------------------------------------------------------------ #
# Depth limiting                                                       #
# ------------------------------------------------------------------ #


def test_max_depth_zero(tmp_tree: Path) -> None:
    """Depth 0 = only files directly inside root."""
    result = traverse(str(tmp_tree), max_depth=0)
    assert result.total_files == 2   # a.txt, b.py
    assert result.total_dirs == 1    # sub still counted as a dir entry


def test_max_depth_one(tmp_tree: Path) -> None:
    result = traverse(str(tmp_tree), max_depth=1)
    assert result.total_files == 3


# ------------------------------------------------------------------ #
# Extension filtering                                                  #
# ------------------------------------------------------------------ #


def test_extension_filter(tmp_tree: Path) -> None:
    result = traverse(str(tmp_tree), extensions=[".txt"])
    assert result.total_files == 2   # a.txt, c.txt
    assert result.total_size_bytes == 15


def test_extension_filter_with_dot(tmp_tree: Path) -> None:
    result = traverse(str(tmp_tree), extensions=["txt"])  # without leading dot
    assert result.total_files == 2


# ------------------------------------------------------------------ #
# size_by_extension / count_by_extension                               #
# ------------------------------------------------------------------ #


def test_size_by_extension(tmp_tree: Path) -> None:
    result = traverse(str(tmp_tree))
    assert result.size_by_extension[".txt"] == 15   # 10 + 5
    assert result.size_by_extension[".py"] == 20


def test_count_by_extension(tmp_tree: Path) -> None:
    result = traverse(str(tmp_tree))
    assert result.count_by_extension[".txt"] == 2
    assert result.count_by_extension[".py"] == 1


# ------------------------------------------------------------------ #
# Human-readable size                                                  #
# ------------------------------------------------------------------ #


def test_human_size_bytes(tmp_tree: Path) -> None:
    result = traverse(str(tmp_tree))
    assert "B" in result.human_size()


def test_human_size_mb(tmp_path: Path) -> None:
    # Create a 2 MB file
    big = tmp_path / "big.bin"
    big.write_bytes(b"\x00" * (2 * 1024 * 1024))
    result = traverse(str(tmp_path))
    assert "MB" in result.human_size()


# ------------------------------------------------------------------ #
# Summary / file_list                                                  #
# ------------------------------------------------------------------ #


def test_summary_contains_root(tmp_tree: Path) -> None:
    result = traverse(str(tmp_tree))
    assert str(tmp_tree) in result.summary()


def test_file_list_contains_paths(tmp_tree: Path) -> None:
    result = traverse(str(tmp_tree))
    listing = result.file_list()
    assert "a.txt" in listing
    assert "b.py" in listing


# ------------------------------------------------------------------ #
# Error cases                                                          #
# ------------------------------------------------------------------ #


def test_nonexistent_path() -> None:
    with pytest.raises(FileNotFoundError):
        traverse("/this/path/does/not/exist")


def test_file_not_dir(tmp_path: Path) -> None:
    f = tmp_path / "file.txt"
    f.write_text("hello")
    with pytest.raises(NotADirectoryError):
        traverse(str(f))
