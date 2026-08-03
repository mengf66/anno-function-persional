import json
import unittest

from scripts.configure_feishu_similarity_workflow import configure_workflow


class FakeCli:
    def __init__(self):
        self.calls = []
        self.responses = [
            {"ok": True, "data": {"workflow_id": "wkfNew", "status": "disabled"}},
            {"ok": True, "data": {"workflow_id": "wkfNew", "status": "enabled"}},
        ]

    def run(self, *args):
        self.calls.append(args)
        return self.responses.pop(0)


class ConfigureFeishuSimilarityWorkflowTest(unittest.TestCase):
    def test_configures_and_enables_existing_table(self):
        cli = FakeCli()

        result = configure_workflow(
            cli,
            base_token="BascExisting",
            table_id="tblExisting",
            webhook_url="https://temporary.example/webhook/text-similarity",
            webhook_token="secret-token",
            enable=True,
        )

        self.assertEqual(result, {"workflow_id": "wkfNew", "status": "enabled"})
        self.assertEqual(cli.calls[0][1], "+workflow-create")
        self.assertEqual(cli.calls[1][1], "+workflow-enable")
        body = json.loads(cli.calls[0][cli.calls[0].index("--json") + 1])
        self.assertEqual(body["steps"][0]["data"]["table_name"], "Function查重测试")
        self.assertEqual(
            body["steps"][2]["data"]["url"][0]["value"],
            "https://temporary.example/webhook/text-similarity",
        )


if __name__ == "__main__":
    unittest.main()
