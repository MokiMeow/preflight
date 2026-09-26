import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from preflight.artifacts import canonical_json, strict_json
from preflight.models import Contract, TOOL_INPUTS


def test_fixture_and_ten_schemas():
    contract = Contract.model_validate(json.loads(Path("config/contract.example.json").read_text()))
    assert len(TOOL_INPUTS) == 10
    assert contract.tables[0].expected_schema.added_columns[0].nullable is False
    for schema in TOOL_INPUTS.values():
        assert schema.model_json_schema()["additionalProperties"] is False


def test_no_unknown_contract_or_duplicate_keys():
    data = json.loads(Path("config/contract.example.json").read_text())
    data["approved"] = True
    with pytest.raises(ValidationError):
        Contract.model_validate(data)
    with pytest.raises(Exception):
        strict_json(b'{"x":{"a":1,"a":2}}')


def test_canonical_order_and_nonfinite():
    assert canonical_json({"b": 2, "a": 1}) == b'{"a":1,"b":2}'
    with pytest.raises(Exception):
        strict_json(b'{"x":NaN}')
