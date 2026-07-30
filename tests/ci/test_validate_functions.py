from pathlib import Path
import shutil
import tempfile
import unittest

from scripts.validate_functions import discover_functions, validate_repository


FIXTURE = Path(__file__).parent / "fixtures" / "valid"


class RepositoryValidatorTest(unittest.TestCase):
    def make_repo(self):
        temporary = tempfile.TemporaryDirectory()
        root = Path(temporary.name)
        target = root / "function" / "example"
        shutil.copytree(
            FIXTURE,
            target,
            ignore=shutil.ignore_patterns("__pycache__", "*.py[cod]"),
        )
        return temporary, root, target

    def test_valid_repository_passes(self):
        temporary, root, _ = self.make_repo()
        with temporary:
            self.assertEqual(validate_repository(root), [])

    def test_discovers_only_direct_function_children(self):
        temporary, root, _ = self.make_repo()
        with temporary:
            self.assertEqual(
                [path.name for path in discover_functions(root)],
                ["example"],
            )

    def test_rejects_missing_tests(self):
        temporary, root, function = self.make_repo()
        with temporary:
            shutil.rmtree(function / "test")
            findings = validate_repository(root)
            self.assertIn("layout.test.missing", str(findings))

    def test_rejects_forbidden_artifact(self):
        temporary, root, function = self.make_repo()
        with temporary:
            (function / ".env").write_text("TOKEN=secret", encoding="utf-8")
            self.assertIn("layout.artifact.forbidden", str(validate_repository(root)))

    def test_rejects_escaping_symlink(self):
        temporary, root, function = self.make_repo()
        with temporary:
            (function / "escape").symlink_to(Path(temporary.name).parent)
            self.assertIn("layout.symlink.escape", str(validate_repository(root)))

    def test_rejects_failing_test(self):
        temporary, root, function = self.make_repo()
        with temporary:
            (function / "test" / "test.py").write_text(
                "import unittest\n"
                "class Bad(unittest.TestCase):\n"
                "    def test_bad(self): self.fail('boom')\n",
                encoding="utf-8",
            )
            self.assertIn("test.failed", str(validate_repository(root)))

    def test_findings_are_stably_sorted(self):
        temporary, root, function = self.make_repo()
        with temporary:
            (function / ".env").write_text("", encoding="utf-8")
            (function / "src" / "__pycache__").mkdir(exist_ok=True)
            findings = validate_repository(root)
            self.assertEqual(findings, sorted(findings))


if __name__ == "__main__":
    unittest.main()
