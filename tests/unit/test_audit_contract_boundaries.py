import base64
import builtins
import hashlib
import json
import socket
from pathlib import Path
from uuid import uuid4

import boto3
import psycopg
import pytest
from typer.testing import CliRunner

from preflight.artifacts import canonical_json, sha256
from preflight.cli import app
from preflight.config import Settings
from preflight.offline import ReportVerificationError, verify_report
from preflight.service import RehearsalService
from tests.unit.test_reports import mutate_and_rehash, passing_payload, report_bytes

ROOT = Path(__file__).parents[2]
RUNNER = CliRunner()


class NoRuntimeEffects:
    def __init__(self):
        self.calls: list[str] = []

    def __getattr__(self, name):
        def forbidden(*_args, **_kwargs):
            self.calls.append(name)
            raise AssertionError(f"unexpected runtime call: {name}")

        return forbidden


def contract() -> dict:
    return json.loads((ROOT / "config/contract.example.json").read_text(encoding="utf-8"))


def registration(
    service: RehearsalService,
    raw: bytes,
    *,
    as_text: bool = False,
    expected_digest: str | None = None,
    contract_value: dict | None = None,
) -> dict:
    arguments = {
        "request_id": str(uuid4()),
        "expected_migration_sha256": expected_digest or hashlib.sha256(raw).hexdigest(),
        "contract": contract_value or contract(),
        "operator_id": "audit-unit",
    }
    if as_text:
        arguments["sql_text"] = raw.decode("utf-8")
    else:
        arguments["sql_utf8_b64"] = base64.b64encode(raw).decode("ascii")
    return service.call("register_candidate", arguments)


@pytest.mark.parametrize("as_text", [False, True], ids=["base64", "text"])
def test_u01_registration_preserves_exact_utf8_crlf_comment_and_trailing_newline(
    tmp_path, as_text
):
    runtime = NoRuntimeEffects()
    service = RehearsalService(Settings(state_dir=tmp_path), runtime=runtime)
    raw = (
        "-- Unicode snowman ☃; COMMIT remains a comment\r\n"
        "UPDATE public.customers SET email='x;COMMIT' WHERE id=1;\r\n"
    ).encode("utf-8")

    result = registration(service, raw, as_text=as_text)

    assert result["ok"] is True
    assert result["data"]["migration_sha256"] == hashlib.sha256(raw).hexdigest()
    candidate_id = result["data"]["candidate_id"]
    assert service.candidate(candidate_id)[1] == raw
    assert runtime.calls == []


@pytest.mark.parametrize(
    ("arguments", "error_code"),
    [
        (
            {
                "sql_text": "UPDATE public.customers SET email='x'",
                "expected_migration_sha256": "0" * 64,
            },
            "MIGRATION_HASH_MISMATCH",
        ),
        (
            {
                "sql_utf8_b64": base64.b64encode(b"\xff\xfe").decode("ascii"),
                "expected_migration_sha256": hashlib.sha256(b"\xff\xfe").hexdigest(),
            },
            "INVALID_SQL_ENCODING",
        ),
        (
            {"sql_utf8_b64": "!!!", "expected_migration_sha256": hashlib.sha256(b"").hexdigest()},
            "INVALID_SQL_ENCODING",
        ),
        (
            {
                "sql_text": "UPDATE public.customers SET email='x'\x00",
                "expected_migration_sha256": hashlib.sha256(
                    b"UPDATE public.customers SET email='x'\x00"
                ).hexdigest(),
            },
            "SQL_SIZE_OR_NUL",
        ),
        ({"sql_text": "", "expected_migration_sha256": hashlib.sha256(b"").hexdigest()}, "SQL_SIZE_OR_NUL"),
        (
            {
                "sql_text": " " * 65_537,
                "expected_migration_sha256": hashlib.sha256(b" " * 65_537).hexdigest(),
            },
            "INVALID_INPUT",
        ),
    ],
    ids=["wrong-hash", "invalid-utf8", "invalid-base64", "nul", "empty", "oversize"],
)
def test_u02_registration_rejects_invalid_bytes_before_runtime_or_publication(
    tmp_path, arguments, error_code
):
    runtime = NoRuntimeEffects()
    service = RehearsalService(Settings(state_dir=tmp_path), runtime=runtime)
    arguments.update(
        request_id=str(uuid4()), contract=contract(), operator_id="audit-unit"
    )

    result = service.call("register_candidate", arguments)

    assert result["ok"] is False
    assert result["error_code"] == error_code
    assert service.store.list_records("candidate") == []
    assert service.store.list_runs() == []
    assert runtime.calls == []


