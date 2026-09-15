"""Numeric helpers."""


def clamp(value: int, minimum: int, maximum: int) -> int:
    """Restrict value to the given inclusive range."""
    return max(minimum, min(value, maximum))
