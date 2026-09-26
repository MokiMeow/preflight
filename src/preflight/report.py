"""Immutable report sealing and deterministic, safe Markdown rendering."""

from __future__ import annotations

import html
import re
from urllib.parse import parse_qsl, urlsplit

from .artifacts import canonical_json, sha256
from .models import PreflightError, ReportPayload, SealedReport
from .verdict import evaluate

_URL = re.compile(r"\b(?:https?|postgres(?:ql)?|mysql)://[^\s<>\])]+", re.IGNORECASE)
_SECRET_QUERY_KEYS = {"access_token", "api_key", "key", "password", "secret", "token"}


def _payload_bytes(payload: ReportPayload) -> bytes:
    return canonical_json(payload.model_dump(mode="json"))


def _has_complete_evidence(payload: ReportPayload) -> bool:
    if payload.before is None or payload.after is None:
        return False
    if not payload.before.tables or not payload.after.tables:
        return False
    before_names = [table.name for table in payload.before.tables]
    after_names = [table.name for table in payload.after.tables]
    return len(set(before_names)) == len(before_names) and set(before_names) == set(after_names)


def recompute_report_verdict(payload: ReportPayload) -> str:
    """Apply the shared oracle plus report-only evidence completeness rules."""
    verdict = evaluate(
        payload.checks,
        payload.validation_requirements,
        payload.migration.outcome,
        payload.impact_summary,
    )
    if verdict == "PASS" and (not _has_complete_evidence(payload) or not payload.backup_available):
        return "WARN"
    return verdict


def seal_report(payload: ReportPayload) -> SealedReport:
    """Seal a validated payload; never bless a model-supplied verdict."""
    requirement_ids = [item.id for item in payload.validation_requirements]
    check_ids = [item.id for item in payload.checks]
    if (
        not requirement_ids
        or len(requirement_ids) != len(set(requirement_ids))
        or len(check_ids) != len(set(check_ids))
        or set(requirement_ids) != set(check_ids)
    ):
        raise PreflightError("REPORT_REQUIREMENTS_INCONSISTENT")
    if recompute_report_verdict(payload) != payload.verdict:
        raise PreflightError("REPORT_VERDICT_MISMATCH")
    if payload.apply_eligible_at_report_time != (payload.verdict == "PASS"):
        raise PreflightError("REPORT_ELIGIBILITY_MISMATCH")
    return SealedReport(payload=payload, report_sha256=sha256(_payload_bytes(payload)))


def _redact_credential_url(match: re.Match[str]) -> str:
    value = match.group(0)
    parsed = urlsplit(value)
    secret_query = any(key.casefold() in _SECRET_QUERY_KEYS for key, _ in parse_qsl(parsed.query))
    if parsed.username is not None or parsed.password is not None or secret_query:
        return "[REDACTED_CREDENTIAL_URL]"
    return value


def _cell(value: object) -> str:
    """Render untrusted data as one inert inline-code Markdown cell."""
    if value is None:
        return "—"
    if isinstance(value, bool):
        text = "true" if value else "false"
    else:
        text = str(value)
    text = " ".join(text.splitlines())
    text = _URL.sub(_redact_credential_url, text)
    text = html.escape(text, quote=True).replace("|", "&#124;").replace("`", "&#96;")
    return f"`{text}`"


def _evidence_rows(payload: ReportPayload) -> list[str]:
    before = {table.name: table for table in payload.before.tables} if payload.before else {}
    after = {table.name: table for table in payload.after.tables} if payload.after else {}
    rows: list[str] = []
    for name in sorted(set(before) | set(after)):
        old = before.get(name)
        new = after.get(name)
        rows.append(
            "| "
            + " | ".join(
                (
                    _cell(name),
                    _cell(old.row_count if old else None),
                    _cell(new.row_count if new else None),
                    _cell(old.schema_sha256 if old else None),
                    _cell(new.schema_sha256 if new else None),
                    _cell(old.preserved_sha256 if old else None),
                    _cell(new.preserved_sha256 if new else None),
                    _cell(old.full_sha256 if old else None),
                    _cell(new.full_sha256 if new else None),
                )
            )
            + " |"
        )
    if not rows:
        rows.append("| — | — | — | — | — | — | — | — | — |")
    return rows