def test_u03_canonical_contract_hash_and_raw_file_hash_labels_are_distinct(tmp_path):
    value = contract()
    compact = tmp_path / "compact.json"
    pretty = tmp_path / "pretty.json"
    compact.write_text(json.dumps(value, separators=(",", ":")), encoding="utf-8")
    pretty.write_text(json.dumps(value, indent=4, sort_keys=True) + "\n", encoding="utf-8")
    sql = tmp_path / "candidate.sql"
    sql.write_bytes((ROOT / "fixtures/good.sql").read_bytes())

    requests = []
    labels = []
    for index, contract_path in enumerate((compact, pretty)):
        output = tmp_path / f"request-{index}.json"
        invocation = RUNNER.invoke(
            app,
            [
                "candidate",
                "intake",
                "--sql",
                str(sql),
                "--contract",
                str(contract_path),
                "--output",
                str(output),
                "--operator-id",
                "audit-unit",
            ],
        )
        assert invocation.exit_code == 0, invocation.stdout
        requests.append(json.loads(output.read_text(encoding="utf-8")))
        labels.append(json.loads(invocation.stdout))

    runtime = NoRuntimeEffects()
    service = RehearsalService(Settings(state_dir=tmp_path / "state"), runtime=runtime)
    registered = [service.call("register_candidate", request) for request in requests]

    expected_contract_hash = sha256(canonical_json(value))
    assert {item["data"]["contract_sha256"] for item in registered} == {
        expected_contract_hash
    }
    assert {item["contract_sha256"] for item in labels} == {expected_contract_hash}
    assert labels[0]["raw_contract_sha256"] != labels[1]["raw_contract_sha256"]
    assert labels[0]["raw_contract_sha256"] == sha256(compact.read_bytes())
    assert labels[1]["raw_contract_sha256"] == sha256(pretty.read_bytes())
    assert runtime.calls == []


@pytest.mark.parametrize(
    "mutation",
    [
        lambda value: value["tables"][0]["checks"].append({"type": "arbitrary_sql"}),
        lambda value: value["tables"][0].update(primary_key=[]),
        lambda value: value["tables"][0].update(primary_key=["id"], preserve_columns=["email"]),
    ],
    ids=["unsupported-check", "missing-primary-key", "unpreserved-primary-key"],
)
def test_u04_unsupported_checks_and_primary_key_coverage_fail_closed(tmp_path, mutation):
    runtime = NoRuntimeEffects()
    service = RehearsalService(Settings(state_dir=tmp_path), runtime=runtime)
    value = contract()
    mutation(value)
    raw = (ROOT / "fixtures/good.sql").read_bytes()

    result = registration(service, raw, contract_value=value)

    assert result["ok"] is False
    assert result["error_code"] == "INVALID_INPUT"
    assert service.store.list_records("candidate") == []
    assert runtime.calls == []


def test_v13_unknown_result_and_mandatory_false_cannot_evade_manifest():
    original = report_bytes(passing_payload())
    unknown = mutate_and_rehash(
        original, lambda payload: payload["checks"][0].update(id="unknown:result")
    )
    mandatory_false = mutate_and_rehash(
        original,
        lambda payload: payload["validation_requirements"][0].update(mandatory=False),
    )

    with pytest.raises(ReportVerificationError, match="REPORT_REQUIREMENTS_INCONSISTENT"):
        verify_report(unknown)
    with pytest.raises(ReportVerificationError, match="REPORT_SCHEMA_INVALID"):
        verify_report(mandatory_false)


@pytest.mark.parametrize(
    ("data", "error_code"),
    [
        (b"\xff", "INVALID_JSON"),
        (b'{"value":Infinity}', "INVALID_JSON_NUMBER"),
        (b" " * 2_097_153, "INPUT_TOO_LARGE"),
        ((b"[" * 34) + b"0" + (b"]" * 34), "JSON_TOO_DEEP"),
    ],
    ids=["invalid-utf8", "infinity", "oversize", "excessive-depth"],
)
def test_v15_offline_strict_parser_rejects_remaining_invalid_inputs(data, error_code):
    with pytest.raises(ReportVerificationError) as caught:
        verify_report(data)
    assert caught.value.code == error_code
    assert caught.value.exit_code == 2


def test_v15_offline_rejects_unsupported_version_and_backend():
    original = report_bytes(passing_payload())
    version = mutate_and_rehash(
        original, lambda payload: payload.update(schema_version="unsupported")
    )
    backend = mutate_and_rehash(
        original, lambda payload: payload.update(evidence_backend="pretend_cloud")
    )

    with pytest.raises(ReportVerificationError, match="UNSUPPORTED_REPORT_SCHEMA"):
        verify_report(version)
    with pytest.raises(ReportVerificationError, match="REPORT_SCHEMA_INVALID"):
        verify_report(backend)


@pytest.mark.parametrize("backend", ["aws_rds", "local_postgres_test", "unit_fixture"])
def test_v21_offline_preserves_backend_and_calls_no_connected_client(monkeypatch, backend):
    def forbidden(*_args, **_kwargs):
        raise AssertionError("offline verifier attempted connected access")

    monkeypatch.setattr(socket, "create_connection", forbidden)
    monkeypatch.setattr(psycopg, "connect", forbidden)
    monkeypatch.setattr(boto3, "client", forbidden)
    real_import = builtins.__import__

    def guarded_import(name, *args, **kwargs):
        if name == "openai" or name.startswith("openai."):
            raise AssertionError("offline verifier attempted model-client import")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", guarded_import)

    result = verify_report(report_bytes(passing_payload(evidence_backend=backend)))

    assert result["evidence_backend"] == backend
    assert result["historical_only"] is True
    assert result["current_apply_eligibility"] == "NOT_EVALUATED"
