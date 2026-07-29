# Text Quality Analyzer Runner Contract Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make `text_quality_analyzer` callable by `anno-function-runner` using the `main(**parameters) -> dict` contract established in repository tag `v5`.

**Architecture:** Preserve `analyze_text` as the pure analysis function. Change `run(parameters)` into a mapping adapter that delegates to a keyword-parameter `main`, and make `main` return the analysis result directly without process I/O.

**Tech Stack:** Python 3 standard library (`re`, `unittest`), Anno Function runner contract

## Global Constraints

- Modify only `function/text_quality_analyzer/src/main.py` and `function/text_quality_analyzer/test/test.py` as runtime artifacts.
- Keep `analyze_text(text_field: str, max_length: int = 0) -> dict` behavior unchanged.
- Expose `main(text_field: str, max_length: int = 0) -> dict` for `anno-function-runner`.
- Keep `run(parameters: dict) -> dict`, with `max_length` converted through `int(...)`, and delegate it to `main`.
- Remove argv, stdin, stdout, and JSON serialization responsibilities from the module.
- After verification and review, create annotated tag `v7` without moving tag `v6`.

---

### Task 1: Runner-Compatible Main

**Files:**
- Modify: `function/text_quality_analyzer/test/test.py`
- Modify: `function/text_quality_analyzer/src/main.py`

**Interfaces:**
- Consumes: runner keyword arguments `text_field: str` and `max_length: int = 0`.
- Produces: `main(text_field: str, max_length: int = 0) -> dict` and the existing result keys.

- [ ] **Step 1: Add a failing runner-contract test**

Add this method to `TextQualityAnalyzerTest`:

```python
def test_main_accepts_function_parameters(self):
    analyzer = load_main_module()

    result = analyzer.main(text_field="Hello world", max_length=20)

    self.assertEqual(result["char_count"], 11)
    self.assertTrue(result["result"])
```

- [ ] **Step 2: Run the focused test and verify RED**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest \
  function.text_quality_analyzer.test.test.TextQualityAnalyzerTest.test_main_accepts_function_parameters \
  -v
```

Expected: FAIL with `TypeError: main() got an unexpected keyword argument 'text_field'`.

- [ ] **Step 3: Implement the v5-style runner contract**

In `function/text_quality_analyzer/src/main.py`, remove the `json` and `sys` imports, replace `run` and `main`, and remove the `if __name__ == "__main__"` block so the lower section is:

```python
def run(parameters: dict) -> dict:
    """Run the function from a parameter payload."""
    return main(
        text_field=parameters["text_field"],
        max_length=int(parameters.get("max_length", 0)),
    )


def main(text_field: str, max_length: int = 0) -> dict:
    """Run the Function with parameters supplied by anno-function-runner."""
    return analyze_text(text_field=text_field, max_length=max_length)
```

- [ ] **Step 4: Run the complete Function tests and verify GREEN**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest \
  function/text_similarity_checker/test/test.py \
  function/text_quality_analyzer/test/test.py \
  -v
```

Expected: 13 tests run and pass: 3 existing similarity-checker tests on the feature branch and 10 text-quality-analyzer tests.

- [ ] **Step 5: Verify the callable contract directly**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 - <<'PY'
import importlib.util
from pathlib import Path

path = Path("function/text_quality_analyzer/src/main.py")
spec = importlib.util.spec_from_file_location("text_quality_analyzer", path)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
result = module.main(text_field="Hello 世界\nAnno", max_length=20)
assert result == {
    "result": True,
    "char_count": 13,
    "non_whitespace_count": 11,
    "word_count": 3,
    "line_count": 2,
}
print("runner main contract OK")
PY
```

Expected: `runner main contract OK`.

- [ ] **Step 6: Commit the runner fix**

```bash
git add function/text_quality_analyzer/src/main.py function/text_quality_analyzer/test/test.py
git commit -m "fix(function): align analyzer main with runner contract"
```
