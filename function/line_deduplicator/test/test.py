import importlib.util
import unittest
from pathlib import Path


MAIN_PATH = Path(__file__).resolve().parents[1] / "src" / "main.py"


def load_main_module():
    if not MAIN_PATH.exists():
        raise AssertionError("src/main.py must exist")
    spec = importlib.util.spec_from_file_location("line_deduplicator", MAIN_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class LineDeduplicatorTest(unittest.TestCase):
    def test_removes_duplicate_lines_and_preserves_order(self):
        deduplicator = load_main_module()

        result = deduplicator.deduplicate_lines("apple\nbanana\napple\npear\nbanana")

        self.assertEqual(
            result,
            {
                "result": "apple\nbanana\npear",
                "original_line_count": 5,
                "unique_line_count": 3,
                "removed_count": 2,
            },
        )

    def test_empty_text_has_no_lines(self):
        deduplicator = load_main_module()

        result = deduplicator.deduplicate_lines("")

        self.assertEqual(result["result"], "")
        self.assertEqual(result["original_line_count"], 0)
        self.assertEqual(result["removed_count"], 0)

    def test_treats_blank_line_as_a_value(self):
        deduplicator = load_main_module()

        result = deduplicator.deduplicate_lines("first\n\nsecond\n\n")

        self.assertEqual(result["result"], "first\n\nsecond")
        self.assertEqual(result["removed_count"], 1)

    def test_run_delegates_to_main(self):
        deduplicator = load_main_module()

        result = deduplicator.run({"text_field": "one\none"})

        self.assertEqual(result, deduplicator.main("one\none"))


if __name__ == "__main__":
    unittest.main()
