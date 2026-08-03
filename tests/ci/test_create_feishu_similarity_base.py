import json
import unittest
from unittest.mock import patch

from scripts.create_feishu_similarity_base import (
    TABLE_FIELDS,
    TABLE_NAME,
    CreatedBase,
    build_workflow,
    create_similarity_base,
)


class FakeCli:
    dry_run = False

    def __init__(self):
        self.calls = []
        self.responses = [
            {
                "ok": True,
                "data": {
                    "base": {
                        "base_token": "BascNew",
                        "url": "https://example.feishu.cn/base/BascNew",
                    }
                },
            },
            {"ok": True, "data": {"table": {"table_id": "tblNew"}}},
            {
                "ok": True,
                "data": {"workflow_id": "wkfNew", "status": "disabled"},
            },
            {"ok": True, "data": {"workflow_id": "wkfNew", "status": "enabled"}},
        ]

    def run(self, *args):
        self.calls.append(args)
        return self.responses.pop(0)


class CreateFeishuSimilarityBaseTest(unittest.TestCase):
    def test_table_schema_matches_similarity_function_contract(self):
        self.assertEqual(TABLE_NAME, "Function查重测试")
        self.assertEqual(
            [field["name"] for field in TABLE_FIELDS],
            [
                "record_id",
                "目标文本",
                "执行状态",
                "最相似文本",
                "查重通过",
                "最高相似度",
                "用例名称",
                "已有文本",
            ],
        )

    @patch("scripts.create_feishu_similarity_base.uuid.uuid4")
    def test_workflow_uses_new_base_table_and_trigger_record(self, uuid4):
        uuid4.return_value.hex = "client-token"
        workflow = build_workflow(
            "BascNew",
            "tblNew",
            "https://hook.example/run",
            "secret-token",
        )

        self.assertEqual(workflow["client_token"], "client-token")
        self.assertEqual(workflow["steps"][0]["type"], "SetRecordTrigger")
        self.assertEqual(workflow["steps"][1]["type"], "SetRecordAction")
        http_step = workflow["steps"][2]
        self.assertEqual(http_step["type"], "HTTPClientAction")
        self.assertEqual(
            http_step["data"]["url"][0]["value"], "https://hook.example/run"
        )
        self.assertEqual(
            http_step["data"]["headers"][1]["value"][0]["value"],
            "secret-token",
        )
        raw_body = http_step["data"]["raw_body"]
        self.assertIn('"app_token":"BascNew"', raw_body[0]["value"])
        self.assertIn('"table_id":"tblNew"', raw_body[0]["value"])
        self.assertEqual(
            raw_body[1]["value"], "$.trigger_pending_similarity_check.recordId"
        )

    def test_create_builds_table_workflow_and_enables_on_request(self):
        cli = FakeCli()
        result = create_similarity_base(
            cli,
            base_name="新查重测试",
            webhook_url="https://hook.example/run",
            webhook_token="secret-token",
            enable_workflow=True,
        )

        self.assertEqual(
            result,
            CreatedBase(
                base_token="BascNew",
                base_url="https://example.feishu.cn/base/BascNew",
                table_id="tblNew",
                workflow_id="wkfNew",
                workflow_status="enabled",
            ),
        )
        self.assertEqual([call[1] for call in cli.calls], [
            "+base-create",
            "+table-create",
            "+workflow-create",
            "+workflow-enable",
        ])
        fields_arg = cli.calls[1][cli.calls[1].index("--fields") + 1]
        self.assertEqual(json.loads(fields_arg), TABLE_FIELDS)
        workflow_arg = cli.calls[2][cli.calls[2].index("--json") + 1]
        self.assertEqual(json.loads(workflow_arg)["steps"][2]["type"], "HTTPClientAction")


if __name__ == "__main__":
    unittest.main()
