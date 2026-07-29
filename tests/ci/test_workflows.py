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

    def test_release_ci(self):
        _, workflow = load_workflow("function-release.yml")
        self.assertIn("workflow_dispatch", workflow["on"])
        self.assertEqual(workflow["on"]["push"]["tags"], ["v*"])
        self.assertEqual(workflow["permissions"], {"contents": "read"})
        self.assertEqual(set(workflow["jobs"]), {"validate", "create", "audit"})
        self.assertEqual(workflow["jobs"]["create"]["needs"], "validate")
        token_step = next(
            step
            for step in workflow["jobs"]["create"]["steps"]
            if step.get("id") == "app-token"
        )
        self.assertEqual(token_step["with"]["repositories"], "anno-function-persional")
        uses = [
            step["uses"]
            for job in workflow["jobs"].values()
            for step in job["steps"]
            if "uses" in step
        ]
        self.assertTrue(uses)
        for action in uses:
            self.assertRegex(action, r"^[^@]+@[0-9a-f]{40}$")


if __name__ == "__main__":
    unittest.main()
