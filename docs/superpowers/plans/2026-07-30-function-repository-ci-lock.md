# Function Repository CI Lock Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Enforce the pinned Anno Function contract on every branch and make v* releases validated, authorized, and immutable.

**Architecture:** A local Python validator is the sole contract implementation used by tests and GitHub Actions. One workflow validates every commit, a separate workflow validates before creating an annotated tag through a dedicated GitHub App, and an idempotent ruleset reconciler applies the server-side branch and tag locks.

**Tech Stack:** Python 3.11, Pydantic 2, PyYAML, unittest, subprocess, GitHub Actions, GitHub REST API

## Global Constraints

- Pin the contract to anno-kit origin/test as inspected on 2026-07-30; never execute mutable upstream code.
- Validate every branch push and pull request.
- Require src/main.py to expose callable main(**parameters), including async support.
- Treat bool as distinct from int and allow int where float is declared.
- Fail closed on invalid UTF-8, YAML, imports, timeouts, tests, and GitHub API ambiguity.
- Use read-only workflow permissions except the isolated release job.
- Pin third-party GitHub Actions to full commit SHAs.
- Never move or delete an existing tag.
- Never modify unrelated repository rulesets.

---

### Task 1: Pinned Metadata Contract

**Files:**
- Create: scripts/function_contract.py
- Create: tests/ci/test_function_contract.py
- Create: tests/ci/fixtures/valid/meta.yaml

**Interfaces:**
- Produces: parse_definition(raw: str) -> FunctionDefinition
- Produces: validate_value(field: Field, value: object) -> None
- Produces: ContractError with stable code, path, and message

- [ ] **Step 1: Write failing contract tests**

Add table-driven unittest cases for a complete valid definition and mutations
covering unknown keys, duplicate parameter/return keys, invalid Python keys,
bool-as-int, array itemType, manual UI requirements, Feishu UI rejection,
range bounds, regex compilation, defaults, and complete examples.

The core test shape is:

~~~python
def test_bool_is_not_accepted_as_int(self):
    raw = valid_yaml().replace("default: 3", "default: true")
    with self.assertRaisesRegex(ContractError, "parameter.default.type"):
        parse_definition(raw)
~~~

- [ ] **Step 2: Verify RED**

Run: python3 -m unittest tests.ci.test_function_contract -v

Expected: import failure because scripts.function_contract does not exist.

- [ ] **Step 3: Implement the pinned schema**

Define strict Pydantic models for Header, FunctionMetadata, ParameterField,
ReturnField, FunctionExample, and discriminated UI models. Set extra="forbid",
populate_by_name=True, and camelCase aliases. Port the observable validation
rules from anno-kit's definition_contract.py, rule_compilers.py, and
value_validators.py into focused functions in scripts/function_contract.py.

ContractError must render as:

~~~text
<code> at <path>: <message>
~~~

- [ ] **Step 4: Verify GREEN**

Run: python3 -m unittest tests.ci.test_function_contract -v

Expected: all contract tests pass with no warnings.

- [ ] **Step 5: Commit**

Run:

~~~bash
git add scripts/function_contract.py tests/ci
git commit -m "feat(ci): add pinned Function metadata contract"
~~~

### Task 2: Isolated Entrypoint Execution

**Files:**
- Create: scripts/function_executor.py
- Create: tests/ci/test_function_executor.py
- Create: tests/ci/fixtures/valid/src/main.py

**Interfaces:**
- Consumes: FunctionDefinition from Task 1
- Produces: validate_entrypoint(function_dir: Path, definition: FunctionDefinition, timeout: float = 10) -> None

- [ ] **Step 1: Write failing execution tests**

Create fixtures and tests for sync main, async main, missing main, current
CLI-style main() signature, import exception, timeout, printed output, non-dict
return, missing/extra keys, bool/int confusion, and invalid array items.

Use the actual failure that exists in the repository:

~~~python
def test_rejects_cli_main_without_declared_parameters(self):
    write_main("def main(): return 0")
    with self.assertRaisesRegex(ValidationError, "entrypoint.signature"):
        validate_entrypoint(function_dir, definition)
