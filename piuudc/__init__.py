"""Core helpers for piuudc-1."""

from .filesystem import read_text, write_text
from .iterables import chunked, flatten_once, unique_preserve_order
from .numbers import clamp, safe_int
from .text import is_blank, normalize_whitespace, slugify

__all__ = [
    "chunked",
    "clamp",
    "flatten_once",
    "is_blank",
    "normalize_whitespace",
    "read_text",
    "safe_int",
    "slugify",
    "unique_preserve_order",
    "write_text",
]
