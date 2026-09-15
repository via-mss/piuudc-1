"""Iterable helpers."""


def chunked(items: list[str], size: int) -> list[list[str]]:
    """Split items into equally sized chunks."""
    if size <= 0:
        raise ValueError("size must be positive")
    return [items[index:index + size] for index in range(0, len(items), size)]


def flatten_once(groups: list[list[str]]) -> list[str]:
    """Flatten one nesting level from a list of lists."""
    return [item for group in groups for item in group]


def unique_preserve_order(items: list[str]) -> list[str]:
    """Deduplicate strings while keeping their original order."""
    seen: set[str] = set()
    output: list[str] = []
    for item in items:
        if item in seen:
            continue
        seen.add(item)
        output.append(item)
    return output
