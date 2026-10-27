"""Resolve requested locations under the application's download root."""

from pathlib import Path


def resolve_download(root: Path, requested: str) -> Path:
    resolved_root = Path(root).resolve()
    target = (resolved_root / requested).resolve()
    if not str(target).startswith(str(resolved_root)):
        raise ValueError("requested location is outside the download root")
    return target
