#!/usr/bin/env python3
"""Intentionally load malformed JSON for failure-path testing."""

import json


MALFORMED_JSON = """{
  "name": "Anno",
  "enabled": true,
}"""


def run(parameters: dict) -> dict:
    """Run the intentionally broken function from a parameter payload."""
    return main()


def main() -> dict:
    """Raise JSONDecodeError because MALFORMED_JSON has a trailing comma."""
    return json.loads(MALFORMED_JSON)
