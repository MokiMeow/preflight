"""Frozen public contracts. Private evidence must use separate nonserializable types."""

from enum import StrEnum
from typing import Annotated, Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

Digest = Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]
Identifier = Annotated[str, Field(pattern=r"^[a-z_][a-z0-9_]{0,62}$")]
TableName = Annotated[str, Field(pattern=r"^[a-z_][a-z0-9_]{0,62}\.[a-z_][a-z0-9_]{0,62}$")]
ResourceId = Annotated[str, Field(pattern=r"^[a-z][a-z0-9-]{0,62}$")]


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class Phase(StrEnum):
    REGISTERED = "REGISTERED"
    SNAPSHOTTING = "SNAPSHOTTING"
    RESTORING = "RESTORING"
    READY = "READY"
    BASELINED = "BASELINED"
    MIGRATING = "MIGRATING"
    VALIDATING = "VALIDATING"
    PASS = "PASS"
    AWAITING_APPROVAL = "AWAITING_APPROVAL"
    WARN = "WARN"
    BLOCKED = "BLOCKED"
    CLONE_OUTCOME_UNKNOWN = "CLONE_OUTCOME_UNKNOWN"
    APPLYING = "APPLYING"
    APPLIED = "APPLIED"
    APPLY_FAILED = "APPLY_FAILED"
    APPLIED_NEEDS_ATTENTION = "APPLIED_NEEDS_ATTENTION"
    APPLY_OUTCOME_UNKNOWN = "APPLY_OUTCOME_UNKNOWN"
    STALE = "STALE"
    ERROR = "ERROR"


TRANSITIONS: dict[Phase, frozenset[Phase]] = {
    Phase.REGISTERED: frozenset({Phase.SNAPSHOTTING, Phase.ERROR}),
    Phase.SNAPSHOTTING: frozenset({Phase.RESTORING, Phase.ERROR}),
    Phase.RESTORING: frozenset({Phase.READY, Phase.ERROR}),
    Phase.READY: frozenset({Phase.BASELINED, Phase.WARN, Phase.ERROR}),
    Phase.BASELINED: frozenset({Phase.MIGRATING, Phase.WARN, Phase.ERROR}),
    Phase.MIGRATING: frozenset({Phase.VALIDATING, Phase.BLOCKED, Phase.CLONE_OUTCOME_UNKNOWN}),
    Phase.VALIDATING: frozenset({Phase.PASS, Phase.WARN, Phase.BLOCKED, Phase.ERROR}),
    Phase.PASS: frozenset({Phase.AWAITING_APPROVAL}),
    Phase.BLOCKED: frozenset({Phase.BASELINED}),
    Phase.AWAITING_APPROVAL: frozenset({Phase.APPLYING, Phase.STALE, Phase.ERROR}),
    Phase.APPLYING: frozenset(
        {
            Phase.APPLIED,
            Phase.APPLY_FAILED,
            Phase.APPLIED_NEEDS_ATTENTION,
            Phase.APPLY_OUTCOME_UNKNOWN,
            Phase.STALE,
        }
    ),
}


class AddedColumn(StrictModel):
    name: Identifier
    type: Literal["text"]
    nullable: bool


class ExpectedSchema(StrictModel):
    added_columns: list[AddedColumn] = Field(default_factory=list, max_length=32)
    removed_columns: list[Identifier] = Field(default_factory=list, max_length=0)
    allow_other_changes: Literal[False] = False


class RowCountCheck(StrictModel):
    type: Literal["row_count_unchanged"]


class ColumnCheck(StrictModel):
    type: Literal["no_nulls", "unique_non_null", "column_exists", "column_not_null"]
    column: Identifier


class EqualCheck(StrictModel):
    type: Literal["all_equal"]
    column: Identifier
    value: str | int | None


class TypeCheck(StrictModel):
    type: Literal["column_type_is"]
    column: Identifier
    value: Literal["text", "integer", "bigint", "smallint", "timestamp with time zone"]


DeclaredCheck = Annotated[
    RowCountCheck | ColumnCheck | EqualCheck | TypeCheck, Field(discriminator="type")
]


class TableContract(StrictModel):
    name: TableName
    primary_key: list[Identifier] = Field(min_length=1, max_length=8)
    preserve_columns: list[Identifier] = Field(min_length=1, max_length=64)
    expected_schema: ExpectedSchema | None = None
    checks: list[DeclaredCheck] = Field(min_length=1, max_length=128)

    @model_validator(mode="after")
    def valid_keys(self):
        if not set(self.primary_key) <= set(self.preserve_columns):
            raise ValueError("primary key must be preserved")
        for names in [
            self.primary_key,
            self.preserve_columns,
            [c.name for c in self.expected_schema.added_columns] if self.expected_schema else [],
        ]:
            if len(names) != len(set(names)):
                raise ValueError("duplicate column declaration")
        return self


class Contract(StrictModel):
    schema_version: Literal["1", "1.0", "1.1"]
    database: Identifier
    tables: list[TableContract] = Field(min_length=1, max_length=8)
    max_migration_seconds: int = Field(ge=1, le=60)
    max_rows_per_table: int = Field(ge=1, le=10000)
    max_bytes_per_table: int = Field(ge=1, le=10485760)

    @model_validator(mode="after")
    def unique_tables(self):
        if len({t.name for t in self.tables}) != len(self.tables):
            raise ValueError("duplicate table")
        return self


class Request(StrictModel):
    request_id: UUID


