#!/usr/bin/env python3
"""Validate JSON text and report syntax error details."""

import json


def check_json_syntax(json_text: str) -> dict:
    """Return whether JSON text is valid and locate any syntax error."""
    try:
        json.loads(json_text)
    except json.JSONDecodeError as exc:
        return {
            "result": False,
            "error_message": exc.msg,
            "error_line": exc.lineno,
            "error_column": exc.colno,
            "error_position": exc.pos,
        }

    return {
        "result": True,
        "error_message": "",
        "error_line": 0,
        "error_column": 0,
        "error_position": 0,
    }


def run(parameters: dict) -> dict:
    """Run the function from a parameter payload."""
    return main(json_text=parameters["json_text"])


def main(json_text: str) -> dict:
    """Run the Function with parameters supplied by anno-function-runner."""
    return check_json_syntax(json_text=json_text)
