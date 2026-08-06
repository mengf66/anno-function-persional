#!/usr/bin/env python3
"""Replace text and report how many substitutions were made."""


def replace_text(
    text_field: str,
    old_text: str,
    new_text: str,
    max_replacements: int = 0,
) -> dict:
    """Replace non-overlapping occurrences, with zero meaning no limit."""
    if not isinstance(text_field, str):
        raise TypeError("text_field must be a string")
    if not isinstance(old_text, str):
        raise TypeError("old_text must be a string")
    if not isinstance(new_text, str):
        raise TypeError("new_text must be a string")
    if not isinstance(max_replacements, int) or isinstance(max_replacements, bool):
        raise TypeError("max_replacements must be an integer")
    if not old_text:
        raise ValueError("old_text must not be empty")
    if max_replacements < 0:
        raise ValueError("max_replacements must be zero or greater")

    occurrence_count = text_field.count(old_text)
    replacement_count = (
        occurrence_count
        if max_replacements == 0
        else min(occurrence_count, max_replacements)
    )
    replace_limit = -1 if max_replacements == 0 else max_replacements

    return {
        "result": text_field.replace(old_text, new_text, replace_limit),
        "replacement_count": replacement_count,
    }


def run(parameters: dict) -> dict:
    """Run the function from a parameter payload."""
    return main(
        text_field=parameters["text_field"],
        old_text=parameters["old_text"],
        new_text=parameters["new_text"],
        max_replacements=parameters.get("max_replacements", 0),
    )


def main(
    text_field: str,
    old_text: str,
    new_text: str,
    max_replacements: int = 0,
) -> dict:
    """Run the Function with parameters supplied by anno-function-runner."""
    return replace_text(
        text_field=text_field,
        old_text=old_text,
        new_text=new_text,
        max_replacements=max_replacements,
    )
