"""Text helpers."""


def normalize_whitespace(value: str) -> str:
    """Collapse runs of whitespace and trim edges."""
    return " ".join(value.split())


def is_blank(value: str) -> bool:
    """Return True when text contains only whitespace."""
    return normalize_whitespace(value) == ""
