#!/usr/bin/env python3
"""Core-path test: static parameters only (no field lazy fetch)."""

from __future__ import annotations


def main(prefix: str, value: int) -> dict:
    return {"message": f"{prefix}:{value}", "value": int(value)}
