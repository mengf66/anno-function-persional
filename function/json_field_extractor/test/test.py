import importlib.util
import json
import unittest
from pathlib import Path


MAIN_PATH = Path(__file__).resolve().parents[1] / "src" / "main.py"


def load_main_module():
    if not MAIN_PATH.exists():
        raise AssertionError("src/main.py must exist")
    spec = importlib.util.spec_from_file_location("json_field_extractor", MAIN_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class JsonFieldExtractorTest(unittest.TestCase):
    def test_extracts_required_fields(self):
        extractor = load_main_module()

        result = extractor.extract_json_fields(
            '{"name": "Anno", "enabled": true, "ignored": 1}'
        )

        self.assertEqual(result, {"name": "Anno", "enabled": True})

    def test_rejects_invalid_json(self):
        extractor = load_main_module()

        with self.assertRaises(json.JSONDecodeError):
            extractor.extract_json_fields('{"name": "Anno",}')

    def test_rejects_non_object_json(self):
        extractor = load_main_module()

        with self.assertRaisesRegex(ValueError, "must be an object"):
            extractor.extract_json_fields('["Anno", true]')

    def test_rejects_missing_name(self):
        extractor = load_main_module()

        with self.assertRaisesRegex(ValueError, "name must be a string"):
            extractor.extract_json_fields('{"enabled": true}')

    def test_rejects_non_boolean_enabled(self):
        extractor = load_main_module()

        with self.assertRaisesRegex(ValueError, "enabled must be a boolean"):
            extractor.extract_json_fields('{"name": "Anno", "enabled": 1}')

    def test_run_passes_json_text_to_main(self):
        extractor = load_main_module()

        result = extractor.run({"json_text": '{"name": "Anno", "enabled": false}'})

        self.assertEqual(result, {"name": "Anno", "enabled": False})


if __name__ == "__main__":
    unittest.main()
