"""Iterable helpers."""


def chunked(items: list[str], size: int) -> list[list[str]]:
    """Split items into equally sized chunks."""
    if size <= 0:
        raise ValueError("size must be positive")
    return [items[index:index + size] for index in range(0, len(items), size)]
