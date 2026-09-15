"""Iterable helpers."""


def chunked(items: list[str], size: int) -> list[list[str]]:
    """Split items into equally sized chunks."""
    if size <= 0:
        raise ValueError("size must be positive")
    return [items[index:index + size] for index in range(0, len(items), size)]


def flatten_once(groups: list[list[str]]) -> list[str]:
    """Flatten one nesting level from a list of lists."""
    return [item for group in groups for item in group]
