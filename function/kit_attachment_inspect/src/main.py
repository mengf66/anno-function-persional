#!/usr/bin/env python3
"""Core-path test: attachment-related binding + static parameters.

Current anno-function does not download Attachment bytes. This function accepts
either:
- empty/None (empty cell)
- a text summary already materialised by runner (e.g. attach_download out)
- a JSON string of the raw attachment list (if upstream serialises it)
"""

from __future__ import annotations

import json
from collections.abc import Mapping


def main(attachment_raw: str | None = None, label: str = "smoke") -> dict:
    raw = attachment_raw
    if raw is None or raw == "":
        return {"count": 0, "names": "", "status": f"ok:{label}:0"}

    # Prefer JSON list of maps; fall back to treating the whole string as one name.
    names: list[str] = []
    try:
        parsed = json.loads(raw)
    except (TypeError, json.JSONDecodeError):
        parsed = None

    if isinstance(parsed, list):
        for item in parsed:
            if isinstance(item, Mapping):
                names.append(str(item.get("name") or "<no-name>"))
            else:
                names.append(str(item))
    else:
        # plain text summary from runner attach download etc.
        names = [raw.strip()] if str(raw).strip() else []

    return {
        "count": len(names),
        "names": ",".join(names),
        "status": f"ok:{label}:{len(names)}",
    }
