"""Canonical query-string storage for a small set of text settings."""

from urllib.parse import parse_qsl, urlencode


def encode_options(options: dict[str, str]) -> str:
    return urlencode(sorted(options.items()))


def decode_options(encoded: str) -> dict[str, str]:
    return dict(parse_qsl(encoded))