~~~

- [ ] **Step 2: Verify RED**

Run: python3 -m unittest tests.ci.test_function_executor -v

Expected: import failure because scripts.function_executor does not exist.

- [ ] **Step 3: Implement the subprocess protocol**

Implement a parent validator and a private child mode in the same module. The
parent serializes the function path plus every metadata example, starts
sys.executable with a minimal allowlisted environment and temporary cwd,
captures stdout/stderr, and enforces the timeout. The child imports src/main.py,
binds each example with inspect.signature(main).bind(**parameters), calls it,
awaits awaitables with asyncio.run, and returns JSON through one protocol line.

Reject any returned value not matching the pinned definition. Captured user
stdout is diagnostic only and must not corrupt the protocol.

- [ ] **Step 4: Verify GREEN**

Run: python3 -m unittest tests.ci.test_function_executor -v

Expected: all execution tests pass; timeout fixture completes within 12 seconds.

- [ ] **Step 5: Commit**

Run:

~~~bash
git add scripts/function_executor.py tests/ci
git commit -m "feat(ci): validate Function entrypoints in isolation"
~~~

### Task 3: Repository Validator And Test Gate

**Files:**
- Create: scripts/validate_functions.py
- Create: tests/ci/test_validate_functions.py

**Interfaces:**
- Consumes: parse_definition and validate_entrypoint
- Produces: discover_functions(root: Path) -> list[Path]
- Produces: validate_repository(root: Path, run_tests: bool = True) -> list[Finding]
- CLI exit 0 on success and 1 on any finding

- [ ] **Step 1: Write failing repository tests**

Test missing function/, nested Function directories, missing required files,
missing tests, escaping symlinks, forbidden artifacts, invalid UTF-8, stable
sorted findings, one failing Function test, and a valid multi-Function tree.

- [ ] **Step 2: Verify RED**

Run: python3 -m unittest tests.ci.test_validate_functions -v

Expected: import failure because scripts.validate_functions does not exist.

- [ ] **Step 3: Implement discovery and orchestration**

Discover only direct directories under function/. Reject .pyc, __pycache__,
.env, credentials, build, dist, and symlinks resolving outside root. Read files
as strict UTF-8, aggregate deterministic findings across all Functions, then
run each test directory with:

~~~python
[sys.executable, "-W", "error", "-m", "unittest", "discover",
 "-s", str(function_dir / "test"), "-p", "test*.py", "-v"]
~~~

Require at least one discovered test and enforce a per-Function timeout.

- [ ] **Step 4: Verify GREEN and CLI behavior**

Run:

~~~bash
python3 -m unittest discover -s tests/ci -p "test_*.py" -v
python3 scripts/validate_functions.py --root tests/ci/fixtures/valid
~~~

Expected: tests pass and validator prints a success summary.

- [ ] **Step 5: Commit**

Run:

~~~bash
git add scripts/validate_functions.py tests/ci
git commit -m "feat(ci): add strict repository validation gate"
~~~

### Task 4: Correct Existing Function Runtime Contracts

**Files:**
- Modify: function/text_similarity_checker/test/test.py
- Modify: function/text_similarity_checker/src/main.py
- Modify: function/text_quality_analyzer/test/test.py
- Modify: function/text_quality_analyzer/src/main.py

**Interfaces:**
- Produces: main(text_field: str, existing_texts: list[str] | None = None, confidence: float = 0.8) -> dict
- Produces: main(text_field: str, max_length: int = 0) -> dict
- Retains: run(parameters: dict) -> dict adapters

- [ ] **Step 1: Add runner-style tests first**

For each Function add a test that calls main with keyword arguments from its
metadata example and asserts the exact returned dict. Add a test proving run
delegates to main. Remove no existing behavioral coverage.

- [ ] **Step 2: Verify RED**

Run:

~~~bash
python3 -m unittest discover -s function/text_similarity_checker/test -v
python3 -m unittest discover -s function/text_quality_analyzer/test -v
~~~

Expected: both new tests fail because main accepts no Function parameters and
returns an integer.

