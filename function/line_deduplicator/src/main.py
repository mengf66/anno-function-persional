#!/usr/bin/env python3
"""Remove duplicate lines while preserving their first occurrence."""


def deduplicate_lines(text_field: str) -> dict:
    """Return the text with duplicate lines removed in encounter order."""
    if not isinstance(text_field, str):
        raise TypeError("text_field must be a string")

    lines = text_field.splitlines()
    unique_lines: list[str] = []
    seen: set[str] = set()

    for line in lines:
        if line in seen:
            continue
        seen.add(line)
        unique_lines.append(line)

    return {
        "result": "\n".join(unique_lines),
        "original_line_count": len(lines),
        "unique_line_count": len(unique_lines),
        "removed_count": len(lines) - len(unique_lines),
    }


def run(parameters: dict) -> dict:
    """Run the function from a parameter payload."""
    return main(text_field=parameters["text_field"])


def main(text_field: str) -> dict:
    """Run the Function with parameters supplied by anno-function-runner."""
    return deduplicate_lines(text_field)
