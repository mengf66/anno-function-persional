#!/usr/bin/env python3
"""Core-path test: multi input_bindings + multi output_bindings."""

from __future__ import annotations


def main(left: str, right: str) -> dict:
    if not isinstance(left, str) or not isinstance(right, str):
        raise TypeError("left/right must be strings")
    return {
        "joined": f"{left}|{right}",
        "left_upper": left.upper(),
        "right_len": len(right),
    }
