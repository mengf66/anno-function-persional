from __future__ import annotations

import keyword
import re
from decimal import Decimal, InvalidOperation
from enum import Enum
from typing import Any, Literal

import yaml
from pydantic import (
    BaseModel,
    ConfigDict,
    Field as PydanticField,
    StrictBool,
    StrictFloat,
    StrictInt,
    StrictStr,
    ValidationError,
)


API_VERSION = "functions.anno.meetchances.com/v1alpha1"


class ContractError(ValueError):
    def __init__(self, code: str, path: str, message: str) -> None:
        self.code = code
        self.path = path
        self.message = message
        super().__init__(f"{code} at {path}: {message}")


def _camel(value: str) -> str:
    head, *tail = value.split("_")
    return head + "".join(item.capitalize() for item in tail)


class Model(BaseModel):
    model_config = ConfigDict(
        alias_generator=_camel,
        populate_by_name=True,
        extra="forbid",
    )


class DataType(str, Enum):
    STRING = "string"
    INT = "int"
    FLOAT = "float"
    BOOL = "bool"
    ARRAY = "array"


class SourceType(str, Enum):
    FEISHU = "feishu"
    MANUAL = "manual"


class EnumOption(Model):
    label: str
    value: str | int | float | bool


class TextInput(Model):
    type: Literal["textInput"]
    min_length: int | None = PydanticField(default=None, ge=0)
    max_length: int | None = PydanticField(default=None, ge=0)
    pattern: str | None = None


class NumberInput(Model):
    type: Literal["numberInput"]
    minimum: int | float | None = None
    maximum: int | float | None = None
    step: int | float | None = PydanticField(default=None, gt=0)
    precision: int | None = PydanticField(default=None, ge=0)


class RangeInput(Model):
    type: Literal["range"]
    minimum: int | float
    maximum: int | float
    step: int | float = PydanticField(gt=0)


class ChoiceInput(Model):
    type: Literal["select", "multiSelect"]
    options: list[EnumOption] | None = None
    provider: str | None = None
    minimum_selections: int | None = PydanticField(default=None, ge=0)
    maximum_selections: int | None = PydanticField(default=None, ge=0)


Ui = TextInput | NumberInput | RangeInput | ChoiceInput
Scalar = StrictStr | StrictInt | StrictFloat | StrictBool


class Field(Model):
    key: str
    name: str
    description: str
    data_type: DataType
    item_type: DataType | None = None
    required: bool


class ParameterField(Field):
    source_type: SourceType
    default: Scalar | list[Scalar] | None = None
    ui: list[Ui] = PydanticField(default_factory=list, discriminator=None)


class ReturnField(Field):
    pass


class FunctionExample(Model):
    name: str
    parameters: dict[str, Scalar | list[Scalar]]
    returns: dict[str, Scalar | list[Scalar]]


class Metadata(Model):
    name: str
    owner: str
    description: str
    examples: list[FunctionExample] = PydanticField(default_factory=list)


class FunctionDefinition(Model):
    api_version: Literal[API_VERSION]
    kind: Literal["Function"]
    metadata: Metadata
    parameters: list[ParameterField]
    returns: list[ReturnField]


def parse_definition(raw: str) -> FunctionDefinition:
    try:
        payload = yaml.safe_load(raw)
        definition = FunctionDefinition.model_validate(payload)
    except (yaml.YAMLError, ValidationError, TypeError, ValueError) as exc:
        path = "definition"
        if isinstance(exc, ValidationError) and exc.errors():
            path = ".".join(str(item) for item in exc.errors()[0]["loc"])
        raise ContractError("schema.invalid", path, str(exc)) from exc
    _validate_definition(definition)
    return definition


def _validate_definition(definition: FunctionDefinition) -> None:
    _unique_keys(definition.parameters, "parameter")
    _unique_keys(definition.returns, "return")
    for index, field in enumerate(definition.parameters):
        path = f"parameters[{index}]"
        if not field.key.isidentifier() or keyword.iskeyword(field.key):
            raise ContractError("parameter.key.invalid", f"{path}.key", field.key)
        _validate_field(field, path)
        if field.source_type == SourceType.MANUAL and not field.ui:
            raise ContractError("parameter.ui.required", f"{path}.ui", field.key)
        if field.source_type == SourceType.FEISHU and field.ui:
            raise ContractError("parameter.ui.forbidden", f"{path}.ui", field.key)
        rules = _validate_ui(field, path)
        if field.default is not None:
            validate_value(field, field.default, "parameter.default.type", f"{path}.default")
            _validate_rules(
                field,
                field.default,
                rules,
                "parameter.default.rule",
                f"{path}.default",
            )
    for index, field in enumerate(definition.returns):
        _validate_field(field, f"returns[{index}]")
    for index, example in enumerate(definition.metadata.examples):
        _validate_example(definition, example, index)


