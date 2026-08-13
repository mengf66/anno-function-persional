#!/usr/bin/env python3
"""Core-path test: lazy field map + multi-output + empty-bound tolerance."""

from __future__ import annotations


def main(text_field: str, empty_field: str | None = None) -> dict:
    if not isinstance(text_field, str):
        raise TypeError("text_field must be a string")
    lines = text_field.splitlines()
    unique: list[str] = []
    seen: set[str] = set()
    for line in lines:
        if line in seen:
            continue
        seen.add(line)
        unique.append(line)
    empty = empty_field is None or (isinstance(empty_field, str) and empty_field == "")
    return {
        "result": "\n".join(unique),
        "line_count": len(lines),
        "empty_is_none": empty,
        "status": "ok",
    }
