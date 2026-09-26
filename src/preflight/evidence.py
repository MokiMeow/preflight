"""Private typed evidence with only aggregate public projections."""

import hashlib
import json
from datetime import datetime, timezone

from psycopg import sql
from psycopg.pq import TransactionStatus

from .db import validate_catalog
from .models import (
    CheckResult,
    CheckSet,
    Contract,
    PreflightError,
    PublicEvidence,
    PublicTableEvidence,
    Requirement,
    SqlPlan,
)
from .sql_policy import resolve_coverage


def canonical(value):
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode("utf-8")


def typed_value(value):
    if value is None:
        return ["null"]
    if type(value) is int:
        return ["int", str(value)]
    if type(value) is str:
        return ["text", value]
    if type(value) is datetime and value.tzinfo is not None and value.utcoffset() is not None:
        return ["timestamptz", value.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")]
    raise PreflightError("UNSUPPORTED_VALUE_TYPE")


def _digest(domain, pieces):
    h = hashlib.sha256()
    h.update(b"preflight-evidence-1\0" + domain.encode() + b"\0")
    for piece in pieces:
        h.update(len(piece).to_bytes(8, "big"))
        h.update(piece)
    return h.hexdigest()


def _root(domain, mapping):
    return _digest(
        domain, (piece for k in sorted(mapping) for piece in (k, mapping[k].encode("ascii")))
    )


class EvidenceBundle:
    """Intentionally not a Pydantic/dataclass model: never JSON serialize this object."""

    __slots__ = ("public", "_tables", "existing_columns")

    def __init__(self, public, tables, existing_columns):
        self.public = public
        self._tables = tables
        self.existing_columns = existing_columns

    def __repr__(self):
        return "<EvidenceBundle private>"


def _capture(connection, contract, existing_columns):
    metadata = validate_catalog(connection, contract)
    private = {}
    public = []
    for table in contract.tables:
        meta = metadata[table.name]
        columns = [c["name"] for c in meta["columns"]]
        full_columns = existing_columns.get(table.name) if existing_columns is not None else columns
        if full_columns is None or not set(full_columns) <= set(columns):
            raise PreflightError("BASELINE_COLUMNS_MISSING")
        schema, name = table.name.split(".")
        ident = sql.Identifier(schema, name)
        with connection.cursor() as cur:
            # Server-side byte guard prevents fetching one enormous text datum first.
            sizes = sql.SQL(" + ").join(
                sql.SQL("COALESCE(pg_catalog.octet_length({}::text),0)").format(sql.Identifier(c))
                for c in columns
            )
            cur.execute(sql.SQL("SELECT count(*),COALESCE(sum({}),0) FROM {}").format(sizes, ident))
            count, size = cur.fetchone()
            if count > contract.max_rows_per_table or size > contract.max_bytes_per_table:
                raise PreflightError("SCAN_BUDGET_EXCEEDED")
        preserved, full, values = {}, {}, {c: [] for c in columns}
        total = 0
        count_actual = 0
        # Named server cursor streams instead of materializing the whole result in libpq.
        with connection.cursor(name="preflight_scan") as cur:
            cur.itersize = 128
            cur.execute(
                sql.SQL("SELECT {} FROM {}").format(
                    sql.SQL(",").join(map(sql.Identifier, columns)), ident
                )
            )
            for row in cur:
                encoded = {c: typed_value(v) for c, v in zip(columns, row, strict=True)}
                raw = canonical([encoded[c] for c in columns])
                total += len(raw)
                count_actual += 1
                if (
                    total > contract.max_bytes_per_table
                    or count_actual > contract.max_rows_per_table
                ):
                    raise PreflightError("SCAN_BUDGET_EXCEEDED")
                key = canonical([encoded[c] for c in table.primary_key])
                if key in preserved or any(encoded[c] == ["null"] for c in table.primary_key):
                    raise PreflightError("PRIMARY_KEY_INVALID")
                preserved[key] = _digest(
                    "preserved-row", [key, canonical([encoded[c] for c in table.preserve_columns])]
                )
                full[key] = _digest(
                    "full-existing-row", [key, canonical([encoded[c] for c in full_columns])]
                )
                for c in columns:
                    values[c].append(canonical(encoded[c]))
        if count_actual != count:
            raise PreflightError("SCAN_INCONSISTENT")
        private[table.name] = {
            "preserved": preserved,
            "full": full,
            "values": values,
            "schema": meta,
        }
        public.append(
            PublicTableEvidence(
                name=table.name,
                row_count=count_actual,
                schema_sha256=_digest("schema", [canonical(meta)]),
                preserved_sha256=_root("preserved-root", preserved),
                full_sha256=_root("full-existing-root", full),
                schema_summary=meta["columns"],
            )
        )
    return EvidenceBundle(
        PublicEvidence(tables=public),
        private,
        {name: [c["name"] for c in meta["columns"]] for name, meta in metadata.items()},
    )


def capture_evidence(
    connection, contract: Contract, existing_columns=None, in_transaction=False
) -> EvidenceBundle:
    """Fresh baselines use one read-only RR snapshot; locked apply callbacks reuse theirs."""
    fresh = connection.info.transaction_status == TransactionStatus.IDLE
    if in_transaction and fresh:
        raise PreflightError("EVIDENCE_TRANSACTION_REQUIRED")
    if not in_transaction and not fresh:
        raise PreflightError("EVIDENCE_SESSION_NOT_FRESH")
    try:
        if fresh:
            with connection.transaction():
                connection.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY")
                connection.execute(
                    "SELECT pg_catalog.set_config('search_path','pg_catalog',true), pg_catalog.set_config('statement_timeout',%s,true)",
                    (str(contract.max_migration_seconds * 1000),),
                )
                return _capture(connection, contract, existing_columns)
        return _capture(connection, contract, existing_columns)
    except PreflightError:
        raise
    except Exception:
        raise PreflightError("EVIDENCE_CAPTURE_FAILED") from None


def baseline_matches(before: EvidenceBundle, after: EvidenceBundle) -> bool:
    if not isinstance(before, EvidenceBundle) or not isinstance(after, EvidenceBundle):
        return False
    return before.existing_columns == after.existing_columns and {
        t.name: (t.schema_sha256, t.full_sha256, t.row_count) for t in before.public.tables
    } == {t.name: (t.schema_sha256, t.full_sha256, t.row_count) for t in after.public.tables}


def compare_evidence(
    before: EvidenceBundle, after: EvidenceBundle, contract: Contract, plan: SqlPlan
) -> CheckSet:
    requirements, results = [], []

    def record(id, kind, passed, table=None, column=None, role="invariant", reason=None):
        requirements.append(
            Requirement(id=id, kind=kind, table=table, column=column, policy_role=role)
        )
        results.append(
            CheckResult(
                id=id,
                category=kind,
                status="pass" if passed else "fail",
                after=passed,
                reason_code=reason if not passed else None,
            )
        )

    if not isinstance(before, EvidenceBundle) or not isinstance(after, EvidenceBundle):
        raise PreflightError("BASELINE_EVIDENCE_MISSING")
    coverage = resolve_coverage(plan, contract, before.existing_columns)
    pk_pass = protected_pass = schema_pass = True
    schema_complete = all(t.expected_schema is not None for t in contract.tables)
    for table in contract.tables:
        if table.name not in before._tables or table.name not in after._tables:
            raise PreflightError("BASELINE_EVIDENCE_MISSING")
        b, a = before._tables[table.name], after._tables[table.name]
        before_keys, after_keys = b["preserved"].keys(), a["preserved"].keys()
        counts = {
            "missing_keys": len(before_keys - after_keys),
            "extra_keys": len(after_keys - before_keys),
            "changed_preserved_rows": sum(
                b["preserved"][key] != a["preserved"][key] for key in before_keys & after_keys
            ),
        }
        for kind, count in counts.items():
            id = f"coverage:{table.name}:{kind}"
            requirements.append(
                Requirement(id=id, kind=kind, table=table.name, policy_role="coverage")
            )
            results.append(
                CheckResult(
                    id=id,
                    category=kind,
                    status="pass" if count == 0 else "fail",
                    before=0,
                    after=count,
                    reason_code="ROW_COMPARISON_FAILED" if count else None,
                )
            )
        keys_match = b["preserved"].keys() == a["preserved"].keys()
        pk_pass &= keys_match
        protected_pass &= b["preserved"] == a["preserved"]
        bc, ac = b["schema"]["columns"], a["schema"]["columns"]
        expected = table.expected_schema
        schema_ok = True
        if expected:
            expected_cols = bc + [
                {
                    "name": c.name,
                    "type": c.type,
                    "nullable": c.nullable,
                    "position": len(bc) + i + 1,
                    "default": False,
                }
                for i, c in enumerate(expected.added_columns)
            ]
            schema_ok &= ac == expected_cols
            schema_ok &= (
                b["schema"]["constraints"] == a["schema"]["constraints"]
                and b["schema"]["indexes"] == a["schema"]["indexes"]
            )
        schema_pass &= schema_ok
        for i, c in enumerate(table.checks):
            col = getattr(c, "column", None)
            vals = a["values"].get(col)
            info = next((x for x in ac if x["name"] == col), None)
            null = canonical(["null"])
            if c.type == "row_count_unchanged":
                passed = len(b["preserved"]) == len(a["preserved"])
            elif c.type == "column_exists":
                passed = info is not None
            elif c.type == "column_type_is":
                passed = info is not None and info["type"] == c.value
            elif c.type == "column_not_null":
                passed = info is not None and not info["nullable"]
            elif c.type == "no_nulls":
                passed = vals is not None and null not in vals
            elif c.type == "unique_non_null":
                passed = vals is not None and null not in vals and len(vals) == len(set(vals))
            elif c.type == "all_equal":
                # Type tags prevent integer 1 from equalling text '1'; explicit NULL works.
                passed = vals is not None and all(
                    v == canonical(typed_value(c.value)) for v in vals
                )
            else:
                raise PreflightError("UNKNOWN_CHECK")
            record(
                f"declared:{table.name}:{i}:{c.type}",
                c.type,
                passed,
                table.name,
                col,
                "declared",
                "DECLARED_CHECK_FAILED",
            )
    for kind, passed, reason in [
        ("pk_set_unchanged", pk_pass, "PRIMARY_KEY_CHANGED"),
        ("preserved_values_unchanged", protected_pass, "PRESERVED_VALUES_CHANGED"),
        (
            "schema_expected",
            schema_pass and schema_complete,
            "SCHEMA_MISMATCH" if schema_complete else "COVERAGE_INCOMPLETE",
        ),
        (
            "coverage_complete",
            all(c.complete for c in coverage)
            and all(t.expected_schema is not None for t in contract.tables),
            "COVERAGE_INCOMPLETE",
        ),
        ("within_budgets", True, None),
        ("declared_checks_complete", True, None),
    ]:
        record("invariant:" + kind, kind, passed, reason=reason)
    # Missing coverage is incomplete, not a known observed correctness failure.
    results = [
        r.model_copy(update={"status": "not_run"}) if r.reason_code == "COVERAGE_INCOMPLETE" else r
        for r in results
    ]
    return CheckSet(checks=results, requirements=requirements, coverage=coverage)
