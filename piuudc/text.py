"""Text helpers."""


def normalize_whitespace(value: str) -> str:
    """Collapse runs of whitespace and trim edges."""
    return " ".join(value.split())