class RegisterCandidate(Request):
    sql_text: str | None = Field(default=None, max_length=65536)
    sql_utf8_b64: str | None = Field(default=None, max_length=87384)
    expected_migration_sha256: Digest
    contract: Contract
    operator_id: str = Field(min_length=1, max_length=64, pattern=r"^[a-zA-Z0-9_-]+$")
    run_id: UUID | None = None
    parent_candidate_id: UUID | None = None

    @model_validator(mode="after")
    def one_payload(self):
        if (self.sql_text is None) == (self.sql_utf8_b64 is None):
            raise ValueError("exactly one SQL payload required")
        if (self.run_id is None) != (self.parent_candidate_id is None):
            raise ValueError("revision requires run and parent")
        return self


class StartRehearsal(Request):
    candidate_id: UUID
    source_instance_id: ResourceId
    database_name: Identifier


class RunRequest(Request):
    run_id: UUID


class GetSourceStatus(Request):
    source_instance_id: ResourceId
    database_name: Identifier
    table_names: list[TableName] = Field(min_length=1, max_length=8)
    run_id: UUID | None = None


class ApplyClone(RunRequest):
    candidate_id: UUID


class GetReport(RunRequest):
    candidate_id: UUID | None = None


class ApplySource(ApplyClone):
    migration_sha256: Digest
    report_sha256: Digest
    source_instance_id: ResourceId


class CleanupRun(RunRequest):
    clone_instance_id: ResourceId | None = None
    snapshot_id: ResourceId | None = None
    delete_clone: bool = False
    delete_snapshot: bool = False
    recovery_backup_snapshot_id: ResourceId | None = None

    @model_validator(mode="after")
    def selected_resource(self):
        if not self.delete_clone and not self.delete_snapshot:
            raise ValueError("select a resource")
        return self


TOOL_INPUTS: dict[str, type[Request]] = {
    "register_candidate": RegisterCandidate,
    "start_rehearsal": StartRehearsal,
    "get_run": RunRequest,
    "get_source_status": GetSourceStatus,
    "capture_baseline": RunRequest,
    "apply_to_clone": ApplyClone,
    "validate_rehearsal": RunRequest,
    "get_report": GetReport,
    "apply_to_demo_source": ApplySource,
    "cleanup_run": CleanupRun,
}


class ToolEnvelope(StrictModel):
    ok: bool
    request_id: UUID
    run_id: UUID | None = None
    state: Phase | None = None
    data: dict[str, Any]
    error_code: str | None = None
    retryable: bool = False


class Candidate(StrictModel):
    candidate_id: UUID
    parent_candidate_id: UUID | None = None
    operator_id: str
    migration_sha256: Digest
    contract_sha256: Digest
    byte_size: int
    created_at: str
    policy_version: Literal["1.1"] = "1.1"
    contract: Contract


class WriteEntry(StrictModel):
    table: TableName
    column: Identifier
    operation: Literal["add_column", "update", "set_not_null"]
    read_columns: list[Identifier] = Field(default_factory=list)


class SqlPlan(StrictModel):
    policy_version: Literal["1.1"] = "1.1"
    postgres_major: Literal[18] = 18
    statement_count: int
    writes: list[WriteEntry]
    tables: list[TableName]


class CoverageEntry(StrictModel):
    table: TableName
    column: Identifier
    operation: str
    rule: Literal["preserved", "all_equal", "schema", "missing"]
    complete: bool
    reason_code: str | None = None


class Requirement(StrictModel):
    id: str
    kind: str
    table: TableName | None = None
    column: Identifier | None = None
    mandatory: Literal[True] = True
    policy_role: Literal["invariant", "declared", "coverage"]
    expected_schema: dict[str, str | bool | None] | None = None


class CheckResult(StrictModel):
    id: str
    category: str
    mandatory: Literal[True] = True
    status: Literal["pass", "fail", "not_run"]
    before: int | bool | str | None = None
    after: int | bool | str | None = None
    reason_code: str | None = None


class CheckSet(StrictModel):
    checks: list[CheckResult]
    requirements: list[Requirement]
    coverage: list[CoverageEntry] = Field(default_factory=list)


class TxOutcome(StrictModel):
    outcome: Literal["committed", "rolled_back", "unknown"]
    elapsed_ms: int
    sqlstate: str | None = None
    reason_code: str | None = None


class PublicTableEvidence(StrictModel):
    name: TableName
    row_count: int
    schema_sha256: Digest
    preserved_sha256: Digest
    full_sha256: Digest
    schema_summary: list[dict[str, str | bool | int | None]]


class PublicEvidence(StrictModel):
    algorithm_version: Literal["preflight-evidence-1"] = "preflight-evidence-1"
    tables: list[PublicTableEvidence]


class ReportPayload(StrictModel):
    schema_version: Literal["1.1"] = "1.1"
    algorithm_version: Literal["preflight-json-1"] = "preflight-json-1"
    manifest_version: Literal["1"] = "1"
    evidence_backend: Literal["aws_rds", "local_postgres_test", "unit_fixture"]
    run_id: UUID
    candidate_id: UUID
    operator_id: str
    created_at: str
    source_instance_id: ResourceId
    snapshot_id: ResourceId
    clone_instance_id: ResourceId
    engine_major: Literal[18]
    dependency_versions: dict[str, str]
    migration_sha256: Digest
    contract_sha256: Digest
    before: PublicEvidence | None
    after: PublicEvidence | None
    checks: list[CheckResult]
    validation_requirements: list[Requirement]
    impact_summary: list[CoverageEntry]
    migration: TxOutcome
    backup_available: bool
    verdict: Literal["PASS", "WARN", "BLOCK"]
    apply_eligible_at_report_time: bool
    untested_risks: list[str]


class SealedReport(StrictModel):
    payload: ReportPayload
    report_sha256: Digest


class PreflightError(Exception):
    """Safe fixed code, never an upstream exception string."""

    def __init__(self, code: str):
        super().__init__(code)
        self.code = code