- [ ] **Step 3: Implement platform entrypoints**

Change each main to accept declared keyword parameters and return the declared
dict. Keep run as a mapping adapter that calls main. Remove json/sys CLI
behavior because anno-function-runner imports and calls main directly.

- [ ] **Step 4: Verify GREEN and strict validation**

Run:

~~~bash
python3 -m unittest discover -s function/text_similarity_checker/test -v
python3 -m unittest discover -s function/text_quality_analyzer/test -v
python3 scripts/validate_functions.py
~~~

Expected: all Function tests and strict validation pass.

- [ ] **Step 5: Commit**

Run:

~~~bash
git add function
git commit -m "fix(function): conform entrypoints to runner contract"
~~~

### Task 5: Every-Branch GitHub CI

**Files:**
- Create: .github/workflows/function-ci.yml
- Create: tests/ci/test_workflows.py
- Create: requirements-ci.txt

**Interfaces:**
- Produces stable required check name: Function CI / strict

- [ ] **Step 1: Write failing workflow structure tests**

Parse YAML and assert push has no branch filter, pull_request is enabled,
permissions are contents read, Python is 3.11, timeout-minutes is set,
concurrency cancels superseded runs, validator tests run before repository
validation, and every uses value is pinned to a 40-character SHA.

- [ ] **Step 2: Verify RED**

Run: python3 -m unittest tests.ci.test_workflows.WorkflowTest.test_branch_ci -v

Expected: failure because function-ci.yml does not exist.

- [ ] **Step 3: Add pinned dependencies and workflow**

Pin Pydantic and PyYAML to exact versions in requirements-ci.txt. Create the
workflow with push, pull_request, workflow_dispatch, read-only permissions,
one strict job, actions/checkout and actions/setup-python pinned by full SHA,
pip install -r requirements-ci.txt, CI unit tests, and
python3 scripts/validate_functions.py.

- [ ] **Step 4: Verify GREEN**

Run:

~~~bash
python3 -m unittest tests.ci.test_workflows -v
python3 scripts/validate_functions.py
~~~

Expected: workflow tests and repository validation pass.

- [ ] **Step 5: Commit**

Run:

~~~bash
git add .github/workflows/function-ci.yml requirements-ci.txt tests/ci
git commit -m "ci: validate every Function branch and pull request"
~~~

### Task 6: Validated Immutable Tag Release

**Files:**
- Create: scripts/release_tag.py
- Create: tests/ci/test_release_tag.py
- Create: .github/workflows/function-release.yml
- Modify: tests/ci/test_workflows.py

**Interfaces:**
- Produces: validate_release(repo: str, version: str, commit_sha: str, release_branch: str, client: GitHubClient) -> ReleaseDecision
- Produces CLI --check and --create modes; --create requires GitHub App token

- [ ] **Step 1: Write failing release policy tests**

Use a fake GitHub client to cover invalid/non-increasing versions, existing
tags, non-commit targets, off-branch commits, missing successful Function CI,
ambiguous check runs, dry-run, and exactly one annotated tag creation.

- [ ] **Step 2: Verify RED**

Run: python3 -m unittest tests.ci.test_release_tag -v

Expected: import failure because scripts.release_tag does not exist.

- [ ] **Step 3: Implement fail-closed release decisions**

Validate v<positive integer>, query all tag refs without truncation, require the
commit to be reachable from the configured release branch through GitHub's
compare API, and require a successful check run named Function CI / strict for
the exact SHA. In create mode create an annotated tag object then its ref.
Refuse to continue if either target already exists.

- [ ] **Step 4: Add pre-validation release workflow and tag audit**

workflow_dispatch inputs are version, commit_sha, and release_branch. A validate
job uses contents read and runs complete strict CI plus release_tag.py --check.
A create job requires that job, obtains a short-lived GitHub App token from
encrypted APP_ID and APP_PRIVATE_KEY secrets, and runs --create. A v* push audit
job reruns strict validation without mutation.

- [ ] **Step 5: Verify GREEN**

Run:

