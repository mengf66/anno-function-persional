#!/usr/bin/env python3
"""Find duplicate values in a JSON array."""

import json
import sys


def find_duplicates(items: list) -> list:
    """Return duplicate values once, preserving their first duplicate order."""
    seen = set()
    duplicates = []
    duplicate_set = set()

    for item in items:
        if item in seen and item not in duplicate_set:
            duplicates.append(item)
            duplicate_set.add(item)
        seen.add(item)

    return duplicates


def main() -> int:
    try:
        items = json.loads(sys.argv[1] if len(sys.argv) > 1 else sys.stdin.read())
        if not isinstance(items, list):
            raise ValueError("input must be a JSON array")

        duplicates = find_duplicates(items)
        print(json.dumps({"has_duplicates": bool(duplicates), "duplicates": duplicates}, ensure_ascii=False))
        return 0
    except (json.JSONDecodeError, TypeError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
