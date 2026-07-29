import importlib.util
import unittest
from pathlib import Path


MAIN_PATH = Path(__file__).resolve().parents[1] / "src" / "main.py"


def load_main_module():
    if not MAIN_PATH.exists():
        raise AssertionError("src/main.py must exist")
    spec = importlib.util.spec_from_file_location("text_similarity_checker", MAIN_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class TextSimilarityCheckerTest(unittest.TestCase):
    def test_main_accepts_function_parameters(self):
        checker = load_main_module()

        result = checker.main(
            text_field="Python makes data processing easy",
            existing_texts=["Python makes data processing very easy"],
            confidence=0.8,
        )

        self.assertFalse(result["result"])
        self.assertEqual(result["sim_text"], "Python makes data processing very easy")

    def test_rejects_highly_similar_text(self):
        checker = load_main_module()

        result = checker.check_text_similarity(
            "Python makes data processing easy",
            ["Python makes data processing very easy"],
            confidence=0.8,
        )

        self.assertFalse(result["result"])
        self.assertEqual(result["sim_text"], "Python makes data processing very easy")
        self.assertGreaterEqual(result["value"], 0.8)

    def test_accepts_distinct_text(self):
        checker = load_main_module()

        result = checker.check_text_similarity(
            "Python makes data processing easy",
            ["The weather is sunny today"],
            confidence=0.8,
        )

        self.assertTrue(result["result"])

    def test_accepts_similarity_equal_to_threshold(self):
        checker = load_main_module()

        result = checker.check_text_similarity(
            "abcd",
            ["abce"],
            confidence=0.75,
        )

        self.assertTrue(result["result"])


if __name__ == "__main__":
    unittest.main()