def render_report(payload: ReportPayload) -> str:
    """Return the deterministic native Markdown view of a sealed payload."""
    report_digest = sha256(_payload_bytes(payload))
    requirement_by_id = {
        requirement.id: requirement for requirement in payload.validation_requirements
    }
    lines = [
        f"# PREFLIGHT — REHEARSAL {payload.verdict}",
        "",
        "> Historical sealed rehearsal evidence. Current source eligibility is not evaluated here.",
        "",
        "## Target and provenance",
        "",
        f"- Evidence backend: {_cell(payload.evidence_backend)}",
        f"- Run: {_cell(payload.run_id)}",
        f"- Candidate: {_cell(payload.candidate_id)}",
        f"- Operator label: {_cell(payload.operator_id)}",
        f"- Created: {_cell(payload.created_at)}",
        f"- Source instance: {_cell(payload.source_instance_id)}",
        f"- Snapshot: {_cell(payload.snapshot_id)}",
        f"- Clone instance: {_cell(payload.clone_instance_id)}",
        f"- PostgreSQL major: {_cell(payload.engine_major)}",
        "",
        "## Artifact identity",
        "",
        f"- Migration SHA-256: {_cell(payload.migration_sha256)}",
        f"- Contract SHA-256: {_cell(payload.contract_sha256)}",
        f"- Report SHA-256: {_cell(report_digest)}",
        (
            f"- Report schema / algorithm / manifest: {_cell(payload.schema_version)} / "
            f"{_cell(payload.algorithm_version)} / {_cell(payload.manifest_version)}"
        ),
        "",
        "## Aggregate evidence",
        "",
        (
            "| Table | Rows before | Rows after | Schema before | Schema after | "
            "Preserved before | Preserved after | Full before | Full after |"
        ),
        "|---|---:|---:|---|---|---|---|---|---|",
        *_evidence_rows(payload),
        "",
        "## Mandatory checks",
        "",
        "| Requirement | Kind | Category | Before | After | Result | Reason |",
        "|---|---|---|---|---|---|---|",
    ]
    for check in payload.checks:
        requirement = requirement_by_id.get(check.id)
        lines.append(
            "| "
            + " | ".join(
                (
                    _cell(check.id),
                    _cell(requirement.kind if requirement else "MISSING_REQUIREMENT"),
                    _cell(check.category),
                    _cell(check.before),
                    _cell(check.after),
                    _cell(check.status.upper()),
                    _cell(check.reason_code),
                )
            )
            + " |"
        )
    if not payload.checks:
        lines.append("| — | — | — | — | — | — | — |")

    lines.extend(
        [
            "",
            "## Impact and coverage",
            "",
            "| Table | Column | Operation | Rule | Complete | Reason |",
            "|---|---|---|---|---|---|",
        ]
    )
    for entry in payload.impact_summary:
        lines.append(
            "| "
            + " | ".join(
                (
                    _cell(entry.table),
                    _cell(entry.column),
                    _cell(entry.operation),
                    _cell(entry.rule),
                    _cell(entry.complete),
                    _cell(entry.reason_code),
                )
            )
            + " |"
        )
    if not payload.impact_summary:
        lines.append("| — | — | — | — | — | — |")

    lines.extend(
        [
            "",
            "## Execution and recovery",
            "",
            f"- Migration outcome: {_cell(payload.migration.outcome)}",
            f"- Clone migration duration (ms): {_cell(payload.migration.elapsed_ms)}",
            f"- Safe SQLSTATE: {_cell(payload.migration.sqlstate)}",
            f"- Migration reason: {_cell(payload.migration.reason_code)}",
            f"- Recovery backup available at report time: {_cell(payload.backup_available)}",
            f"- Apply eligible at report time: {_cell(payload.apply_eligible_at_report_time)}",
            "- Current apply eligibility: `NOT_EVALUATED`",
            "",
            "## Dependency versions",
            "",
        ]
    )
    for name, version in sorted(payload.dependency_versions.items()):
        lines.append(f"- {_cell(name)}: {_cell(version)}")
    if not payload.dependency_versions:
        lines.append("- `NOT_OBSERVED`")

    lines.extend(["", "## Untested risks", ""])
    for risk in payload.untested_risks:
        lines.append(f"- {_cell(risk)}")
    if not payload.untested_risks:
        lines.append("- `NONE_RECORDED`")
    lines.append("")
    return "\n".join(lines)
