# Text Quality Analyzer Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an Anno Function that reports useful text metrics and optionally rejects text exceeding a configured character limit.

**Architecture:** Follow the existing `text_similarity_checker` three-file layout. Keep the pure analysis in `analyze_text`, adapt the platform parameter mapping in `run`, and retain the same command-line-or-stdin JSON entry point used by the existing function.

**Tech Stack:** Python 3 standard library (`json`, `re`, `sys`, `unittest`), Anno Function YAML metadata

## Global Constraints

- Create only `function/text_quality_analyzer/meta.yaml`, `function/text_quality_analyzer/src/main.py`, and `function/text_quality_analyzer/test/test.py` as runtime artifacts.
- Use no third-party dependencies, network calls, file writes, or shared helpers.
- Use `apiVersion: functions.anno.meetchances.com/v1alpha1` and `kind: Function`.
- Accept `text_field: string` and optional `max_length: int`, where `0` disables the limit and negative values are invalid.
- Return exactly `result`, `char_count`, `non_whitespace_count`, `word_count`, and `line_count`.
- Read JSON from the first command-line argument or standard input and emit one JSON object with `ensure_ascii=False`.

---

### Task 1: Text Analysis And Runtime Entry Point

**Files:**
- Create: `function/text_quality_analyzer/test/test.py`
- Create: `function/text_quality_analyzer/src/main.py`

**Interfaces:**
- Consumes: `text_field: str`, `max_length: int = 0`, and platform parameter mappings.
- Produces: `analyze_text(text_field: str, max_length: int = 0) -> dict`, `run(parameters: dict) -> dict`, and `main() -> int`.

- [ ] **Step 1: Write the failing unit tests**

Create `function/text_quality_analyzer/test/test.py`:

```python
import importlib.util
import unittest
from pathlib import Path


MAIN_PATH = Path(__file__).resolve().parents[1] / "src" / "main.py"


def load_main_module():
    if not MAIN_PATH.exists():
        raise AssertionError("src/main.py must exist")
    spec = importlib.util.spec_from_file_location("text_quality_analyzer", MAIN_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class TextQualityAnalyzerTest(unittest.TestCase):
    def test_reports_english_text_metrics(self):
        analyzer = load_main_module()

        result = analyzer.analyze_text("Hello world", max_length=20)

        self.assertEqual(
            result,
            {
                "result": True,
                "char_count": 11,
                "non_whitespace_count": 10,
                "word_count": 2,
                "line_count": 1,
            },
        )

    def test_counts_mixed_chinese_and_english_words(self):
        analyzer = load_main_module()

        result = analyzer.analyze_text("你好，Anno 2026")

        self.assertEqual(result["word_count"], 3)
        self.assertEqual(result["non_whitespace_count"], 11)

    def test_counts_trailing_newline_as_empty_logical_line(self):
        analyzer = load_main_module()

        result = analyzer.analyze_text("first\nsecond\n")

        self.assertEqual(result["line_count"], 3)

    def test_empty_text_has_zero_lines(self):
        analyzer = load_main_module()

        result = analyzer.analyze_text("")

        self.assertEqual(result["line_count"], 0)
        self.assertEqual(result["word_count"], 0)
        self.assertTrue(result["result"])

    def test_accepts_text_at_length_limit(self):
        analyzer = load_main_module()

        result = analyzer.analyze_text("abcd", max_length=4)

        self.assertTrue(result["result"])

    def test_rejects_text_over_length_limit(self):
        analyzer = load_main_module()

        result = analyzer.analyze_text("abcde", max_length=4)

        self.assertFalse(result["result"])

    def test_zero_disables_length_limit(self):
        analyzer = load_main_module()

        result = analyzer.analyze_text("a" * 1000, max_length=0)

        self.assertTrue(result["result"])

    def test_rejects_negative_length_limit(self):
        analyzer = load_main_module()

        with self.assertRaisesRegex(ValueError, "max_length must be zero or greater"):
            analyzer.analyze_text("text", max_length=-1)

    def test_run_uses_default_length_limit(self):
        analyzer = load_main_module()

        result = analyzer.run({"text_field": "hello"})

        self.assertTrue(result["result"])
        self.assertEqual(result["char_count"], 5)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run the tests and verify they fail**

Run:

```bash
python -m unittest function/text_quality_analyzer/test/test.py -v
```

Expected: FAIL because `function/text_quality_analyzer/src/main.py` does not exist.

- [ ] **Step 3: Implement the minimal analyzer and entry point**

Create `function/text_quality_analyzer/src/main.py`:

```python
#!/usr/bin/env python3
"""Text quality analyzer entry point."""

import json
import re
import sys


LINE_BOUNDARIES = ("\n", "\r", "\x0b", "\x0c", "\x1c", "\x1d", "\x1e", "\x85", "\u2028", "\u2029")


def count_lines(text: str) -> int:
    """Count logical lines, including an empty line after a trailing boundary."""
    if not text:
        return 0
    return len(text.splitlines()) + int(text.endswith(LINE_BOUNDARIES))


