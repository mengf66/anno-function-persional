#!/usr/bin/env python3
"""Extract typed fields from a JSON object."""

import json


def extract_json_fields(json_text: str) -> dict:
    """Parse JSON and return its required name and enabled fields."""
    payload = json.loads(json_text)
    if not isinstance(payload, dict):
        raise ValueError("JSON value must be an object")

    name = payload.get("name")
    enabled = payload.get("enabled")
    if not isinstance(name, str):
        raise ValueError("name must be a string")
    if not isinstance(enabled, bool):
        raise ValueError("enabled must be a boolean")

    return {"name": name, "enabled": enabled}


def run(parameters: dict) -> dict:
    """Run the function from a parameter payload."""
    return main(json_text=parameters["json_text"])


def main(json_text: str) -> dict:
    """Run the Function with parameters supplied by anno-function-runner."""
    return extract_json_fields(json_text=json_text)
