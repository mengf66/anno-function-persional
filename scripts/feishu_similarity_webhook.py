#!/usr/bin/env python3
"""HTTP webhook that runs text_similarity_checker for a Feishu Base record."""

from __future__ import annotations

import argparse
import hmac
import importlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
from dataclasses import dataclass
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Mapping, Protocol, Sequence
from urllib.parse import urlsplit


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


INPUT_FIELDS = ("目标文本", "已有文本", "执行状态")
OUTPUT_FIELDS = ("record_id", "查重通过", "最相似文本", "最高相似度", "执行状态")


class WebhookError(RuntimeError):
    def __init__(self, status: HTTPStatus, message: str) -> None:
        self.status = status
        self.message = message
        super().__init__(message)


class LarkCliError(RuntimeError):
    pass


@dataclass(frozen=True)
class SimilarityRequest:
    app_token: str
    table_id: str
    record_id: str

    @classmethod
    def from_payload(cls, payload: object) -> "SimilarityRequest":
        if not isinstance(payload, dict):
            raise WebhookError(HTTPStatus.BAD_REQUEST, "JSON body must be an object")
        values: dict[str, str] = {}
        for key in ("app_token", "table_id", "record_id"):
            value = payload.get(key)
            if not isinstance(value, str) or not value.strip():
                raise WebhookError(HTTPStatus.BAD_REQUEST, f"{key} is required")
            values[key] = value.strip()
        return cls(**values)


class BaseClient(Protocol):
    def get_record(self, request: SimilarityRequest) -> dict[str, Any]: ...

    def update_record(
        self,
        request: SimilarityRequest,
        fields: Mapping[str, Any],
    ) -> None: ...


class LarkBaseClient:
    def __init__(self, executable: str = "lark-cli", identity: str = "user") -> None:
        if identity not in {"user", "bot"}:
            raise ValueError("identity must be user or bot")
        self.executable = executable
        self.identity = identity

    def _run(self, *args: str) -> dict[str, Any]:
        completed = subprocess.run(
            [self.executable, *args],
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
            raise LarkCliError("lark-cli returned invalid JSON") from error
        if not payload.get("ok"):
            raise LarkCliError(f"lark-cli request failed: {payload}")
        return payload

    def get_record(self, request: SimilarityRequest) -> dict[str, Any]:
        args = [
            "base",
            "+record-get",
            "--base-token",
            request.app_token,
            "--table-id",
            request.table_id,
            "--record-id",
            request.record_id,
        ]
        for field in INPUT_FIELDS:
            args.extend(["--field-id", field])
        args.extend(["--format", "json", "--as", self.identity])
        payload = self._run(*args)
        data = payload.get("data", {})
        fields = data.get("fields")
        rows = data.get("data")
        record_ids = data.get("record_id_list")
        if (
            not isinstance(fields, list)
            or not isinstance(rows, list)
            or len(rows) != 1
            or not isinstance(rows[0], list)
            or len(fields) != len(rows[0])
            or record_ids != [request.record_id]
        ):
            raise LarkCliError("unexpected record-get response")
        return dict(zip(fields, rows[0], strict=True))

    def update_record(
        self,
        request: SimilarityRequest,
        fields: Mapping[str, Any],
    ) -> None:
        self._run(
            "base",
            "+record-upsert",
            "--base-token",
            request.app_token,
            "--table-id",
            request.table_id,
            "--record-id",
            request.record_id,
            "--json",
            json.dumps(dict(fields), ensure_ascii=False, separators=(",", ":")),
            "--as",
            self.identity,
        )


def _single_select_name(value: object) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, list) and len(value) == 1 and isinstance(value[0], str):
        return value[0]
    return ""


def _string_list(value: object) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list) and all(isinstance(item, str) for item in value):
        return value
    raise WebhookError(HTTPStatus.UNPROCESSABLE_ENTITY, "已有文本必须是文本列表")


def _run_checker(text_field: str, existing_texts: list[str]) -> dict[str, Any]:
    module = importlib.import_module("function.text_similarity_checker.src.main")
    result = module.main(text_field=text_field, existing_texts=existing_texts)
    if not isinstance(result, dict):
        raise RuntimeError("text_similarity_checker returned a non-object")
    return result