def analyze_text(text_field: str, max_length: int = 0) -> dict:
    """Measure text and apply an optional character limit."""
    if max_length < 0:
        raise ValueError("max_length must be zero or greater")

    char_count = len(text_field)
    return {
        "result": max_length == 0 or char_count <= max_length,
        "char_count": char_count,
        "non_whitespace_count": sum(not character.isspace() for character in text_field),
        "word_count": len(re.findall(r"[^\W_]+", text_field, flags=re.UNICODE)),
        "line_count": count_lines(text_field),
    }


def run(parameters: dict) -> dict:
    """Run the function from a parameter payload."""
    return analyze_text(
        text_field=parameters["text_field"],
        max_length=int(parameters.get("max_length", 0)),
    )


def main() -> int:
    payload = json.loads(sys.argv[1] if len(sys.argv) > 1 else sys.stdin.read())
    print(json.dumps(run(payload), ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Run the tests and verify they pass**

Run:

```bash
python -m unittest function/text_quality_analyzer/test/test.py -v
```

Expected: 9 tests run and `OK`.

- [ ] **Step 5: Verify both JSON input paths**

Run:

```bash
python function/text_quality_analyzer/src/main.py '{"text_field":"Hello 世界\nAnno","max_length":20}'
```

Expected stdout:

```json
{"result": true, "char_count": 13, "non_whitespace_count": 11, "word_count": 3, "line_count": 2}
```

Run:

```bash
printf '%s' '{"text_field":"12345","max_length":4}' | python function/text_quality_analyzer/src/main.py
```

Expected stdout:

```json
{"result": false, "char_count": 5, "non_whitespace_count": 5, "word_count": 1, "line_count": 1}
```

- [ ] **Step 6: Commit the behavior**

```bash
git add function/text_quality_analyzer/src/main.py function/text_quality_analyzer/test/test.py
git commit -m "feat(function): add text quality analyzer"
```

### Task 2: Anno Function Metadata

**Files:**
- Create: `function/text_quality_analyzer/meta.yaml`
- Verify: `function/text_quality_analyzer/src/main.py`

**Interfaces:**
- Consumes: `analyze_text` return keys from Task 1.
- Produces: Anno discovery metadata for the `text_quality_analyzer` function.

- [ ] **Step 1: Create metadata matching the runtime contract**

Create `function/text_quality_analyzer/meta.yaml`:

```yaml
apiVersion: functions.anno.meetchances.com/v1alpha1
kind: Function

metadata:
  name: text_quality_analyzer
  owner: 欣翔
  description: 统计文本质量指标，并按可选字符数上限进行校验
  examples:
    - name: 检查文本质量
      parameters:
        text_field: |-
          Hello 世界
          Anno
        max_length: 20
      returns:
        result: true
        char_count: 13
        non_whitespace_count: 11
        word_count: 3
        line_count: 2

parameters:
  - key: text_field
    name: 待检查文本
    description: 需要统计质量指标的文本
    dataType: string
    sourceType: feishu
    required: true

  - key: max_length
    name: 最大字符数
    description: 允许的最大字符数，设为 0 时不限制
    dataType: int
    sourceType: manual
    required: false
    default: 0
    ui:
      - type: numberInput
        minimum: 0

returns:
  - key: result
    name: 长度校验结果
    description: 未启用字符数限制或文本未超过上限时为 true
    dataType: bool
    required: true

  - key: char_count
    name: 字符数
    description: 文本包含的 Unicode 字符总数
    dataType: int
    required: true

  - key: non_whitespace_count
    name: 非空白字符数
    description: 文本中不属于空白符的字符数
    dataType: int
    required: true

  - key: word_count
    name: 词段数
    description: 文本中连续 Unicode 字母或数字片段的数量
    dataType: int
    required: true

  - key: line_count
    name: 行数
    description: 文本逻辑行数量，空文本为 0
    dataType: int
    required: true
```

- [ ] **Step 2: Check metadata and runtime keys mechanically**

Run:

```bash
python - <<'PY'
from pathlib import Path

metadata = Path("function/text_quality_analyzer/meta.yaml").read_text(encoding="utf-8")
required_fragments = (
    "apiVersion: functions.anno.meetchances.com/v1alpha1",
    "kind: Function",
    "name: text_quality_analyzer",
    "key: text_field",
    "key: max_length",
    "key: result",
    "key: char_count",
    "key: non_whitespace_count",
    "key: word_count",
    "key: line_count",
)
missing = [fragment for fragment in required_fragments if fragment not in metadata]
if missing:
    raise SystemExit(f"missing metadata fragments: {missing}")
print("metadata contract OK")
PY
```

Expected: `metadata contract OK`.

- [ ] **Step 3: Run the complete function test suite**

Run:

```bash
python -m unittest discover -s function -p 'test.py' -v
```

Expected: all existing and new function tests pass.

- [ ] **Step 4: Check repository cleanliness and formatting errors**

Run:

```bash
git diff --check
git status --short
```

Expected: `git diff --check` exits successfully; status lists only `function/text_quality_analyzer/meta.yaml` before the metadata commit.

- [ ] **Step 5: Commit metadata**

```bash
git add function/text_quality_analyzer/meta.yaml
git commit -m "feat(function): declare text quality analyzer"
```
