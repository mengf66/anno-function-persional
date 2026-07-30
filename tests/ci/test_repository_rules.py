import unittest

from scripts.configure_repository_rules import (
    RuleError,
    desired_rulesets,
    reconcile,
)


class RepositoryRulesTest(unittest.TestCase):
    def test_desired_rules_split_tag_creation_from_immutability(self):
        rules = desired_rulesets("release", 42)
        self.assertEqual(
            [rule["name"] for rule in rules],
            [
                "anno-function-release-branch",
                "anno-function-version-creation",
                "anno-function-version-immutable",
            ],
        )
        creation = rules[1]
        immutable = rules[2]
        self.assertEqual([rule["type"] for rule in creation["rules"]], ["creation"])
        self.assertEqual(
            creation["bypass_actors"],
            [{"actor_id": 42, "actor_type": "Integration", "bypass_mode": "always"}],
        )
        self.assertEqual(
            [rule["type"] for rule in immutable["rules"]],
            ["deletion", "update"],
        )
        self.assertEqual(immutable["bypass_actors"], [])

    def test_branch_rule_requires_pr_and_exact_check(self):
        branch = desired_rulesets("release", 42)[0]
        types = {rule["type"]: rule for rule in branch["rules"]}
        self.assertIn("pull_request", types)
        checks = types["required_status_checks"]["parameters"]
        self.assertEqual(
            checks["required_status_checks"],
            [{"context": "Function CI / strict"}],
        )
        self.assertTrue(checks["strict_required_status_checks_policy"])
        self.assertIn("deletion", types)
        self.assertIn("non_fast_forward", types)
        self.assertEqual(branch["bypass_actors"], [])

    def test_reconcile_creates_only_missing_managed_rules(self):
        current = [{"id": 9, "name": "unrelated", "enforcement": "active"}]
        changes = reconcile(current, desired_rulesets("release", 42))
        self.assertEqual(len(changes.create), 3)
        self.assertEqual(changes.update, [])
        self.assertEqual(changes.unchanged, [])

    def test_reconcile_is_idempotent(self):
        desired = desired_rulesets("release", 42)
        current = [{"id": index + 1, **rule} for index, rule in enumerate(desired)]
        changes = reconcile(current, desired)
        self.assertEqual(changes.create, [])
        self.assertEqual(changes.update, [])
        self.assertEqual(len(changes.unchanged), 3)

    def test_reconcile_updates_changed_managed_rule_only(self):
        desired = desired_rulesets("release", 42)
        current = [{"id": 1, **desired[0]}, {"id": 2, **desired[1]}, {"id": 3, **desired[2]}]
        current[1]["enforcement"] = "disabled"
        changes = reconcile(current, desired)
        self.assertEqual([item[0] for item in changes.update], [2])

    def test_reconcile_rejects_duplicate_managed_names(self):
        current = [
            {"id": 1, "name": "anno-function-release-branch"},
            {"id": 2, "name": "anno-function-release-branch"},
        ]
        with self.assertRaisesRegex(RuleError, "ruleset.ambiguous"):
            reconcile(current, desired_rulesets("release", 42))

    def test_inputs_are_required(self):
        with self.assertRaises(RuleError):
            desired_rulesets("", 42)
        with self.assertRaises(RuleError):
            desired_rulesets("release", 0)


if __name__ == "__main__":
    unittest.main()
