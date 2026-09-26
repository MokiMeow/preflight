"""Network-free verification for historical sealed report artifacts."""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections.abc import Sequence
from typing import Any, NoReturn

from pydantic import ValidationError

from .artifacts import canonical_json, sha256, strict_json
from .models import PreflightError, ReportPayload
from .report import recompute_report_verdict

_DIGEST = re.compile(r"^[0-9a-f]{64}$")
_REASON_CODE = re.compile(r"^[A-Z][A-Z0-9_]{0,127}$")


class ReportVerificationError(PreflightError):
    """A sanitized verifier failure with a stable process exit code."""

    def __init__(self, code: str, exit_code: int):
        super().__init__(code)
        self.exit_code = exit_code


def _fail(code: str, exit_code: int) -> NoReturn:
    raise ReportVerificationError(code, exit_code)


def _schema_versions(payload: Any) -> None:
    if not isinstance(payload, dict):
        _fail("INVALID_REPORT_PAYLOAD", 2)
    expected = {
        "schema_version": "1.1",
        "algorithm_version": "preflight-json-1",
        "manifest_version": "1",
    }
    if any(payload.get(key) != value for key, value in expected.items()):
        _fail("UNSUPPORTED_REPORT_SCHEMA", 4)


def _validate_manifest(payload: ReportPayload) -> None:
    requirement_ids = [requirement.id for requirement in payload.validation_requirements]
    check_ids = [check.id for check in payload.checks]
    if (
        not requirement_ids
        or len(requirement_ids) != len(set(requirement_ids))
        or len(check_ids) != len(set(check_ids))
        or set(requirement_ids) != set(check_ids)
    ):
        _fail("REPORT_REQUIREMENTS_INCONSISTENT", 4)

    for check in payload.checks:
        if check.status != "pass" and (
            check.reason_code is None or not _REASON_CODE.fullmatch(check.reason_code)
        ):
            _fail("REPORT_REASON_MISSING", 4)
    for entry in payload.impact_summary:
        if not entry.complete and (
            entry.reason_code is None or not _REASON_CODE.fullmatch(entry.reason_code)
        ):
            _fail("REPORT_COVERAGE_REASON_MISSING", 4)

    for evidence in (payload.before, payload.after):
        if evidence is None:
            continue
        names = [table.name for table in evidence.tables]
        if len(names) != len(set(names)):
            _fail("REPORT_EVIDENCE_INCONSISTENT", 4)

    if payload.verdict == "PASS":
        before = payload.before
        after = payload.after
        if before is None or after is None:
            _fail("REPORT_EVIDENCE_INCOMPLETE", 4)
        if not before.tables or not after.tables:
            _fail("REPORT_EVIDENCE_INCOMPLETE", 4)
        if not payload.impact_summary:
            _fail("REPORT_COVERAGE_INCOMPLETE", 4)
    if payload.verdict != "PASS" and payload.apply_eligible_at_report_time:
        _fail("REPORT_ELIGIBILITY_INCONSISTENT", 4)


def verify_report(data: bytes, expected_digest: str | None = None) -> dict[str, Any]:
    """Verify one bounded report without network, database, provider, or model access."""
    if expected_digest is not None and not _DIGEST.fullmatch(expected_digest):
        _fail("INVALID_EXPECTED_DIGEST", 2)
    try:
        envelope = strict_json(data)
    except PreflightError as exc:
        raise ReportVerificationError(exc.code, 2) from None

    if not isinstance(envelope, dict) or set(envelope) != {"payload", "report_sha256"}:
        _fail("INVALID_REPORT_ENVELOPE", 2)
    declared_digest = envelope["report_sha256"]
    if not isinstance(declared_digest, str) or not _DIGEST.fullmatch(declared_digest):
        _fail("INVALID_REPORT_DIGEST", 2)

    payload_data = envelope["payload"]
    _schema_versions(payload_data)
    computed_digest = sha256(canonical_json(payload_data))
    if computed_digest != declared_digest:
        _fail("REPORT_DIGEST_MISMATCH", 3)
    if expected_digest is not None and computed_digest != expected_digest:
        _fail("EXPECTED_DIGEST_MISMATCH", 3)

    try:
        payload = ReportPayload.model_validate_json(canonical_json(payload_data), strict=True)
    except ValidationError:
        _fail("REPORT_SCHEMA_INVALID", 4)

    _validate_manifest(payload)
    recomputed = recompute_report_verdict(payload)
    if recomputed != payload.verdict:
        _fail("REPORT_VERDICT_MISMATCH", 5)
    if payload.apply_eligible_at_report_time != (payload.verdict == "PASS"):
        _fail("REPORT_ELIGIBILITY_INCONSISTENT", 4)

    anchor_status = "EXPECTED_DIGEST_MATCH" if expected_digest else "UNANCHORED"
    return {
        "report_sha256": computed_digest,
        "integrity": "VALID",
        "anchor_status": anchor_status,
        "verification_status": (
            "EXPECTED_DIGEST_MATCH" if expected_digest else "SELF_CONSISTENT_UNANCHORED"
        ),
        "requirements_consistent": True,
        "declared_verdict": payload.verdict,
        "recomputed_verdict": recomputed,
        "evidence_backend": payload.evidence_backend,
        "historical_only": True,
        "current_apply_eligibility": "NOT_EVALUATED",
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="preflight evidence verify")
    parser.add_argument("report")
    parser.add_argument("--expected-report-sha256", dest="expected_digest")
    args = parser.parse_args(argv)
    try:
        with open(args.report, "rb") as report_file:
            data = report_file.read(2_097_153)
        if len(data) > 2_097_152:
            _fail("INPUT_TOO_LARGE", 2)
        result = verify_report(data, args.expected_digest)
    except (OSError, ReportVerificationError) as exc:
        if isinstance(exc, ReportVerificationError):
            code, exit_code = exc.code, exc.exit_code
        else:
            code, exit_code = "REPORT_FILE_UNAVAILABLE", 2
        print(json.dumps({"ok": False, "error_code": code}, separators=(",", ":")))
        return exit_code
    print(json.dumps({"ok": True, **result}, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    sys.exit(main())
