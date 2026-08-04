import importlib.util
import unittest
from pathlib import Path


MAIN_PATH = Path(__file__).resolve().parents[1] / "src" / "main.py"


def load_main_module():
    if not MAIN_PATH.exists():
        raise AssertionError("src/main.py must exist")
    spec = importlib.util.spec_from_file_location("keyword_occurrence_checker", MAIN_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class KeywordOccurrenceCheckerTest(unittest.TestCase):
    def test_finds_keyword_without_case_sensitivity(self):
        checker = load_main_module()

        result = checker.check_keyword_occurrences("Anno and ANNO", "anno")

        self.assertEqual(result, {"result": True, "match_count": 2})

    def test_respects_case_sensitivity(self):
        checker = load_main_module()

        result = checker.check_keyword_occurrences(
            "Anno and ANNO",
            "Anno",
            case_sensitive=True,
        )

        self.assertEqual(result, {"result": True, "match_count": 1})

    def test_reports_no_match(self):
        checker = load_main_module()

        result = checker.check_keyword_occurrences("annotation", "review")

        self.assertEqual(result, {"result": False, "match_count": 0})

    def test_counts_non_overlapping_occurrences(self):
        checker = load_main_module()

        result = checker.check_keyword_occurrences("aaaa", "aa")

        self.assertEqual(result["match_count"], 2)

    def test_uses_unicode_case_folding(self):
        checker = load_main_module()

        result = checker.check_keyword_occurrences("Straße", "STRASSE")

        self.assertTrue(result["result"])
        self.assertEqual(result["match_count"], 1)

    def test_rejects_empty_keyword(self):
        checker = load_main_module()

        with self.assertRaisesRegex(ValueError, "keyword must not be empty"):
            checker.check_keyword_occurrences("text", "")

    def test_rejects_non_string_text(self):
        checker = load_main_module()

        with self.assertRaisesRegex(TypeError, "text_field must be a string"):
            checker.check_keyword_occurrences(None, "anno")

    def test_rejects_non_boolean_case_sensitive(self):
        checker = load_main_module()

        with self.assertRaisesRegex(TypeError, "case_sensitive must be a boolean"):
            checker.check_keyword_occurrences("Anno", "anno", "false")

    def test_run_uses_default_case_sensitivity(self):
        checker = load_main_module()

        result = checker.run({"text_field": "Anno", "keyword": "anno"})

        self.assertEqual(result, checker.main("Anno", "anno", False))


if __name__ == "__main__":
    unittest.main()
