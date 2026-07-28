#!/usr/bin/env python3
"""Text similarity checker entry point."""

import json
import sys
from difflib import SequenceMatcher


def check_text_similarity(
    text_field: str,
    existing_texts: list[str],
    confidence: float = 0.8,
) -> dict:
    """Compare a target with existing texts and return the closest match."""
    if not 0 <= confidence <= 1:
        raise ValueError("confidence must be between 0 and 1")

    best_text = ""
    best_value = 0.0
    for candidate in existing_texts:
        value = SequenceMatcher(None, text_field, candidate).ratio()
        if value > best_value:
            best_text = candidate
            best_value = value

    return {
        "result": best_value <= confidence,
        "sim_text": best_text,
        "value": round(best_value, 4),
    }


def run(parameters: dict) -> dict:
    """Run the function from a parameter payload."""
    return check_text_similarity(
        text_field=parameters["text_field"],
        existing_texts=parameters.get("existing_texts", []),
        confidence=float(parameters.get("confidence", 0.8)),
    )


def main() -> int:
    payload = json.loads(sys.argv[1] if len(sys.argv) > 1 else sys.stdin.read())
    print(json.dumps(run(payload), ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
