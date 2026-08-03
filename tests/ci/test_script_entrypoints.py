from pathlib import Path
import subprocess
import sys
import unittest


ROOT = Path(__file__).resolve().parents[2]


class ScriptEntrypointTest(unittest.TestCase):
    def assert_help_works(self, script_name):
        completed = subprocess.run(
            [sys.executable, str(ROOT / "scripts" / script_name), "--help"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)

    def test_webhook_direct_entrypoint(self):
        self.assert_help_works("feishu_similarity_webhook.py")

    def test_workflow_config_direct_entrypoint(self):
        self.assert_help_works("configure_feishu_similarity_workflow.py")


if __name__ == "__main__":
    unittest.main()
