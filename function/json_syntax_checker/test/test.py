import importlib.util
import unittest
from pathlib import Path


MAIN_PATH = Path(__file__).resolve().parents[1] / "src" / "main.py"


def load_main_module():
    if not MAIN_PATH.exists():
        raise AssertionError("src/main.py must exist")
    spec = importlib.util.spec_from_file_location("json_syntax_checker", MAIN_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class JsonSyntaxCheckerTest(unittest.TestCase):
    def test_accepts_valid_json_object(self):
        checker = load_main_module()

        result = checker.check_json_syntax('{"name": "Anno", "count": 2}')

        self.assertEqual(
            result,
            {
                "result": True,
                "error_message": "",
                "error_line": 0,
                "error_column": 0,
                "error_position": 0,
            },
        )

    def test_accepts_valid_json_array(self):
        checker = load_main_module()

        result = checker.check_json_syntax('[true, false, null, "text"]')

        self.assertTrue(result["result"])

    def test_reports_trailing_comma(self):
        checker = load_main_module()

        result = checker.check_json_syntax('{"name": "Anno",}')

        self.assertFalse(result["result"])
        self.assertEqual(
            result["error_message"],
            "Expecting property name enclosed in double quotes",
        )
        self.assertEqual(result["error_line"], 1)
        self.assertEqual(result["error_column"], 17)
        self.assertEqual(result["error_position"], 16)

    def test_reports_multiline_error_location(self):
        checker = load_main_module()

        result = checker.check_json_syntax('{\n  "name": "Anno",\n  "enabled": tru\n}')

        self.assertFalse(result["result"])
        self.assertEqual(result["error_line"], 3)
        self.assertEqual(result["error_column"], 14)

    def test_rejects_single_quoted_property_name(self):
        checker = load_main_module()

        result = checker.check_json_syntax("{'name': 'Anno'}")

        self.assertFalse(result["result"])
        self.assertIn("double quotes", result["error_message"])

    def test_rejects_truncated_object(self):
        checker = load_main_module()

        result = checker.check_json_syntax('{"name": "Anno"')

        self.assertFalse(result["result"])
        self.assertGreater(result["error_position"], 0)

    def test_rejects_empty_text(self):
        checker = load_main_module()

        result = checker.check_json_syntax("")

        self.assertFalse(result["result"])
        self.assertEqual(result["error_line"], 1)
        self.assertEqual(result["error_column"], 1)

    def test_run_passes_json_text_to_main(self):
        checker = load_main_module()

        result = checker.run({"json_text": "{}"})

        self.assertEqual(result, checker.main("{}"))


if __name__ == "__main__":
    unittest.main()
