from __future__ import annotations

import argparse
from dataclasses import dataclass
import json
import os
import re
from typing import Any
from urllib.error import HTTPError
from urllib.parse import quote
from urllib.request import Request, urlopen


CHECK_NAME = "Function CI / strict"
CHECK_RUN_NAME = "strict"


class ReleaseError(ValueError):
    def __init__(self, code: str, message: str) -> None:
        self.code = code
        super().__init__(f"{code}: {message}")


@dataclass(frozen=True)
class ReleaseDecision:
    version: str
    commit_sha: str
    release_branch: str


def validate_release(
    version: str,
    commit_sha: str,
    release_branch: str,
    client,
    *,
    create: bool = False,
) -> ReleaseDecision:
    match = re.fullmatch(r"v([1-9][0-9]*)", version)
    if match is None:
        raise ReleaseError("version.invalid", "expected v followed by a positive integer")
    if re.fullmatch(r"[0-9a-f]{40}", commit_sha) is None:
        raise ReleaseError("commit.invalid", "expected a full lowercase commit SHA")
    tags = client.list_tags()
    if version in tags:
        raise ReleaseError("tag.exists", version)
    numeric_versions = [
        int(found.group(1))
        for tag in tags
        if (found := re.fullmatch(r"v([1-9][0-9]*)", tag))
    ]
    if numeric_versions and int(match.group(1)) <= max(numeric_versions):
        raise ReleaseError("version.not_increasing", f"latest is v{max(numeric_versions)}")
    if not release_branch.strip():
        raise ReleaseError("branch.invalid", "release branch is required")
    if not client.is_reachable(release_branch, commit_sha):
        raise ReleaseError("commit.off_branch", release_branch)
    if not client.has_successful_check(commit_sha, CHECK_RUN_NAME):
        raise ReleaseError("check.missing", f"{CHECK_NAME} is not successful for {commit_sha}")
    decision = ReleaseDecision(version, commit_sha, release_branch)
    if create:
        client.create_annotated_tag(version, commit_sha)
    return decision


class GitHubClient:
    def __init__(self, repository: str, token: str) -> None:
        if re.fullmatch(r"[^/]+/[^/]+", repository) is None:
            raise ReleaseError("repository.invalid", repository)
        if not token:
            raise ReleaseError("token.missing", "GH_TOKEN is required")
        self.repository = repository
        self.token = token

    def _request(self, method: str, path: str, payload: dict[str, Any] | None = None):
        request = Request(
            f"https://api.github.com/repos/{self.repository}/{path}",
            method=method,
            data=None if payload is None else json.dumps(payload).encode(),
            headers={
                "Accept": "application/vnd.github+json",
                "Authorization": f"Bearer {self.token}",
                "Content-Type": "application/json",
                "X-GitHub-Api-Version": "2022-11-28",
            },
        )
        try:
            with urlopen(request, timeout=20) as response:
                return json.load(response)
        except HTTPError as exc:
            detail = exc.read().decode(errors="replace")
            raise ReleaseError("github.api", f"{exc.code} {path}: {detail}") from exc

    def list_tags(self) -> dict[str, str]:
        tags: dict[str, str] = {}
        page = 1
        while True:
            items = self._request("GET", f"git/matching-refs/tags/?per_page=100&page={page}")
            if not isinstance(items, list):
                raise ReleaseError("github.response", "tag refs must be a list")
            for item in items:
                ref = item.get("ref", "")
                sha = item.get("object", {}).get("sha", "")
                if not ref.startswith("refs/tags/") or not isinstance(sha, str):
                    raise ReleaseError("github.response", "invalid tag ref")
                tags[ref.removeprefix("refs/tags/")] = sha
            if len(items) < 100:
                return tags
            page += 1

    def is_reachable(self, branch: str, sha: str) -> bool:
        result = self._request("GET", f"compare/{quote(sha, safe='')}...{quote(branch, safe='')}")
        return result.get("status") in {"ahead", "identical"}

    def has_successful_check(self, sha: str, name: str) -> bool:
        result = self._request("GET", f"commits/{sha}/check-runs?per_page=100")
        checks = [
            check
            for check in result.get("check_runs", [])
            if check.get("name") == name
        ]
        return len(checks) == 1 and checks[0].get("conclusion") == "success"

    def create_annotated_tag(self, version: str, sha: str) -> None:
        tag = self._request(
            "POST",
            "git/tags",
            {
                "tag": version,
                "message": f"Validated Anno Function release {version}",
                "object": sha,
                "type": "commit",
            },
        )
        tag_sha = tag.get("sha")
        if not isinstance(tag_sha, str):
            raise ReleaseError("github.response", "tag object SHA missing")
        self._request("POST", "git/refs", {"ref": f"refs/tags/{version}", "sha": tag_sha})


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository", default=os.getenv("GITHUB_REPOSITORY", ""))
    parser.add_argument("--version", required=True)
    parser.add_argument("--commit-sha", required=True)
    parser.add_argument("--release-branch", required=True)
    parser.add_argument("--create", action="store_true")
    args = parser.parse_args()
    client = GitHubClient(args.repository, os.getenv("GH_TOKEN", ""))
    decision = validate_release(
        args.version,
        args.commit_sha,
        args.release_branch,
        client,
        create=args.create,
    )
    action = "created" if args.create else "validated"
    print(f"{action} {decision.version} at {decision.commit_sha}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
