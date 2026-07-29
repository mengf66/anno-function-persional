from pathlib import Path
import re
import unittest

import yaml


ROOT = Path(__file__).resolve().parents[2]


def load_workflow(name: str):
    path = ROOT / ".github" / "workflows" / name
    return path, yaml.load(path.read_text(encoding="utf-8"), Loader=yaml.BaseLoader)


class WorkflowTest(unittest.TestCase):
    def test_branch_ci(self):
        path, workflow = load_workflow("function-ci.yml")
        self.assertIn("push", workflow["on"])
        self.assertNotIn("branches", workflow["on"]["push"] or {})
        self.assertIn("pull_request", workflow["on"])
        self.assertEqual(workflow["permissions"], {"contents": "read"})
        job = workflow["jobs"]["strict"]
        self.assertEqual(job["name"], "strict")
        self.assertEqual(job["timeout-minutes"], "15")
        self.assertEqual(workflow["concurrency"]["cancel-in-progress"], "true")
        commands = "\n".join(
            step.get("run", "") for step in job["steps"] if "run" in step
        )
        self.assertLess(commands.index("tests/ci"), commands.index("validate_functions.py"))
        self.assertIn("python-version: '3.11'", path.read_text(encoding="utf-8"))
        for step in job["steps"]:
            if "uses" in step:
                self.assertRegex(step["uses"], r"^[^@]+@[0-9a-f]{40}$")


if __name__ == "__main__":
    unittest.main()
