#!/usr/bin/env python3
"""Check whether a keyword occurs in text and count its occurrences."""


def check_keyword_occurrences(
    text_field: str,
    keyword: str,
    case_sensitive: bool = False,
) -> dict:
    """Count non-overlapping keyword occurrences in the supplied text."""
    if not keyword:
        raise ValueError("keyword must not be empty")

    search_text = text_field if case_sensitive else text_field.casefold()
    search_keyword = keyword if case_sensitive else keyword.casefold()
    match_count = search_text.count(search_keyword)

    return {
        "result": match_count > 0,
        "match_count": match_count,
    }


def run(parameters: dict) -> dict:
    """Run the function from a parameter payload."""
    return main(
        text_field=parameters["text_field"],
        keyword=parameters["keyword"],
        case_sensitive=parameters.get("case_sensitive", False),
    )


def main(
    text_field: str,
    keyword: str,
    case_sensitive: bool = False,
) -> dict:
    """Run the Function with parameters supplied by anno-function-runner."""
    return check_keyword_occurrences(
        text_field=text_field,
        keyword=keyword,
        case_sensitive=case_sensitive,
    )
