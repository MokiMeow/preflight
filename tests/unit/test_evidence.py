import json
from datetime import datetime, timedelta, timezone

import pytest

from preflight.evidence import EvidenceBundle, _digest, _root, canonical, typed_value
from preflight.models import PreflightError, PublicEvidence


def test_type_tags_are_distinct():
    values = [None, 1, "1", "", "null", "a\r\nb", "a\nb", "é", "e\u0301"]
    assert len({canonical(typed_value(v)) for v in values}) == len(values)


def test_utc_microseconds():
    utc = datetime(2026, 1, 1, 0, 0, 0, 123, timezone.utc)
    offset = utc.astimezone(timezone(timedelta(hours=5, minutes=30)))
    assert typed_value(utc) == typed_value(offset)
    assert typed_value(utc)[1] == "2026-01-01T00:00:00.000123Z"


@pytest.mark.parametrize("value", [datetime(2026, 1, 1), 1.0, True, b"x", {}, []])
def test_unsupported_no_stringification(value):
    with pytest.raises(PreflightError, match="UNSUPPORTED_VALUE_TYPE"):
        typed_value(value)


def test_domain_length_and_order():
    assert _digest("a", [b"bc", b"d"]) != _digest("a", [b"b", b"cd"])
    assert _digest("a", [b"x"]) != _digest("b", [b"x"])
    assert _root("x", {b"a": "0" * 64, b"b": "1" * 64}) == _root(
        "x", {b"b": "1" * 64, b"a": "0" * 64}
    )


def test_private_bundle_not_serializable():
    bundle = EvidenceBundle(PublicEvidence(tables=[]), {"secret": "ROW_SENTINEL"}, {})
    assert "ROW_SENTINEL" not in repr(bundle)
    with pytest.raises(TypeError):
        json.dumps(bundle)
