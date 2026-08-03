# Feishu similarity workflow

The workflow calls a public HTTP endpoint after a record's `执行状态` changes to
`待执行`. The endpoint reads that record, runs `text_similarity_checker`, and writes
the result back to the same record.

## 1. Start the webhook

Set one shared secret for both the server and the Feishu workflow:

```bash
export FEISHU_WEBHOOK_TOKEN="replace-with-a-long-random-value"
python3 scripts/feishu_similarity_webhook.py --host 0.0.0.0 --port 8000
```

The externally reachable workflow URL must end with:

```text
/webhook/text-similarity
```

The runtime must have `lark-cli` configured and authenticated for the target Base. Use
`--identity bot` when deploying with an application identity that has access to the Base.

## 2. Create the Base and workflow

In another shell, export the same token and run:

```bash
export FEISHU_WEBHOOK_TOKEN="replace-with-a-long-random-value"
python3 scripts/create_feishu_similarity_base.py \
  --name "Function查重测试-新版" \
  --webhook-url "https://your-public-host/webhook/text-similarity" \
  --enable-workflow
```

New workflows are disabled unless `--enable-workflow` is supplied.

## 3. Trigger a check

Fill `目标文本` and `已有文本`, then set `执行状态` to `待执行`. The workflow
sets the status to `执行中`, invokes the webhook, and the webhook writes:

- `record_id`
- `查重通过`
- `最相似文本`
- `最高相似度`
- `执行状态` (`已完成` or `失败`)
