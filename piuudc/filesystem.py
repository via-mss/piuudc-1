"""Filesystem helpers."""

from pathlib import Path


def read_text(path: str, default: str = "") -> str:
    """Read UTF-8 text from file path or return default when missing."""
    file_path = Path(path)
    if not file_path.exists():
        return default
    return file_path.read_text(encoding="utf-8")
