import unittest

from scripts.feishu_similarity_webhook import (
    SimilarityRequest,
    WebhookError,
    process_similarity_request,
)


class FakeBaseClient:
    def __init__(self, record):
        self.record = record
        self.updates = []

    def get_record(self, request):
        return self.record

    def update_record(self, request, fields):
        self.updates.append(dict(fields))


class FeishuSimilarityWebhookTest(unittest.TestCase):
    def setUp(self):
        self.request = SimilarityRequest("BascNew", "tblNew", "recNew")

    def test_processes_record_and_writes_function_results(self):
        client = FakeBaseClient(
            {
                "目标文本": "Python makes data processing easy",
                "已有文本": ["Python makes data processing very easy"],
                "执行状态": ["执行中"],
            }
        )

        result = process_similarity_request(client, self.request)

        self.assertEqual(result["status"], "completed")
        self.assertEqual(
            client.updates,
            [
                {
                    "record_id": "recNew",
                    "查重通过": False,
                    "最相似文本": "Python makes data processing very easy",
                    "最高相似度": 0.9296,
                    "执行状态": "已完成",
                }
            ],
        )

    def test_empty_target_marks_record_failed(self):
        client = FakeBaseClient(
            {"目标文本": "", "已有文本": [], "执行状态": ["执行中"]}
        )

        with self.assertRaisesRegex(WebhookError, "目标文本不能为空"):
            process_similarity_request(client, self.request)

        self.assertEqual(client.updates, [{"执行状态": "失败"}])

    def test_completed_record_is_idempotent(self):
        client = FakeBaseClient(
            {"目标文本": "text", "已有文本": [], "执行状态": ["已完成"]}
        )

        result = process_similarity_request(client, self.request)

        self.assertEqual(result["status"], "already_completed")
        self.assertEqual(client.updates, [])

    def test_request_requires_all_identifiers(self):
        with self.assertRaisesRegex(WebhookError, "record_id is required"):
            SimilarityRequest.from_payload(
                {"app_token": "BascNew", "table_id": "tblNew"}
            )


if __name__ == "__main__":
    unittest.main()
