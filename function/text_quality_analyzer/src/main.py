#!/usr/bin/env python3
"""Text quality analyzer entry point."""

import re


LINE_BOUNDARIES = (
    "\n",
    "\r",
    "\x0b",
    "\x0c",
    "\x1c",
    "\x1d",
    "\x1e",
    "\x85",
    "\u2028",
    "\u2029",
)


def count_lines(text: str) -> int:
    """Count logical lines, including an empty line after a trailing boundary."""
    if not text:
        return 0
    return len(text.splitlines()) + int(text.endswith(LINE_BOUNDARIES))


def analyze_text(text_field: str, max_length: int = 0) -> dict:
    """Measure text and apply an optional character limit."""
    if not isinstance(text_field, str):
        raise TypeError("text_field must be a string")
    if isinstance(max_length, bool) or not isinstance(max_length, int):
        raise TypeError("max_length must be an integer")
    if max_length < 0:
        raise ValueError("max_length must be zero or greater")

    char_count = len(text_field)
    return {
        "result": max_length == 0 or char_count <= max_length,
        "char_count": char_count,
        "non_whitespace_count": sum(
            not character.isspace() for character in text_field
        ),
        "word_count": len(re.findall(r"[^\W_]+", text_field, flags=re.UNICODE)),
        "line_count": count_lines(text_field),
    }


def run(parameters: dict) -> dict:
    """Run the function from a parameter payload."""
    return main(
        text_field=parameters["text_field"],
        max_length=int(parameters.get("max_length", 0)),
    )


def main(text_field: str, max_length: int = 0) -> dict:
    """Run the Function with parameters supplied by anno-function-runner."""
    return analyze_text(text_field=text_field, max_length=max_length)
