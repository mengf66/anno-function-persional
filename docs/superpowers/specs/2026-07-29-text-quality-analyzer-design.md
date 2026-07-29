# Text Quality Analyzer Design

## Goal

Add a small Anno Function that measures text quality signals commonly needed when records enter a Feishu-based annotation workflow. The function must use only the Python standard library and remain structurally identical to the repository's existing `text_similarity_checker` function.

## Scope

Create `function/text_quality_analyzer/` with exactly these runtime artifacts:

- `meta.yaml` declares the function, Feishu/manual inputs, outputs, and one representative example.
- `src/main.py` contains the analysis logic, the `run(parameters)` adapter, and the JSON command-line entry point.
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

`main()` reads one JSON object from the first command-line argument, or from standard input when no argument is supplied. It passes the decoded object to `run(parameters)`. `run` extracts the declared inputs and calls `analyze_text`. The result is serialized as one JSON object on standard output with `ensure_ascii=False` so Chinese text remains readable.

`analyze_text` validates `max_length`, calculates each metric, and returns the declared result mapping. The entry point does not catch malformed input or validation errors; it exits unsuccessfully with the original error rather than producing a plausible but incorrect result.

## Error Handling

- Missing `text_field` raises `KeyError`, matching the existing function's required-parameter behavior.
- A negative `max_length` raises `ValueError` with a clear message.
- JSON decoding and incompatible input types are not silently coerced, except `max_length` follows the existing adapter pattern and is converted with `int(...)`.

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
- the `run(parameters)` adapter defaults.

The script will also be exercised through both supported JSON entry paths to verify that stdout is valid JSON and matches the metadata contract.