~~~bash
python3 -m unittest tests.ci.test_release_tag tests.ci.test_workflows -v
python3 scripts/validate_functions.py
~~~

Expected: all release and workflow tests pass.

- [ ] **Step 6: Commit**

Run:

~~~bash
git add scripts/release_tag.py .github/workflows/function-release.yml tests/ci
git commit -m "ci: gate immutable Function version tags"
~~~

### Task 7: Idempotent Repository Rulesets

**Files:**
- Create: scripts/configure_repository_rules.py
- Create: tests/ci/test_repository_rules.py

**Interfaces:**
- Produces: desired_rulesets(release_branch: str, app_integration_id: int) -> list[dict]
- Produces: reconcile(current: list[dict], desired: list[dict]) -> ChangeSet
- CLI defaults to dry-run; --apply is required for writes

- [ ] **Step 1: Write failing reconciler tests**

Test create, exact no-op, minimal update, preservation of unrelated rulesets,
duplicate managed-name rejection, missing branch rejection, absent app ID
rejection, no administrator bypass, tag create-only app bypass, and serialized
GitHub API payloads.

- [ ] **Step 2: Verify RED**

Run: python3 -m unittest tests.ci.test_repository_rules -v

Expected: import failure because configure_repository_rules does not exist.

- [ ] **Step 3: Implement pure reconciliation and GitHub adapter**

Manage only rulesets named anno-function-release-branch,
anno-function-version-creation, and anno-function-version-immutable. The branch
ruleset requires PRs, strict status checks, current branches, and blocks
deletion/force push. The creation ruleset gives its only bypass to the supplied
Integration actor. The immutable ruleset blocks tag update/deletion with no
bypass. Fetch full current ruleset details before diffing. Abort on ambiguity
or partial reads.

- [ ] **Step 4: Verify GREEN and dry-run**

Run:

~~~bash
python3 -m unittest tests.ci.test_repository_rules -v
python3 scripts/configure_repository_rules.py \
  --repository mengf66/anno-function-persional \
  --release-branch feat/add-dedup-script \
  --app-integration-id 1
~~~

Expected: tests pass; dry-run prints three proposed rulesets and performs no
POST, PUT, or DELETE.

- [ ] **Step 5: Commit**

Run:

~~~bash
git add scripts/configure_repository_rules.py tests/ci
git commit -m "feat(ci): reconcile Function repository rulesets"
~~~

### Task 8: End-To-End Verification And Controlled Activation

**Files:**
- Modify only files found defective by verification.

**Interfaces:**
- Consumes all prior task outputs.
- Produces local verification evidence and an explicit ruleset activation diff.

- [ ] **Step 1: Run all local gates from a clean checkout**

Run:

~~~bash
python3 -m unittest discover -s tests/ci -p "test_*.py" -v
python3 scripts/validate_functions.py
git diff --check
git status --short
~~~

Expected: all tests pass, validator succeeds, no whitespace errors, and only
intentional files are present.

- [ ] **Step 2: Review the ruleset dry-run**

Run configure_repository_rules.py without --apply using the real repository,
chosen release branch, and dedicated GitHub App integration ID. Save the exact
read-only diff in the task report. Expected: only the three named managed
rulesets are created or updated.

- [ ] **Step 3: Push and verify branch CI before protection**

Push the feature branch, open a PR to the chosen release branch, and verify the
exact Function CI / strict check succeeds. Do not activate a required check
that has never reported successfully in the repository.

- [ ] **Step 4: Obtain explicit activation confirmation**

Present the real ruleset diff, release branch, app identity, passing check URL,
and rollback API operations. Apply no repository setting until the user
confirms this exact activation.

- [ ] **Step 5: Apply and read back rulesets**

Run the reconciler with --apply, then fetch all three rulesets again and compare
their normalized bodies to desired_rulesets. Expected: no diff.

- [ ] **Step 6: Verify server-side enforcement**

Use GitHub API read operations to confirm required check, pull request,
force-push/deletion blocks, tag create restriction, and tag update/deletion
blocks. Do not create or delete a production tag as a test.
