# Text Quality Analyzer Design

## Goal

Add a small Anno Function that measures text quality signals commonly needed when records enter a Feishu-based annotation workflow. The function must use only the Python standard library and remain structurally identical to the repository's existing `text_similarity_checker` function.

## Scope

Create `function/text_quality_analyzer/` with exactly these runtime artifacts:

- `meta.yaml` declares the function, Feishu/manual inputs, outputs, and one representative example.
- `src/main.py` contains the analysis logic, the `run(parameters)` adapter, and the callable `main(**parameters)` entry point required by `anno-function-runner`.
- `test/test.py` contains standard-library `unittest` coverage.

No third-party dependencies, network calls, file writes, shared helpers, or changes to the existing function are included.

## Function Contract

The function accepts:

- `text_field` (`string`, required, Feishu source): text to inspect.
- `max_length` (`int`, optional, manual source, default `0`): maximum allowed character count. Zero disables the limit. Negative values are invalid.

It returns:

- `result` (`bool`): true when the limit is disabled or `char_count <= max_length`.
- `char_count` (`int`): Python Unicode code-point count, equivalent to `len(text_field)`.
- `non_whitespace_count` (`int`): count of characters for which `str.isspace()` is false.
- `word_count` (`int`): count of contiguous Unicode alphanumeric sequences. Underscores and punctuation are separators.
- `line_count` (`int`): zero for empty text; otherwise the number of logical lines recognized by `str.splitlines()`, including one additional empty line when the text ends in a line boundary.

The metadata uses `apiVersion: functions.anno.meetchances.com/v1alpha1`, `kind: Function`, and the same field structure used by `text_similarity_checker`.

## Runtime Flow

`anno-function-runner` imports `src/main.py` and calls `main(text_field=..., max_length=...)` directly. `main` delegates to `analyze_text` and returns the declared result mapping. It does not read process arguments, consume standard input, or print JSON.

`run(parameters)` remains a mapping adapter for compatibility with direct payload-based callers. It extracts the declared inputs and delegates to `main`, matching the structure established by `text_similarity_checker` in tag `v5`.

`analyze_text` validates `max_length`, calculates each metric, and returns the declared result mapping. Neither entry point catches validation or type errors, so invalid invocations fail explicitly rather than producing a plausible but incorrect result.

## Error Handling

- Calling `run` without `text_field` raises `KeyError`, matching the existing function's required-parameter behavior.
- Calling `main` without `text_field` raises `TypeError` through its required Python parameter.
- A negative `max_length` raises `ValueError` with a clear message.
- Incompatible input types are not silently coerced by `main`; `run` retains the existing adapter behavior and converts `max_length` with `int(...)`.

## Verification

Unit tests cover:

- ordinary English text and the exact output metrics;
- mixed Chinese and English text with Unicode-aware word counting;
- multiline text, including a trailing newline;
- empty text;
- a disabled length limit;
- equality at the maximum length boundary;
- text over the maximum length;
- rejection of a negative maximum length;
- direct runner-style invocation through `main(text_field=..., max_length=...)`;
- the `run(parameters)` adapter defaults.

The complete Function tests and the anno-server metadata parser must pass. After verification and review, annotated tag `v7` will point to the corrected runner-compatible commit; existing tag `v6` remains unchanged.
