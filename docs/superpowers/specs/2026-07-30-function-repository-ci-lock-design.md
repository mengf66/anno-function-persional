# Function Repository CI Lock Design

## Goal

Make every branch and release tag in mengf66/anno-function-persional
machine-verifiable against the Anno Function contract. Invalid changes must not
be mergeable into the release branch, and published version tags must not be
movable or deletable.

The contract source is anno-kit's test branch as inspected on 2026-07-30. This
repository keeps a pinned executable copy so upstream changes cannot
retroactively invalidate an existing Function version.

## Enforcement Model

The lock has three independent layers:

1. GitHub Actions runs strict validation for every branch push, pull request,
   and v* tag.
2. A branch ruleset requires the strict check before changes enter the
   canonical release branch through a pull request.
3. Separate tag rulesets restrict v* creation to the release App and forbid
   tag update and deletion for every actor, including that App.

All branches are validated. Feature branches remain pushable so their first
commit can obtain a CI result; requiring a pre-existing result on every feature
branch update would prevent new branches from being published.

The repository currently has no main branch and uses feat/add-dedup-script as
its default branch. Deployment must first establish one canonical release
branch. The ruleset installer discovers the current default branch unless an
explicit release branch is supplied; it never changes the GitHub default
branch.

## Repository Artifacts

    .github/workflows/function-ci.yml
    .github/workflows/function-release.yml
    scripts/validate_functions.py
    scripts/configure_repository_rules.py
    tests/ci/fixtures/
    tests/ci/test_validate_functions.py

validate_functions.py is the single implementation used locally and in both
workflows. Workflow YAML only installs pinned dependencies and invokes it.

configure_repository_rules.py idempotently reconciles branch and tag rulesets.
It supports dry-run and requires an explicit confirmation flag for writes.

## Strict Function Contract

Every direct child of function/ is one Function. It must contain exactly one
meta.yaml, exactly one src/main.py, and at least one Python test under test/.
Symlinks escaping the repository and committed cache, bytecode, secret, build,
or environment artifacts are rejected.

The metadata validator enforces:

- apiVersion functions.anno.meetchances.com/v1alpha1 and kind Function;
- required metadata, parameter, return, example, and UI fields;
- no unknown keys and unique parameter/return keys;
- Python-safe parameter keys;
- exact scalar types (bool is not int; int is accepted for float);
- array itemType consistency;
- manual/Feishu source and UI constraints;
- UI ranges, steps, precision, selection counts, regex patterns, and exclusive
  option/provider sources;
- defaults and examples against declared rules;
- complete required inputs and outputs with no undeclared values.

The entrypoint validator imports each src/main.py in an isolated subprocess and
requires a top-level callable main. For every metadata example it calls
main(**parameters), awaits async results, and requires a dict whose keys and
values exactly satisfy declared returns. CLI adapters may exist but cannot
replace the platform entrypoint.

The test gate runs every Function test with Python 3.11. A missing test,
collection error, skipped complete suite, warning promoted to error, non-zero
exit, or contract mismatch fails the check. Errors include Function-relative
paths and stable codes.

## Workflows

function-ci.yml triggers on every branch push and pull request. It checks out
the exact event SHA, uses Python 3.11, installs pinned dependencies, runs
validator tests, validates all Functions, and runs all Function tests. The job
and check name remain stable for the branch ruleset. Permissions are read-only
and superseded runs on the same ref are cancelled.

function-release.yml is manually dispatched with a version and release commit.
It validates before creating anything, then uses the sole tag-authorized GitHub
App identity to create the tag. A tag-push audit job repeats complete CI at the
created tag commit. The release workflow verifies:

- the tag is v followed by a positive integer and exceeds existing versions;
- the tag resolves directly to a commit;
- the commit is reachable from the configured release branch;
- that commit has a successful strict CI check;
- the tag name does not already exist locally or remotely.

The workflow may create one new annotated tag after all gates pass. It never
moves or deletes tags. Direct user and administrator tag creation is denied by
the ruleset; if no dedicated GitHub App credential is configured, release
aborts instead of weakening the rule.

## GitHub Rulesets

The installer reconciles named rulesets without replacing unrelated settings.
The release-branch ruleset targets only the configured canonical branch,
requires pull requests and the stable strict CI check, requires branches to be
current, and blocks force pushes and deletion. It creates no broad bypass.

The creation ruleset targets refs/tags/v*, blocks creation, and grants its only
bypass to the dedicated release GitHub App. A separate immutable ruleset blocks
update and deletion with no bypass actors. Splitting these rules is required
because a GitHub ruleset bypass applies to every rule in that ruleset.

Dry-run prints the exact desired/current diff. The installer aborts on missing
admin scope, unsupported repository features, an unknown release branch, or
ambiguous existing rulesets.

## Error Handling And Security

- Validation is fail-closed for unreadable YAML, invalid UTF-8, import failure,
  timeout, or subprocess failure.
- Example execution has a timeout, temporary working directory, minimal
  environment, no repository credentials, and captured output.
- Workflow permissions default to contents read; ruleset writes are a separate
  explicit administrative operation.
- GitHub actions are pinned to immutable commit SHAs.
- Workflows execute no code fetched from anno-kit or another mutable branch.
- Existing user changes and tags are never rewritten.

## Test Strategy

Fixture-driven tests start with failing cases for the current CLI-style
main() incompatibility; bad layout; missing tests; malformed, unknown,
duplicate, or inconsistent metadata; bool/int confusion; invalid arrays,
defaults, UI rules, and examples; missing, extra, mistyped, synchronous, and
asynchronous returns; import failure; timeout; and failing tests.

Workflow syntax is checked locally. The ruleset reconciler is tested against
recorded API-shaped fixtures in dry-run mode before any live write.

## Acceptance Criteria

- Every branch push and pull request produces the same strict CI check.
- Both current Functions fail for the known CLI entrypoint incompatibility
  until main(**parameters) is corrected.
- Valid synchronous and asynchronous fixtures pass end to end.
- Invalid metadata, code, example output, or tests fail with a precise path and
  reason.
- The canonical release branch cannot merge without the strict check.
- A v* tag can only be created by the post-validation release workflow, cannot
  be moved or deleted, and cannot reference an off-branch commit.
- Re-running ruleset configuration is idempotent and leaves unrelated settings
  unchanged.
