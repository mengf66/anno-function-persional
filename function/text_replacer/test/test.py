import importlib.util
import unittest
from pathlib import Path


MAIN_PATH = Path(__file__).resolve().parents[1] / "src" / "main.py"


def load_main_module():
    if not MAIN_PATH.exists():
        raise AssertionError("src/main.py must exist")
    spec = importlib.util.spec_from_file_location("text_replacer", MAIN_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class TextReplacerTest(unittest.TestCase):
    def test_replaces_all_occurrences_by_default(self):
        replacer = load_main_module()

        result = replacer.replace_text("Anno and Anno", "Anno", "ANNO")

        self.assertEqual(
            result,
            {"result": "ANNO and ANNO", "replacement_count": 2},
        )

    def test_limits_replacement_count(self):
        replacer = load_main_module()

        result = replacer.replace_text("one one one", "one", "two", 2)

        self.assertEqual(result, {"result": "two two one", "replacement_count": 2})

    def test_can_delete_matching_text(self):
        replacer = load_main_module()

        result = replacer.replace_text("a-b-c", "-", "")

        self.assertEqual(result, {"result": "abc", "replacement_count": 2})

    def test_reports_zero_when_no_text_matches(self):
        replacer = load_main_module()

        result = replacer.replace_text("Anno", "review", "done")

        self.assertEqual(result, {"result": "Anno", "replacement_count": 0})

    def test_counts_non_overlapping_matches(self):
        replacer = load_main_module()

        result = replacer.replace_text("aaaa", "aa", "b")

        self.assertEqual(result, {"result": "bb", "replacement_count": 2})

    def test_rejects_empty_old_text(self):
        replacer = load_main_module()

        with self.assertRaisesRegex(ValueError, "old_text must not be empty"):
            replacer.replace_text("Anno", "", "text")

    def test_rejects_negative_max_replacements(self):
        replacer = load_main_module()

        with self.assertRaisesRegex(ValueError, "must be zero or greater"):
            replacer.replace_text("Anno", "Anno", "ANNO", -1)

    def test_rejects_non_string_input(self):
        replacer = load_main_module()

        with self.assertRaisesRegex(TypeError, "text_field must be a string"):
            replacer.replace_text(None, "Anno", "ANNO")

    def test_rejects_boolean_max_replacements(self):
        replacer = load_main_module()

        with self.assertRaisesRegex(TypeError, "must be an integer"):
            replacer.replace_text("Anno", "Anno", "ANNO", True)

    def test_run_uses_default_replacement_limit(self):
        replacer = load_main_module()

        result = replacer.run(
            {"text_field": "x x", "old_text": "x", "new_text": "y"}
        )

        self.assertEqual(result, {"result": "y y", "replacement_count": 2})


if __name__ == "__main__":
    unittest.main()
