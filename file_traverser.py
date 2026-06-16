"""
file_traverser.py
-----------------
Recursive directory traversal and file-system calculations for
My_file_traverse_calculator.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional


@dataclass
class FileInfo:
    path: str
    name: str
    size_bytes: int
    extension: str


@dataclass
class TraversalResult:
    root: str
    total_files: int = 0
    total_dirs: int = 0
    total_size_bytes: int = 0
    files: List[FileInfo] = field(default_factory=list)
    size_by_extension: Dict[str, int] = field(default_factory=dict)
    count_by_extension: Dict[str, int] = field(default_factory=dict)

    # ------------------------------------------------------------------ #
    # Convenience formatters                                               #
    # ------------------------------------------------------------------ #

    @property
    def total_size_kb(self) -> float:
        return self.total_size_bytes / 1024

    @property
    def total_size_mb(self) -> float:
        return self.total_size_bytes / (1024 ** 2)

    @property
    def total_size_gb(self) -> float:
        return self.total_size_bytes / (1024 ** 3)

    def human_size(self) -> str:
        if self.total_size_bytes >= 1024 ** 3:
            return f"{self.total_size_gb:.2f} GB"
        if self.total_size_bytes >= 1024 ** 2:
            return f"{self.total_size_mb:.2f} MB"
        if self.total_size_bytes >= 1024:
            return f"{self.total_size_kb:.2f} KB"
        return f"{self.total_size_bytes} B"

    def summary(self) -> str:
        lines = [
            f"Root     : {self.root}",
            f"Files    : {self.total_files}",
            f"Dirs     : {self.total_dirs}",
            f"Total    : {self.human_size()}",
        ]
        if self.size_by_extension:
            lines.append("By type  :")
            for ext, size in sorted(
                self.size_by_extension.items(),
                key=lambda x: x[1],
                reverse=True,
            ):
                count = self.count_by_extension.get(ext, 0)
                lines.append(
                    f"  {ext or '(no ext)':12s}  {count:5d} file(s)"
                    f"  {_human(size)}"
                )
        return "\n".join(lines)

    def file_list(self) -> str:
        return "\n".join(f.path for f in self.files)


# ------------------------------------------------------------------ #
# Public traversal API                                                 #
# ------------------------------------------------------------------ #


def traverse(
    root: str,
    *,
    max_depth: Optional[int] = None,
    include_hidden: bool = False,
    extensions: Optional[List[str]] = None,
) -> TraversalResult:
    """
    Walk *root* recursively and collect size/count statistics.

    Parameters
    ----------
    root          : Starting directory path.
    max_depth     : Maximum recursion depth (None = unlimited).
    include_hidden: Include files/dirs whose name starts with '.'.
    extensions    : Whitelist of extensions (e.g. ['.py', '.txt']).
                    If None, every file is included.
    """
    root_path = Path(root).resolve()
    if not root_path.exists():
        raise FileNotFoundError(f"Path does not exist: {root_path}")
    if not root_path.is_dir():
        raise NotADirectoryError(f"Not a directory: {root_path}")

    # Normalise extension filter to lowercase with leading dot
    ext_filter: Optional[set] = None
    if extensions is not None:
        ext_filter = {
            (e if e.startswith(".") else f".{e}").lower() for e in extensions
        }

    result = TraversalResult(root=str(root_path))
    _walk(root_path, root_path, result, 0, max_depth, include_hidden, ext_filter)
    return result


# ------------------------------------------------------------------ #
# Internal helpers                                                     #
# ------------------------------------------------------------------ #


def _walk(
    current: Path,
    root: Path,
    result: TraversalResult,
    depth: int,
    max_depth: Optional[int],
    include_hidden: bool,
    ext_filter: Optional[set],
) -> None:
    try:
        entries = list(current.iterdir())
    except PermissionError:
        return

    for entry in entries:
        if not include_hidden and entry.name.startswith("."):
            continue

        if entry.is_symlink():
            continue

        if entry.is_dir():
            result.total_dirs += 1
            if max_depth is None or depth < max_depth:
                _walk(
                    entry, root, result, depth + 1,
                    max_depth, include_hidden, ext_filter,
                )
        elif entry.is_file():
            ext = entry.suffix.lower()
            if ext_filter is not None and ext not in ext_filter:
                continue
            try:
                size = entry.stat().st_size
            except OSError:
                size = 0
            result.total_files += 1
            result.total_size_bytes += size
            result.size_by_extension[ext] = (
                result.size_by_extension.get(ext, 0) + size
            )
            result.count_by_extension[ext] = (
                result.count_by_extension.get(ext, 0) + 1
            )
            result.files.append(
                FileInfo(
                    path=str(entry),
                    name=entry.name,
                    size_bytes=size,
                    extension=ext,
                )
            )


def _human(size: int) -> str:
    if size >= 1024 ** 3:
        return f"{size / (1024 ** 3):.2f} GB"
    if size >= 1024 ** 2:
        return f"{size / (1024 ** 2):.2f} MB"
    if size >= 1024:
        return f"{size / 1024:.2f} KB"
    return f"{size} B"
