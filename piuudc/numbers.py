"""Numeric helpers."""


def clamp(value: int, minimum: int, maximum: int) -> int:
    """Restrict value to the given inclusive range."""
    return max(minimum, min(value, maximum))


def safe_int(value: str, fallback: int = 0) -> int:
    """Parse integer text, returning fallback for invalid values."""
    try:
        return int(value.strip())
    except (TypeError, ValueError, AttributeError):
        return fallback