def _unique_keys(fields: list[Field], section: str) -> None:
    seen: set[str] = set()
    for field in fields:
        if field.key in seen:
            raise ContractError(f"{section}.key.duplicate", section, field.key)
        seen.add(field.key)


def _validate_field(field: Field, path: str) -> None:
    if field.data_type == DataType.ARRAY and field.item_type is None:
        raise ContractError("field.item_type.required", f"{path}.itemType", field.key)
    if field.data_type != DataType.ARRAY and field.item_type is not None:
        raise ContractError("field.item_type.forbidden", f"{path}.itemType", field.key)
    if field.item_type == DataType.ARRAY:
        raise ContractError("field.item_type.invalid", f"{path}.itemType", "nested arrays")


def _validate_ui(field: ParameterField, path: str) -> dict[str, object]:
    rules: dict[str, object] = {}

    def add(name: str, value: object | None, ui_path: str) -> None:
        if value is None:
            return
        if name in rules and rules[name] != value:
            raise ContractError("ui.rule.conflict", ui_path, name)
        rules[name] = value

    for index, ui in enumerate(field.ui):
        ui_path = f"{path}.ui[{index}]"
        if isinstance(ui, TextInput):
            if field.data_type != DataType.STRING:
                raise ContractError("ui.type.invalid", ui_path, "textInput requires string")
            if ui.min_length is not None and ui.max_length is not None and ui.min_length > ui.max_length:
                raise ContractError("ui.bounds.invalid", ui_path, "minimum exceeds maximum")
            if ui.pattern is not None:
                try:
                    re.compile(ui.pattern)
                except re.error as exc:
                    raise ContractError("ui.pattern.invalid", f"{ui_path}.pattern", str(exc)) from exc
            add("min_length", ui.min_length, ui_path)
            add("max_length", ui.max_length, ui_path)
            add("pattern", ui.pattern, ui_path)
        elif isinstance(ui, (NumberInput, RangeInput)):
            if field.data_type not in {DataType.INT, DataType.FLOAT}:
                raise ContractError("ui.type.invalid", ui_path, "numeric UI requires number")
            if (
                isinstance(ui, NumberInput)
                and ui.precision is not None
                and field.data_type != DataType.FLOAT
            ):
                raise ContractError("ui.precision.invalid", ui_path, "precision requires float")
            if ui.minimum is not None and ui.maximum is not None and ui.minimum > ui.maximum:
                raise ContractError("ui.bounds.invalid", ui_path, "minimum exceeds maximum")
            add("minimum", ui.minimum, ui_path)
            add("maximum", ui.maximum, ui_path)
            add("step", ui.step, ui_path)
            if isinstance(ui, NumberInput):
                add("precision", ui.precision, ui_path)
        elif isinstance(ui, ChoiceInput):
            if (ui.options is None) == (ui.provider is None):
                raise ContractError("ui.choice.source", ui_path, "exactly one source is required")
            if ui.options == []:
                raise ContractError("ui.choice.empty", ui_path, "options cannot be empty")
            if ui.type == "select" and field.data_type == DataType.ARRAY:
                raise ContractError("ui.select.invalid", ui_path, "select requires scalar")
            if ui.type == "multiSelect" and field.data_type != DataType.ARRAY:
                raise ContractError("ui.multi_select.invalid", ui_path, "multiSelect requires array")
            if ui.type == "select" and (
                ui.minimum_selections is not None or ui.maximum_selections is not None
            ):
                raise ContractError("ui.select.invalid", ui_path, "selection bounds require multiSelect")
            if (
                ui.minimum_selections is not None
                and ui.maximum_selections is not None
                and ui.minimum_selections > ui.maximum_selections
            ):
                raise ContractError("ui.bounds.invalid", ui_path, "minimum exceeds maximum")
            if ui.options is not None:
                option_type = (
                    field.item_type
                    if field.data_type == DataType.ARRAY
                    else field.data_type
                )
                values: list[Scalar] = []
                identities: set[tuple[type[object], str]] = set()
                for option in ui.options:
                    if not _matches(option.value, option_type):
                        raise ContractError("ui.option.type", ui_path, option.label)
                    normalized = (
                        float(option.value)
                        if option_type == DataType.FLOAT
                        else option.value
                    )
                    identity = (type(normalized), repr(normalized))
                    if identity in identities:
                        raise ContractError("ui.option.duplicate", ui_path, repr(normalized))
                    identities.add(identity)
                    values.append(normalized)
                add("options", values, ui_path)
            else:
                add("provider", ui.provider, ui_path)
            if ui.type == "multiSelect":
                add("minimum_selections", ui.minimum_selections, ui_path)
                add("maximum_selections", ui.maximum_selections, ui_path)
    for lower, upper in (
        ("min_length", "max_length"),
        ("minimum", "maximum"),
        ("minimum_selections", "maximum_selections"),
    ):
        if lower in rules and upper in rules and rules[lower] > rules[upper]:
            raise ContractError("ui.bounds.invalid", path, f"{lower} exceeds {upper}")
    return rules


