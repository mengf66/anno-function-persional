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
    def test_main_accepts_function_parameters(self):
        analyzer = load_main_module()

        result = analyzer.main(text_field="Hello world", max_length=20)

        self.assertEqual(result["char_count"], 11)
        self.assertTrue(result["result"])

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
