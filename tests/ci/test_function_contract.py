from pathlib import Path
import unittest

from scripts.function_contract import ContractError, parse_definition


FIXTURE = Path(__file__).parent / "fixtures" / "valid" / "meta.yaml"


def valid_yaml() -> str:
    return FIXTURE.read_text(encoding="utf-8")


class FunctionContractTest(unittest.TestCase):
    def test_accepts_complete_definition(self):
        definition = parse_definition(valid_yaml())
        self.assertEqual(definition.metadata.name, "example")
        self.assertEqual([field.key for field in definition.parameters], ["text", "limit"])

    def test_rejects_unknown_fields(self):
        raw = valid_yaml().replace("  owner: ci", "  owner: ci\n  surprise: true")
        with self.assertRaisesRegex(ContractError, "schema.invalid.*metadata.surprise"):
            parse_definition(raw)

    def test_rejects_duplicate_parameter_keys(self):
        raw = valid_yaml().replace("  - key: limit", "  - key: text")
        with self.assertRaisesRegex(ContractError, "parameter.key.duplicate"):
            parse_definition(raw)

    def test_rejects_non_python_parameter_key(self):
        raw = valid_yaml().replace("key: text", "key: class", 1)
        with self.assertRaisesRegex(ContractError, "parameter.key.invalid"):
            parse_definition(raw)

    def test_bool_is_not_accepted_as_int_default(self):
        raw = valid_yaml().replace("    default: 3", "    default: true")
        with self.assertRaisesRegex(ContractError, "parameter.default.type"):
            parse_definition(raw)

    def test_array_requires_item_type(self):
        raw = valid_yaml().replace("    itemType: int\n", "")
        with self.assertRaisesRegex(ContractError, "field.item_type.required"):
            parse_definition(raw)

    def test_manual_parameter_requires_ui(self):
        raw = valid_yaml().replace(
            "    ui:\n      - type: numberInput\n        minimum: 0\n",
            "",
        )
        with self.assertRaisesRegex(ContractError, "parameter.ui.required"):
            parse_definition(raw)

    def test_feishu_parameter_rejects_ui(self):
        raw = valid_yaml().replace(
            "    required: true\n  - key: limit",
            "    required: true\n    ui:\n      - type: textInput\n  - key: limit",
            1,
        )
        with self.assertRaisesRegex(ContractError, "parameter.ui.forbidden"):
            parse_definition(raw)

    def test_rejects_invalid_regex(self):
        raw = valid_yaml().replace(
            "      - type: numberInput\n        minimum: 0",
            "      - type: textInput\n        pattern: '[invalid'",
        ).replace("    dataType: int", "    dataType: string", 1)
        with self.assertRaisesRegex(ContractError, "ui.pattern.invalid"):
            parse_definition(raw)

    def test_rejects_invalid_example_value(self):
        raw = valid_yaml().replace("        limit: 3", "        limit: true")
        with self.assertRaisesRegex(ContractError, "example.parameter.type"):
            parse_definition(raw)

    def test_rejects_missing_required_example_return(self):
        raw = valid_yaml().replace("        accepted: true\n", "")
        with self.assertRaisesRegex(ContractError, "example.return.missing"):
            parse_definition(raw)

    def test_rejects_conflicting_rules_across_ui_controls(self):
        raw = valid_yaml().replace(
            "      - type: numberInput\n        minimum: 0",
            "      - type: numberInput\n        minimum: 0\n"
            "      - type: range\n        minimum: 1\n        maximum: 10\n        step: 1",
        )
        with self.assertRaisesRegex(ContractError, "ui.rule.conflict"):
            parse_definition(raw)

    def test_rejects_default_outside_numeric_bounds(self):
        raw = valid_yaml().replace("        minimum: 0", "        minimum: 4")
        with self.assertRaisesRegex(ContractError, "parameter.default.rule"):
            parse_definition(raw)

    def test_rejects_default_not_aligned_to_step(self):
        raw = valid_yaml().replace(
            "        minimum: 0",
            "        minimum: 0\n        step: 2",
        )
        with self.assertRaisesRegex(ContractError, "parameter.default.rule"):
            parse_definition(raw)

    def test_rejects_precision_on_integer_field(self):
        raw = valid_yaml().replace(
            "        minimum: 0",
            "        minimum: 0\n        precision: 2",
        )
        with self.assertRaisesRegex(ContractError, "ui.precision.invalid"):
            parse_definition(raw)

    def test_rejects_select_for_array_and_multiselect_for_scalar(self):
        select_array = valid_yaml().replace(
            "      - type: numberInput\n        minimum: 0",
            "      - type: select\n        provider: catalog/v1",
        ).replace("    dataType: int", "    dataType: array\n    itemType: int", 1)
        with self.assertRaisesRegex(ContractError, "ui.select.invalid"):
            parse_definition(select_array)

        multi_scalar = valid_yaml().replace(
            "      - type: numberInput\n        minimum: 0",
            "      - type: multiSelect\n        provider: catalog/v1",
        )
        with self.assertRaisesRegex(ContractError, "ui.multi_select.invalid"):
            parse_definition(multi_scalar)

    def test_rejects_duplicate_or_invalid_static_options(self):
        raw = valid_yaml().replace(
            "      - type: numberInput\n        minimum: 0",
            "      - type: select\n"
            "        options:\n"
            "          - {label: One, value: 1}\n"
            "          - {label: Again, value: 1}",
        )
        with self.assertRaisesRegex(ContractError, "ui.option.duplicate"):
            parse_definition(raw)


if __name__ == "__main__":
    unittest.main()
