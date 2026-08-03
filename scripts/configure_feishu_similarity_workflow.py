#!/usr/bin/env python3
"""Configure the similarity-check workflow on an existing Feishu Base table."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import shutil
import sys
from typing import Sequence

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.create_feishu_similarity_base import (
    LarkCli,
    LarkCliError,
    _required_string,
    build_workflow,
)


def configure_workflow(
    cli: LarkCli,
    *,
    base_token: str,
    table_id: str,
    webhook_url: str,
    webhook_token: str,
    enable: bool,
) -> dict[str, str]:
    payload = cli.run(
        "base",
        "+workflow-create",
        "--base-token",
        base_token,
        "--json",
        json.dumps(
            build_workflow(base_token, table_id, webhook_url, webhook_token),
            ensure_ascii=False,
            separators=(",", ":"),
        ),
        "--as",
        "user",
    )
    workflow_id = _required_string(payload, "data", "workflow_id")
    status = _required_string(payload, "data", "status")
    if enable:
        enabled = cli.run(
            "base",
            "+workflow-enable",
            "--base-token",
            base_token,
            "--workflow-id",
            workflow_id,
            "--as",
            "user",
        )
        status = _required_string(enabled, "data", "status")
    return {"workflow_id": workflow_id, "status": status}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Configure a similarity workflow on an existing Base table."
    )
    parser.add_argument("--base-token", required=True)
    parser.add_argument("--table-id", required=True)
    parser.add_argument("--webhook-url", required=True)
    parser.add_argument("--enable", action="store_true")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if shutil.which("lark-cli") is None:
        print("error: lark-cli is not installed or not on PATH", file=sys.stderr)
        return 2
    webhook_token = os.environ.get("FEISHU_WEBHOOK_TOKEN", "")
    if not webhook_token:
        print("error: FEISHU_WEBHOOK_TOKEN is required", file=sys.stderr)
        return 2
    try:
        result = configure_workflow(
            LarkCli(),
            base_token=args.base_token,
            table_id=args.table_id,
            webhook_url=args.webhook_url,
            webhook_token=webhook_token,
            enable=args.enable,
        )
    except LarkCliError as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
