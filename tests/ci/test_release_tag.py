import unittest

from scripts.release_tag import ReleaseError, validate_release


SHA = "a" * 40


class FakeClient:
    def __init__(self):
        self.tags = {"v1": "1" * 40, "v7": "7" * 40}
        self.ancestor = True
        self.check = True
        self.requested_check = None
        self.created = []

    def list_tags(self):
        return dict(self.tags)

    def is_reachable(self, branch, sha):
        return self.ancestor

    def has_successful_check(self, sha, name):
        self.requested_check = name
        return self.check

    def create_annotated_tag(self, version, sha):
        self.created.append((version, sha))


class ReleaseTagTest(unittest.TestCase):
    def test_accepts_next_validated_version(self):
        client = FakeClient()
        decision = validate_release("v8", SHA, "release", client)
        self.assertEqual(decision.version, "v8")
        self.assertEqual(client.requested_check, "strict")
        self.assertEqual(client.created, [])

    def test_rejects_invalid_or_non_increasing_version(self):
        for version in ("8", "v0", "v7", "v6", "v1.2"):
            with self.subTest(version=version):
                with self.assertRaises(ReleaseError):
                    validate_release(version, SHA, "release", FakeClient())

    def test_rejects_existing_tag(self):
        with self.assertRaisesRegex(ReleaseError, "tag.exists"):
            validate_release("v7", SHA, "release", FakeClient())

    def test_rejects_invalid_commit_sha(self):
        with self.assertRaisesRegex(ReleaseError, "commit.invalid"):
            validate_release("v8", "main", "release", FakeClient())

    def test_rejects_off_branch_commit(self):
        client = FakeClient()
        client.ancestor = False
        with self.assertRaisesRegex(ReleaseError, "commit.off_branch"):
            validate_release("v8", SHA, "release", client)

    def test_rejects_commit_without_exact_successful_check(self):
        client = FakeClient()
        client.check = False
        with self.assertRaisesRegex(ReleaseError, "check.missing"):
            validate_release("v8", SHA, "release", client)

    def test_create_mode_creates_one_annotated_tag(self):
        client = FakeClient()
        validate_release("v8", SHA, "release", client, create=True)
        self.assertEqual(client.created, [("v8", SHA)])


if __name__ == "__main__":
    unittest.main()
