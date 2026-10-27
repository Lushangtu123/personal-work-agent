"""Archived implementation before the containment repair."""

from pathlib import Path


def resolve_download(root: Path, requested: str) -> Path:
    return (Path(root).resolve() / requested).resolve()
