from pathlib import Path
import tempfile
import textwrap
import unittest

from scripts.function_contract import parse_definition
from scripts.function_executor import EntrypointError, validate_entrypoint
from tests.ci.test_function_contract import valid_yaml


class FunctionExecutorTest(unittest.TestCase):
    def run_source(self, source: str, timeout: float = 2):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "src").mkdir()
            (root / "src" / "main.py").write_text(textwrap.dedent(source), encoding="utf-8")
            validate_entrypoint(root, parse_definition(valid_yaml()), timeout=timeout)

    def test_accepts_sync_main(self):
        self.run_source(
            """
            def main(text, limit=3):
                return {"accepted": len(text) <= limit, "scores": [len(text), limit]}
            """
        )

    def test_accepts_async_main(self):
        self.run_source(
            """
            async def main(text, limit=3):
                return {"accepted": True, "scores": [1, 2]}
            """
        )

    def test_rejects_cli_main_without_declared_parameters(self):
        with self.assertRaisesRegex(EntrypointError, "entrypoint.signature"):
            self.run_source("def main(): return 0")

    def test_rejects_missing_main(self):
        with self.assertRaisesRegex(EntrypointError, "entrypoint.missing"):
            self.run_source("VALUE = 1")

    def test_rejects_extra_return(self):
        with self.assertRaisesRegex(EntrypointError, "entrypoint.return.unknown"):
            self.run_source(
                """
                def main(text, limit=3):
                    return {"accepted": True, "scores": [1], "extra": 1}
                """
            )

    def test_rejects_bool_as_integer_array_item(self):
        with self.assertRaisesRegex(EntrypointError, "entrypoint.return.type"):
            self.run_source(
                """
                def main(text, limit=3):
                    return {"accepted": True, "scores": [True]}
                """
            )

    def test_rejects_import_failure(self):
        with self.assertRaisesRegex(EntrypointError, "entrypoint.import"):
            self.run_source("raise RuntimeError('boom')")

    def test_rejects_timeout(self):
        with self.assertRaisesRegex(EntrypointError, "entrypoint.timeout"):
            self.run_source(
                """
                import time
                def main(text, limit=3):
                    time.sleep(5)
                    return {"accepted": True, "scores": [1]}
                """,
                timeout=0.1,
            )


if __name__ == "__main__":
    unittest.main()
