import importlib.util
import json
import unittest
from pathlib import Path


MAIN_PATH = Path(__file__).resolve().parents[1] / "src" / "main.py"


def load_main_module():
    if not MAIN_PATH.exists():
        raise AssertionError("src/main.py must exist")
    spec = importlib.util.spec_from_file_location("invalid_json_loader", MAIN_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class InvalidJsonLoaderTest(unittest.TestCase):
    def test_main_raises_json_syntax_error(self):
        loader = load_main_module()

        with self.assertRaisesRegex(
            json.JSONDecodeError,
            "Expecting property name enclosed in double quotes",
        ):
            loader.main()

    def test_run_preserves_the_intentional_failure(self):
        loader = load_main_module()

        with self.assertRaises(json.JSONDecodeError):
            loader.run({})


if __name__ == "__main__":
    unittest.main()