def validate_value(field: Field, value: object, code: str = "value.type", path: str = "value") -> None:
    if field.data_type == DataType.ARRAY:
        if not isinstance(value, list):
            raise ContractError(code, path, f"{field.key} must be array")
        for index, item in enumerate(value):
            if not _matches(item, field.item_type):
                raise ContractError(code, f"{path}[{index}]", f"{field.key} item type")
        return
    if not _matches(value, field.data_type):
        raise ContractError(code, path, f"{field.key} must be {field.data_type.value}")


def _matches(value: object, data_type: DataType | None) -> bool:
    if data_type == DataType.STRING:
        return isinstance(value, str)
    if data_type == DataType.BOOL:
        return isinstance(value, bool)
    if data_type == DataType.INT:
        return isinstance(value, int) and not isinstance(value, bool)
    if data_type == DataType.FLOAT:
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    return False


def _validate_example(
    definition: FunctionDefinition,
    example: FunctionExample,
    index: int,
) -> None:
    for section, fields, values in (
        ("parameter", definition.parameters, example.parameters),
        ("return", definition.returns, example.returns),
    ):
        by_key = {field.key: field for field in fields}
        unknown = sorted(set(values) - set(by_key))
        if unknown:
            raise ContractError(f"example.{section}.unknown", f"examples[{index}]", unknown[0])
        missing = [field.key for field in fields if field.required and field.key not in values]
        if missing:
            raise ContractError(f"example.{section}.missing", f"examples[{index}]", missing[0])
        for key, value in values.items():
            validate_value(
                by_key[key],
                value,
                f"example.{section}.type",
                f"examples[{index}].{section}s.{key}",
            )
            if section == "parameter":
                rules = _validate_ui(by_key[key], f"parameters.{key}")
                _validate_rules(
                    by_key[key],
                    value,
                    rules,
                    "example.parameter.rule",
                    f"examples[{index}].parameters.{key}",
                )


def _validate_rules(
    field: Field,
    value: object,
    rules: dict[str, object],
    code: str,
    path: str,
) -> None:
    def fail(message: str) -> None:
        raise ContractError(code, path, message)

    if isinstance(value, str):
        if "min_length" in rules and len(value) < rules["min_length"]:
            fail("value is shorter than minLength")
        if "max_length" in rules and len(value) > rules["max_length"]:
            fail("value is longer than maxLength")
        if "pattern" in rules and re.search(str(rules["pattern"]), value) is None:
            fail("value does not match pattern")
    if type(value) in (int, float):
        if "minimum" in rules and value < rules["minimum"]:
            fail("value is below minimum")
        if "maximum" in rules and value > rules["maximum"]:
            fail("value is above maximum")
        if "step" in rules:
            origin = rules.get("minimum", 0)
            try:
                difference = Decimal(str(value)) - Decimal(str(origin))
                if difference % Decimal(str(rules["step"])) != 0:
                    fail("value does not align with step")
            except InvalidOperation:
                fail("invalid numeric step")
        if "precision" in rules:
            places = max(0, -Decimal(str(value)).as_tuple().exponent)
            if places > rules["precision"]:
                fail("value exceeds precision")
    if isinstance(value, list):
        if "minimum_selections" in rules and len(value) < rules["minimum_selections"]:
            fail("too few selections")
        if "maximum_selections" in rules and len(value) > rules["maximum_selections"]:
            fail("too many selections")
    if "options" in rules:
        choices = rules["options"]
        if isinstance(value, list):
            if any(item not in choices for item in value):
                fail(f"value is not in options for field: {field.key}")
        elif value not in choices:
            fail(f"value is not in options for field: {field.key}")
