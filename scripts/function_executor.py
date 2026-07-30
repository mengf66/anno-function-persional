from __future__ import annotations

import argparse
import asyncio
import contextlib
import importlib.util
import inspect
import io
import json
import os
from pathlib import Path
import subprocess
import sys
from typing import Any
from uuid import uuid4

from scripts.function_contract import ContractError, FunctionDefinition, validate_value


PROTOCOL = "ANNO_FUNCTION_VALIDATION:"


class EntrypointError(ValueError):
    def __init__(self, code: str, message: str) -> None:
        self.code = code
        self.message = message
        super().__init__(f"{code}: {message}")


def validate_entrypoint(
    function_dir: Path,
    definition: FunctionDefinition,
    timeout: float = 10,
) -> None:
    payload = {
        "main_path": str((function_dir / "src" / "main.py").resolve()),
        "definition": definition.model_dump(mode="json", by_alias=True),
    }
    repo_root = Path(__file__).resolve().parents[1]
    env = {
        "PATH": os.environ.get("PATH", ""),
        "PYTHONIOENCODING": "utf-8",
        "PYTHONPATH": str(repo_root),
    }
    try:
        completed = subprocess.run(
            [sys.executable, "-m", "scripts.function_executor", "--child"],
            input=json.dumps(payload),
            text=True,
            capture_output=True,
            timeout=timeout,
            cwd=function_dir,
            env=env,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise EntrypointError("entrypoint.timeout", f"exceeded {timeout}s") from exc
    protocol_lines = [
        line.removeprefix(PROTOCOL)
        for line in completed.stdout.splitlines()
        if line.startswith(PROTOCOL)
    ]
    if not protocol_lines:
        detail = completed.stderr.strip() or completed.stdout.strip() or "child exited"
        raise EntrypointError("entrypoint.protocol", detail)
    result = json.loads(protocol_lines[-1])
    if not result["ok"]:
        raise EntrypointError(result["code"], result["message"])
    if completed.returncode != 0:
        raise EntrypointError("entrypoint.child", f"exit code {completed.returncode}")


def _load_main(path: Path):
    spec = importlib.util.spec_from_file_location(f"anno_function_{uuid4().hex}", path)
    if spec is None or spec.loader is None:
        raise EntrypointError("entrypoint.import", f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(module)
    except Exception as exc:
        raise EntrypointError("entrypoint.import", f"{type(exc).__name__}: {exc}") from exc
    entrypoint = getattr(module, "main", None)
    if not callable(entrypoint):
        raise EntrypointError("entrypoint.missing", "src/main.py must define callable main")
    return entrypoint


def _call_example(entrypoint, parameters: dict[str, Any]) -> Any:
    try:
        inspect.signature(entrypoint).bind(**parameters)
    except TypeError as exc:
        raise EntrypointError("entrypoint.signature", str(exc)) from exc
    try:
        result = entrypoint(**parameters)
        if inspect.isawaitable(result):
            result = asyncio.run(result)
        return result
    except EntrypointError:
        raise
    except Exception as exc:
        raise EntrypointError("entrypoint.execution", f"{type(exc).__name__}: {exc}") from exc


def _validate_result(definition: FunctionDefinition, result: object) -> None:
    if not isinstance(result, dict):
        raise EntrypointError("entrypoint.return.type", "main must return a dict")
    fields = {field.key: field for field in definition.returns}
    unknown = sorted(set(result) - set(fields))
    if unknown:
        raise EntrypointError("entrypoint.return.unknown", unknown[0])
    missing = [field.key for field in definition.returns if field.required and field.key not in result]
    if missing:
        raise EntrypointError("entrypoint.return.missing", missing[0])
    for key, value in result.items():
        try:
            validate_value(fields[key], value)
        except ContractError as exc:
            raise EntrypointError("entrypoint.return.type", f"{key}: {exc.message}") from exc


def _child() -> int:
    try:
        payload = json.loads(sys.stdin.read())
        definition = FunctionDefinition.model_validate(payload["definition"])
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            entrypoint = _load_main(Path(payload["main_path"]))
            for example in definition.metadata.examples:
                _validate_result(definition, _call_example(entrypoint, example.parameters))
        response = {"ok": True}
    except EntrypointError as exc:
        response = {"ok": False, "code": exc.code, "message": exc.message}
    except Exception as exc:
        response = {
            "ok": False,
            "code": "entrypoint.internal",
            "message": f"{type(exc).__name__}: {exc}",
        }
    print(PROTOCOL + json.dumps(response, ensure_ascii=False))
    return 0 if response["ok"] else 1


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--child", action="store_true")
    args = parser.parse_args()
    if not args.child:
        parser.error("--child is required")
    return _child()


if __name__ == "__main__":
    raise SystemExit(main())
