#!/usr/bin/env python3
"""Create a Feishu Base and workflow for text similarity checks."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import uuid
from dataclasses import dataclass
from typing import Any, Sequence


TABLE_NAME = "Function查重测试"

TABLE_FIELDS = [
    {
        "name": "record_id",
        "type": "text",
        "description": "飞书记录 ID，供 anno-kit 定位和回写记录",
    },
    {
        "name": "目标文本",
        "type": "text",
        "description": "绑定 text_field",
    },
    {
        "name": "执行状态",
        "type": "select",
        "multiple": False,
        "options": [
            {"name": "待执行", "hue": "Blue", "lightness": "Lighter"},
            {"name": "执行中", "hue": "Orange", "lightness": "Lighter"},
            {"name": "已完成", "hue": "Green", "lightness": "Lighter"},
            {"name": "失败", "hue": "Red", "lightness": "Lighter"},
        ],
    },
    {
        "name": "最相似文本",
        "type": "text",
        "description": "绑定 sim_text",
    },
    {
        "name": "查重通过",
        "type": "checkbox",
        "description": "绑定 result；勾选表示未发现超过阈值的相似文本",
    },
    {
        "name": "最高相似度",
        "type": "number",
        "description": "绑定 value",
        "style": {
            "type": "plain",
            "precision": 4,
            "percentage": False,
            "thousands_separator": False,
        },
    },
    {
        "name": "用例名称",
        "type": "text",
        "description": "Function 查重测试用例标识",
    },
    {
        "name": "已有文本",
        "type": "select",
        "multiple": True,
        "description": "绑定 existing_texts",
        "options": [
            {
                "name": "Python makes data processing very easy",
                "hue": "Lime",
                "lightness": "Lighter",
            },
            {
                "name": "The weather is sunny today",
                "hue": "Carmine",
                "lightness": "Lighter",
            },
            {
                "name": "飞书多维表格支持自动化工作流",
                "hue": "Gray",
                "lightness": "Lighter",
            },
            {
                "name": "今天天气晴朗，适合散步",
                "hue": "Purple",
                "lightness": "Lighter",
            },
        ],
    },
]


class LarkCliError(RuntimeError):
    """Raised when lark-cli fails or returns an unexpected response."""


@dataclass(frozen=True)
class CreatedBase:
    base_token: str
    base_url: str
    table_id: str
    workflow_id: str
    workflow_status: str


class LarkCli:
    def __init__(self, executable: str = "lark-cli", dry_run: bool = False) -> None:
        self.executable = executable
        self.dry_run = dry_run

    def run(self, *args: str) -> dict[str, Any]:
        command = [self.executable, *args]
        if self.dry_run:
            print("DRY RUN:", " ".join(_shell_quote(part) for part in command))
            return {}

        completed = subprocess.run(
            command,
            check=False,
            text=True,
            capture_output=True,
        )
        if completed.returncode != 0:
            detail = completed.stderr.strip() or completed.stdout.strip()
            raise LarkCliError(f"lark-cli failed ({completed.returncode}): {detail}")

        try:
            payload = json.loads(completed.stdout)
        except json.JSONDecodeError as error:
            raise LarkCliError(
                f"lark-cli returned invalid JSON: {completed.stdout.strip()}"
            ) from error
        if not payload.get("ok"):
            raise LarkCliError(f"lark-cli request failed: {payload}")
        return payload


def _shell_quote(value: str) -> str:
    if value and all(character.isalnum() or character in "-._/:" for character in value):
        return value
    return "'" + value.replace("'", "'\"'\"'") + "'"


def _required_string(payload: dict[str, Any], *path: str) -> str:
    current: Any = payload
    for key in path:
        if not isinstance(current, dict) or key not in current:
            raise LarkCliError(f"missing response field: {'.'.join(path)}")
        current = current[key]
    if not isinstance(current, str) or not current:
        raise LarkCliError(f"invalid response field: {'.'.join(path)}")
    return current


def build_workflow(
    base_token: str,
    table_id: str,
    webhook_url: str,
    webhook_token: str,
) -> dict[str, Any]:
    """Build the workflow body using the new Base and table identifiers."""
    trigger_id = "trigger_pending_similarity_check"
    return {
        "client_token": uuid.uuid4().hex,
        "title": "执行状态=待执行时调用文本查重 Function",
        "steps": [
            {
                "id": trigger_id,
                "type": "SetRecordTrigger",
                "title": "执行状态变为待执行",
                "next": "mark_similarity_check_running",
                "data": {
                    "table_name": TABLE_NAME,
                    "field_watch_info": [
                        {
                            "field_name": "执行状态",
                            "operator": "is",
                            "value": [
                                {
                                    "value_type": "option",
                                    "value": {"name": "待执行"},
                                }
                            ],
                        }
                    ],
                    "trigger_control_list": [
                        "pasteUpdate",
                        "automationBatchUpdate",
                        "appendImport",
                        "openAPIBatchUpdate",
                    ],
                },
            },
            {
                "id": "mark_similarity_check_running",
                "type": "SetRecordAction",
                "title": "标记查重执行中",
                "next": "post_similarity_check",
                "data": {
                    "table_name": TABLE_NAME,
                    "max_set_record_num": 1,
                    "ref_info": {"step_id": trigger_id},
                    "field_values": [
                        {
                            "field_name": "执行状态",
                            "value": [
                                {
                                    "value_type": "option",
                                    "value": {"name": "执行中"},
                                }
                            ],
                        }
                    ],
                },
            },
            {
                "id": "post_similarity_check",
                "type": "HTTPClientAction",
                "title": "POST 到文本查重 webhook",
                "next": None,
                "data": {
                    "method": "POST",
                    "url": [{"value_type": "text", "value": webhook_url}],
                    "headers": [
                        {
                            "key": "Content-Type",
                            "value": [
                                {
                                    "value_type": "text",
                                    "value": "application/json",
                                }
                            ],
                        },
                        {
                            "key": "X-Webhook-Token",
                            "value": [
                                {
                                    "value_type": "text",
                                    "value": webhook_token,
                                }
                            ],
                        },
                    ],
                    "queries": [],
                    "body_type": "raw",
                    "raw_body": [
                        {
                            "value_type": "text",
                            "value": json.dumps(
                                {
                                    "app_token": base_token,
                                    "table_id": table_id,
                                },
                                ensure_ascii=False,
                                separators=(",", ":"),
                            )[:-1]
                            + ',"record_id":"',
                        },
                        {
                            "value_type": "ref",
                            "value": f"$.{trigger_id}.recordId",
                        },
                        {"value_type": "text", "value": '"}'},
                    ],
                    "response_type": "json",
                    "response_value": "{}",
                },
            },
        ],
    }


def create_similarity_base(
    cli: LarkCli,
    *,
    base_name: str,
    webhook_url: str,
    webhook_token: str,
    folder_token: str | None = None,
    enable_workflow: bool = False,
) -> CreatedBase | None:
    base_args = ["base", "+base-create", "--name", base_name, "--time-zone", "Asia/Shanghai"]
    if folder_token:
        base_args.extend(["--folder-token", folder_token])
    base_payload = cli.run(*base_args)
    if cli.dry_run:
        print("DRY RUN: later commands require the base/table IDs returned by Feishu")
        return None

    base_token = _required_string(base_payload, "data", "base", "base_token")
    base_url = _required_string(base_payload, "data", "base", "url")

    table_payload = cli.run(
        "base",
        "+table-create",
        "--base-token",
        base_token,
        "--name",
        TABLE_NAME,
        "--fields",
        json.dumps(TABLE_FIELDS, ensure_ascii=False, separators=(",", ":")),
        "--view",
        json.dumps([{"name": "Grid View", "type": "grid"}], ensure_ascii=False),
    )
    table = table_payload.get("data", {}).get("table", {})
    table_id = table.get("table_id") or table.get("id")
    if not isinstance(table_id, str) or not table_id:
        raise LarkCliError("missing response field: data.table.table_id")

    workflow_payload = cli.run(
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
    )
    workflow_id = _required_string(workflow_payload, "data", "workflow_id")
    workflow_status = _required_string(workflow_payload, "data", "status")

    if enable_workflow:
        enabled_payload = cli.run(
            "base",
            "+workflow-enable",
            "--base-token",
            base_token,
            "--workflow-id",
            workflow_id,
        )
        workflow_status = _required_string(enabled_payload, "data", "status")

    return CreatedBase(
        base_token=base_token,
        base_url=base_url,
        table_id=table_id,
        workflow_id=workflow_id,
        workflow_status=workflow_status,
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Create a new Feishu Base for text-similarity Function tests."
    )
    parser.add_argument(
        "--name",
        default="Function查重测试",
        help="new Base name (default: %(default)s)",
    )
    parser.add_argument(
        "--webhook-url",
        required=True,
        help="HTTP endpoint invoked by the Feishu workflow",
    )
    parser.add_argument("--folder-token", help="optional Feishu Drive folder token")
    parser.add_argument(
        "--enable-workflow",
        action="store_true",
        help="enable the workflow after creation (disabled by default)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="print the first command without changing Feishu",
    )
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
        result = create_similarity_base(
            LarkCli(dry_run=args.dry_run),
            base_name=args.name,
            webhook_url=args.webhook_url,
            webhook_token=webhook_token,
            folder_token=args.folder_token,
            enable_workflow=args.enable_workflow,
        )
    except LarkCliError as error:
        print(f"error: {error}", file=sys.stderr)
        return 1

    if result is None:
        return 0
    print(
        json.dumps(
            {
                "base_token": result.base_token,
                "base_url": result.base_url,
                "table_id": result.table_id,
                "workflow_id": result.workflow_id,
                "workflow_status": result.workflow_status,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
