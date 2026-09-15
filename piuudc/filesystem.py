"""Filesystem helpers."""

from pathlib import Path


def read_text(path: str, default: str = "") -> str:
    """Read UTF-8 text from file path or return default when missing."""
    file_path = Path(path)
    if not file_path.exists():
        return default
    return file_path.read_text(encoding="utf-8")


def write_text(path: str, content: str) -> None:
    """Write UTF-8 text to file, creating parent directories when needed."""
    file_path = Path(path)
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text(content, encoding="utf-8")