def process_similarity_request(
    client: BaseClient,
    request: SimilarityRequest,
) -> dict[str, Any]:
    """Read a record, execute the Function, and write the result back."""
    try:
        record = client.get_record(request)
        status = _single_select_name(record.get("执行状态"))
        if status == "已完成":
            return {"record_id": request.record_id, "status": "already_completed"}
        if status not in {"待执行", "执行中"}:
            raise WebhookError(
                HTTPStatus.CONFLICT,
                f"执行状态必须是待执行或执行中，当前为 {status or '空'}",
            )
        text_field = record.get("目标文本")
        if not isinstance(text_field, str) or not text_field:
            raise WebhookError(HTTPStatus.UNPROCESSABLE_ENTITY, "目标文本不能为空")
        result = _run_checker(text_field, _string_list(record.get("已有文本")))
        client.update_record(
            request,
            {
                "record_id": request.record_id,
                "查重通过": bool(result["result"]),
                "最相似文本": str(result["sim_text"]),
                "最高相似度": float(result["value"]),
                "执行状态": "已完成",
            },
        )
        return {
            "record_id": request.record_id,
            "status": "completed",
            "result": result,
        }
    except Exception:
        try:
            client.update_record(request, {"执行状态": "失败"})
        except Exception:
            pass
        raise


class SimilarityWebhookHandler(BaseHTTPRequestHandler):
    server: "SimilarityWebhookServer"

    def do_GET(self) -> None:
        if urlsplit(self.path).path != "/healthz":
            self._write_json(HTTPStatus.NOT_FOUND, {"error": "not found"})
            return
        self._write_json(HTTPStatus.OK, {"ok": True})

    def do_POST(self) -> None:
        if urlsplit(self.path).path != "/webhook/text-similarity":
            self._write_json(HTTPStatus.NOT_FOUND, {"error": "not found"})
            return
        token = self.headers.get("X-Webhook-Token", "")
        if not hmac.compare_digest(token, self.server.webhook_token):
            self._write_json(HTTPStatus.UNAUTHORIZED, {"error": "unauthorized"})
            return
        try:
            content_length = int(self.headers.get("Content-Length", "0"))
            if content_length <= 0 or content_length > 64 * 1024:
                raise WebhookError(HTTPStatus.BAD_REQUEST, "invalid content length")
            payload = json.loads(self.rfile.read(content_length))
            request = SimilarityRequest.from_payload(payload)
            result = process_similarity_request(self.server.client, request)
        except WebhookError as error:
            self._write_json(error.status, {"error": error.message})
            return
        except (json.JSONDecodeError, UnicodeDecodeError):
            self._write_json(HTTPStatus.BAD_REQUEST, {"error": "invalid JSON"})
            return
        except Exception as error:
            self.log_error("webhook failed: %s", error)
            self._write_json(HTTPStatus.INTERNAL_SERVER_ERROR, {"error": "execution failed"})
            return
        self._write_json(HTTPStatus.OK, result)

    def _write_json(self, status: HTTPStatus, payload: Mapping[str, Any]) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status.value)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


class SimilarityWebhookServer(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(
        self,
        address: tuple[str, int],
        client: BaseClient,
        webhook_token: str,
    ) -> None:
        self.client = client
        self.webhook_token = webhook_token
        super().__init__(address, SimilarityWebhookHandler)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the Feishu similarity webhook")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--identity", choices=("user", "bot"), default="user")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    webhook_token = os.environ.get("FEISHU_WEBHOOK_TOKEN", "")
    if not webhook_token:
        print("error: FEISHU_WEBHOOK_TOKEN is required", file=sys.stderr)
        return 2
    if shutil.which("lark-cli") is None:
        print("error: lark-cli is not installed or not on PATH", file=sys.stderr)
        return 2
    server = SimilarityWebhookServer(
        (args.host, args.port),
        LarkBaseClient(identity=args.identity),
        webhook_token,
    )
    print(f"listening on http://{args.host}:{args.port}/webhook/text-similarity")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
