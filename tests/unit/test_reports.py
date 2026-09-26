import json
import socket
from uuid import UUID

import pytest

from preflight.artifacts import canonical_json, sha256
from preflight.models import (
    CheckResult,
    CoverageEntry,
    PreflightError,
    PublicEvidence,
    PublicTableEvidence,
    ReportPayload,
    TxOutcome,
)
from preflight.offline import ReportVerificationError, verify_report
from preflight.report import render_report, seal_report
from preflight.verdict import invariant_requirements

DIGEST_A = "a" * 64
DIGEST_B = "b" * 64
DIGEST_C = "c" * 64
DIGEST_D = "d" * 64
DIGEST_E = "e" * 64


def evidence(row_count: int = 3) -> PublicEvidence:
    return PublicEvidence(
        tables=[
            PublicTableEvidence(
                name="public.customers",
                row_count=row_count,
                schema_sha256=DIGEST_A,
                preserved_sha256=DIGEST_B,
                full_sha256=DIGEST_C,
                schema_summary=[{"name": "id", "type": "integer", "nullable": False}],
            )
        ]
    )


def passing_payload(**updates) -> ReportPayload:
    requirements = invariant_requirements()
    checks = [
        CheckResult(id=item.id, category=item.kind, status="pass", before=True, after=True)
        for item in requirements
    ]
    values = {
        "evidence_backend": "unit_fixture",
        "run_id": UUID("00000000-0000-0000-0000-000000000001"),
        "candidate_id": UUID("00000000-0000-0000-0000-000000000002"),
        "operator_id": "unit-test",
        "created_at": "2026-09-26T00:00:00Z",
        "source_instance_id": "preflight-source",
        "snapshot_id": "preflight-snapshot",
        "clone_instance_id": "preflight-clone",
        "engine_major": 18,
        "dependency_versions": {"preflight": "0.1.0", "postgresql": "18"},
        "migration_sha256": DIGEST_D,
        "contract_sha256": DIGEST_E,
        "before": evidence(),
        "after": evidence(),
        "checks": checks,
        "validation_requirements": requirements,
        "impact_summary": [
            CoverageEntry(
                table="public.customers",
                column="account_tier",
                operation="add_column",
                rule="all_equal",
                complete=True,
            )
        ],
        "migration": TxOutcome(outcome="committed", elapsed_ms=42),
        "backup_available": True,
        "verdict": "PASS",
        "apply_eligible_at_report_time": True,
        "untested_risks": ["traffic and application compatibility"],
    }
    values.update(updates)
    return ReportPayload(**values)


def report_bytes(payload: ReportPayload) -> bytes:
    return canonical_json(seal_report(payload).model_dump(mode="json"))


def mutate_and_rehash(data: bytes, mutate) -> bytes:
    envelope = json.loads(data)
    mutate(envelope["payload"])
    envelope["report_sha256"] = sha256(canonical_json(envelope["payload"]))
    return canonical_json(envelope)


def assert_error(data: bytes, code: str, exit_code: int, expected: str | None = None):
    with pytest.raises(ReportVerificationError) as caught:
        verify_report(data, expected)
    assert caught.value.code == code
    assert caught.value.exit_code == exit_code


def test_seal_hashes_payload_only_and_verifier_labels_anchor():
    payload = passing_payload()
    sealed = seal_report(payload)
    assert sealed.report_sha256 == sha256(canonical_json(payload.model_dump(mode="json")))

    unanchored = verify_report(report_bytes(payload))
    assert unanchored["integrity"] == "VALID"
    assert unanchored["anchor_status"] == "UNANCHORED"
    assert unanchored["verification_status"] == "SELF_CONSISTENT_UNANCHORED"
    assert unanchored["historical_only"] is True
    assert unanchored["current_apply_eligibility"] == "NOT_EVALUATED"

    anchored = verify_report(report_bytes(payload), sealed.report_sha256)
    assert anchored["anchor_status"] == "EXPECTED_DIGEST_MATCH"
    assert anchored["declared_verdict"] == anchored["recomputed_verdict"] == "PASS"


