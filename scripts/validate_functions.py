from __future__ import annotations

import argparse
from dataclasses import dataclass
import os
from pathlib import Path
import subprocess
import sys

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from scripts.function_contract import ContractError, parse_definition
from scripts.function_executor import EntrypointError, validate_entrypoint


FORBIDDEN_NAMES = {
    ".env",
    ".venv",
    "__pycache__",
    "build",
    "credentials",
    "dist",
}
FORBIDDEN_SUFFIXES = {".pyc", ".pyo", ".pem", ".key"}


@dataclass(frozen=True, order=True)
class Finding:
    path: str
    code: str
    message: str

    def __str__(self) -> str:
        return f"{self.path}: [{self.code}] {self.message}"


def discover_functions(root: Path) -> list[Path]:
    function_root = root / "function"
    if not function_root.is_dir():
        return []
    return sorted(path for path in function_root.iterdir() if path.is_dir())


def validate_repository(root: Path, run_tests: bool = True) -> list[Finding]:
    root = root.resolve()
    functions = discover_functions(root)
    if not functions:
        return [Finding("function", "layout.root.empty", "no Functions found")]
    findings: list[Finding] = []
    for function_dir in functions:
        findings.extend(_validate_function(root, function_dir, run_tests))
    return sorted(findings)


def _validate_function(root: Path, function_dir: Path, run_tests: bool) -> list[Finding]:
    relative = function_dir.relative_to(root).as_posix()
    findings = _validate_layout(root, function_dir)
    meta_path = function_dir / "meta.yaml"
    main_path = function_dir / "src" / "main.py"
    definition = None
    if meta_path.is_file():
        try:
            definition = parse_definition(meta_path.read_text(encoding="utf-8"))
        except UnicodeDecodeError as exc:
            findings.append(Finding(f"{relative}/meta.yaml", "metadata.utf8", str(exc)))
        except ContractError as exc:
            findings.append(Finding(f"{relative}/meta.yaml", exc.code, f"{exc.path}: {exc.message}"))
    if definition is not None and main_path.is_file():
        try:
            main_path.read_text(encoding="utf-8")
            validate_entrypoint(function_dir, definition)
        except UnicodeDecodeError as exc:
            findings.append(Finding(f"{relative}/src/main.py", "entrypoint.utf8", str(exc)))
        except EntrypointError as exc:
            findings.append(Finding(f"{relative}/src/main.py", exc.code, exc.message))
    if run_tests and (function_dir / "test").is_dir():
        finding = _run_tests(root, function_dir)
        if finding is not None:
            findings.append(finding)
    return findings


def _validate_layout(root: Path, function_dir: Path) -> list[Finding]:
    relative = function_dir.relative_to(root).as_posix()
    findings: list[Finding] = []
    for required, code in (
        (function_dir / "meta.yaml", "layout.meta.missing"),
        (function_dir / "src" / "main.py", "layout.main.missing"),
    ):
        if not required.is_file():
            findings.append(Finding(required.relative_to(root).as_posix(), code, "required file missing"))
    test_dir = function_dir / "test"
    if not test_dir.is_dir() or not any(test_dir.glob("test*.py")):
        findings.append(Finding(f"{relative}/test", "layout.test.missing", "at least one test*.py is required"))
    for path in _repository_paths(root, function_dir):
        path_relative = path.relative_to(root).as_posix()
        if path.is_symlink():
            try:
                path.resolve().relative_to(root)
            except ValueError:
                findings.append(Finding(path_relative, "layout.symlink.escape", "symlink escapes repository"))
        if path.name in FORBIDDEN_NAMES or path.suffix in FORBIDDEN_SUFFIXES:
            findings.append(Finding(path_relative, "layout.artifact.forbidden", path.name))
    return findings


def _repository_paths(root: Path, function_dir: Path) -> list[Path]:
    if (root / ".git").exists():
        completed = subprocess.run(
            ["git", "ls-files", "-z", "--", function_dir.relative_to(root).as_posix()],
            cwd=root,
            capture_output=True,
            check=False,
        )
        if completed.returncode == 0:
            return [root / item.decode() for item in completed.stdout.split(b"\0") if item]
    return list(function_dir.rglob("*"))


def _run_tests(root: Path, function_dir: Path) -> Finding | None:
    relative = function_dir.relative_to(root).as_posix()
    env = os.environ.copy()
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    try:
        completed = subprocess.run(
            [
                sys.executable,
                "-W",
                "error",
                "-m",
                "unittest",
                "discover",
                "-s",
                str(function_dir / "test"),
                "-p",
                "test*.py",
                "-v",
            ],
            cwd=root,
            text=True,
            capture_output=True,
            timeout=60,
            env=env,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return Finding(f"{relative}/test", "test.timeout", "exceeded 60s")
    output = (completed.stdout + completed.stderr).strip()
    if completed.returncode != 0:
        return Finding(f"{relative}/test", "test.failed", output)
    if "Ran 0 tests" in output:
        return Finding(f"{relative}/test", "test.empty", "no tests discovered")
    return None


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--no-tests", action="store_true")
    args = parser.parse_args()
    findings = validate_repository(args.root, run_tests=not args.no_tests)
    if findings:
        for finding in findings:
            print(f"::error file={finding.path}::{finding.code}: {finding.message}")
        print(f"Function validation failed with {len(findings)} finding(s)")
        return 1
    print(f"Function validation passed for {len(discover_functions(args.root.resolve()))} Function(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
