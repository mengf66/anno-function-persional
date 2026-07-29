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


MANAGED_NAMES = {
    "anno-function-release-branch",
    "anno-function-version-creation",
    "anno-function-version-immutable",
}


class RuleError(ValueError):
    def __init__(self, code: str, message: str) -> None:
        self.code = code
        super().__init__(f"{code}: {message}")


@dataclass(frozen=True)
class ChangeSet:
    create: list[dict[str, Any]]
    update: list[tuple[int, dict[str, Any]]]
    unchanged: list[str]


def desired_rulesets(release_branch: str, app_integration_id: int) -> list[dict[str, Any]]:
    if not release_branch.strip() or release_branch.startswith("refs/"):
        raise RuleError("branch.invalid", release_branch)
    if app_integration_id <= 0:
        raise RuleError("app.invalid", "positive integration ID required")
    tag_condition = {
        "ref_name": {"include": ["refs/tags/v*"], "exclude": []},
    }
    return [
        {
            "name": "anno-function-release-branch",
            "target": "branch",
            "enforcement": "active",
            "bypass_actors": [],
            "conditions": {
                "ref_name": {
                    "include": [f"refs/heads/{release_branch}"],
                    "exclude": [],
                }
            },
            "rules": [
                {"type": "deletion"},
                {"type": "non_fast_forward"},
                {
                    "type": "pull_request",
                    "parameters": {
                        "dismiss_stale_reviews_on_push": True,
                        "require_code_owner_review": False,
                        "require_last_push_approval": False,
                        "required_approving_review_count": 0,
                        "required_review_thread_resolution": True,
                    },
                },
                {
                    "type": "required_status_checks",
                    "parameters": {
                        "do_not_enforce_on_create": False,
                        "required_status_checks": [{"context": "Function CI / strict"}],
                        "strict_required_status_checks_policy": True,
                    },
                },
            ],
        },
        {
            "name": "anno-function-version-creation",
            "target": "tag",
            "enforcement": "active",
            "bypass_actors": [
                {
                    "actor_id": app_integration_id,
                    "actor_type": "Integration",
                    "bypass_mode": "always",
                }
            ],
            "conditions": tag_condition,
            "rules": [{"type": "creation"}],
        },
        {
            "name": "anno-function-version-immutable",
            "target": "tag",
            "enforcement": "active",
            "bypass_actors": [],
            "conditions": tag_condition,
            "rules": [{"type": "deletion"}, {"type": "update"}],
        },
    ]


def _normalized(rule: dict[str, Any]) -> dict[str, Any]:
    return {
        key: rule[key]
        for key in ("name", "target", "enforcement", "bypass_actors", "conditions", "rules")
        if key in rule
    }


def reconcile(current: list[dict[str, Any]], desired: list[dict[str, Any]]) -> ChangeSet:
    managed: dict[str, list[dict[str, Any]]] = {}
    for rule in current:
        if rule.get("name") in MANAGED_NAMES:
            managed.setdefault(rule["name"], []).append(rule)
    duplicate = next((name for name, items in managed.items() if len(items) != 1), None)
    if duplicate is not None:
        raise RuleError("ruleset.ambiguous", duplicate)
    create: list[dict[str, Any]] = []
    update: list[tuple[int, dict[str, Any]]] = []
    unchanged: list[str] = []
    for wanted in desired:
        existing = managed.get(wanted["name"])
        if not existing:
            create.append(wanted)
            continue
        rule = existing[0]
        identifier = rule.get("id")
        if not isinstance(identifier, int):
            raise RuleError("ruleset.id.invalid", wanted["name"])
        if _normalized(rule) == wanted:
            unchanged.append(wanted["name"])
        else:
            update.append((identifier, wanted))
    return ChangeSet(create, update, unchanged)


class GitHubRulesClient:
    def __init__(self, repository: str, token: str) -> None:
        if re.fullmatch(r"[^/]+/[^/]+", repository) is None:
            raise RuleError("repository.invalid", repository)
        if not token:
            raise RuleError("token.missing", "GH_TOKEN is required")
        self.repository = repository
        self.token = token

    def request(self, method: str, path: str, payload: dict[str, Any] | None = None):
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
            raise RuleError("github.api", f"{exc.code} {path}: {detail}") from exc

    def assert_branch_exists(self, branch: str) -> None:
        self.request("GET", f"branches/{quote(branch, safe='')}")

    def get_rulesets(self) -> list[dict[str, Any]]:
        summaries = self.request("GET", "rulesets?per_page=100")
        if not isinstance(summaries, list):
            raise RuleError("github.response", "rulesets must be a list")
        details = []
        for summary in summaries:
            identifier = summary.get("id")
            if not isinstance(identifier, int):
                raise RuleError("github.response", "ruleset id missing")
            details.append(self.request("GET", f"rulesets/{identifier}"))
        return details

    def apply(self, changes: ChangeSet) -> None:
        for payload in changes.create:
            self.request("POST", "rulesets", payload)
        for identifier, payload in changes.update:
            self.request("PUT", f"rulesets/{identifier}", payload)


def _print_changes(changes: ChangeSet) -> None:
    output = {
        "create": [item["name"] for item in changes.create],
        "update": [item["name"] for _, item in changes.update],
        "unchanged": changes.unchanged,
    }
    print(json.dumps(output, indent=2, sort_keys=True))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository", required=True)
    parser.add_argument("--release-branch", required=True)
    parser.add_argument("--app-integration-id", type=int, required=True)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    client = GitHubRulesClient(args.repository, os.getenv("GH_TOKEN", ""))
    client.assert_branch_exists(args.release_branch)
    desired = desired_rulesets(args.release_branch, args.app_integration_id)
    changes = reconcile(client.get_rulesets(), desired)
    _print_changes(changes)
    if args.apply:
        client.apply(changes)
        remaining = reconcile(client.get_rulesets(), desired)
        if remaining.create or remaining.update:
            raise RuleError("ruleset.verify.failed", "read-back differs from desired state")
        print("rulesets applied and verified")
    else:
        print("dry-run only; pass --apply to write")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