def test_seal_refuses_forged_pass_and_eligibility():
    with pytest.raises(PreflightError, match="REPORT_VERDICT_MISMATCH"):
        seal_report(passing_payload(after=None))
    with pytest.raises(PreflightError, match="REPORT_ELIGIBILITY_MISMATCH"):
        seal_report(passing_payload(apply_eligible_at_report_time=False))


def test_seal_refuses_an_incomplete_requirement_manifest():
    payload = passing_payload()
    with pytest.raises(PreflightError, match="REPORT_REQUIREMENTS_INCONSISTENT"):
        seal_report(
            payload.model_copy(
                update={
                    "checks": payload.checks[:-1],
                    "verdict": "WARN",
                    "apply_eligible_at_report_time": False,
                }
            )
        )


def test_verifier_detects_old_hash_and_rehashed_anchor_tampering():
    original = report_bytes(passing_payload())
    trusted = json.loads(original)["report_sha256"]
    old_hash = json.loads(original)
    old_hash["payload"]["operator_id"] = "changed"
    assert_error(canonical_json(old_hash), "REPORT_DIGEST_MISMATCH", 3)

    rehashed = mutate_and_rehash(original, lambda payload: payload.update(operator_id="changed"))
    assert_error(rehashed, "EXPECTED_DIGEST_MISMATCH", 3, trusted)


def test_verifier_rejects_duplicate_keys_and_schema_failures():
    assert_error(
        b'{"payload":{"schema_version":"1.1","x":1,"x":2},"report_sha256":"' + b"a" * 64 + b'"}',
        "DUPLICATE_JSON_KEY",
        2,
    )

    valid = report_bytes(passing_payload())
    unknown_backend = mutate_and_rehash(
        valid, lambda payload: payload.update(evidence_backend="pretend_cloud")
    )
    assert_error(unknown_backend, "REPORT_SCHEMA_INVALID", 4)

    unsupported = mutate_and_rehash(valid, lambda payload: payload.update(schema_version="2"))
    assert_error(unsupported, "UNSUPPORTED_REPORT_SCHEMA", 4)


def test_verifier_rejects_missing_results_and_forged_pass():
    valid = report_bytes(passing_payload())
    missing = mutate_and_rehash(valid, lambda payload: payload["checks"].pop())
    assert_error(missing, "REPORT_REQUIREMENTS_INCONSISTENT", 4)

    def fail_check(payload):
        payload["checks"][0]["status"] = "fail"
        payload["checks"][0]["reason_code"] = "CHECK_FAILED"

    forged = mutate_and_rehash(valid, fail_check)
    assert_error(forged, "REPORT_VERDICT_MISMATCH", 5)


def test_valid_historical_block_is_verified_as_block():
    payload = passing_payload(verdict="BLOCK", apply_eligible_at_report_time=False)
    checks = list(payload.checks)
    checks[0] = checks[0].model_copy(update={"status": "fail", "reason_code": "CHECK_FAILED"})
    payload = payload.model_copy(update={"checks": checks})
    result = verify_report(report_bytes(payload))
    assert result["declared_verdict"] == result["recomputed_verdict"] == "BLOCK"
    assert result["integrity"] == "VALID"


def test_markdown_escapes_untrusted_content_and_is_deterministic():
    payload = passing_payload(
        operator_id="bad|label`<script>alert(1)</script>",
        untested_risks=["[credential](https://user:password@example.invalid) | <img src=x>"],
    )
    first = render_report(payload)
    assert first == render_report(payload)
    assert "<script>" not in first
    assert "<img" not in first
    assert "&lt;script&gt;" in first
    assert "&#124;" in first
    assert "password" not in first
    assert "REDACTED_CREDENTIAL_URL" in first
    assert "Historical sealed rehearsal evidence" in first
    assert "Current apply eligibility: `NOT_EVALUATED`" in first


def test_offline_verifier_makes_no_network_call(monkeypatch):
    def forbidden(*_args, **_kwargs):
        raise AssertionError("network access attempted")

    monkeypatch.setattr(socket, "create_connection", forbidden)
    result = verify_report(report_bytes(passing_payload()))
    assert result["requirements_consistent"] is True
