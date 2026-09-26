"""Explicit, fresh-only owned synthetic source setup. Not a runtime tool or reset."""

import argparse
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

import psycopg
from psycopg import sql
from psycopg.pq import TransactionStatus
from pydantic import Field

from preflight.artifacts import canonical_json, sha256, strict_json
from preflight.db import connect_database
from preflight.models import Digest, Identifier, PreflightError, ResourceId, StrictModel


class SeedPlan(StrictModel):
    schema_version: Literal["preflight-seed-1"] = "preflight-seed-1"
    operation: Literal["seed_fresh_synthetic_source"] = "seed_fresh_synthetic_source"
    account_id: str = Field(pattern=r"^\d{12}$")
    region: str = Field(pattern=r"^[a-z]{2}-[a-z]+-\d$")
    source_instance_id: ResourceId
    database: Identifier
    owner: str = Field(pattern=r"^[a-zA-Z0-9_-]{1,64}$")
    admin_secret_arn: str
    reader_secret_arn: str
    writer_secret_arn: str
    sslrootcert: str = Field(min_length=1, max_length=1024)
    source_seed_authorized: bool
    reader_role: Literal["preflight_reader"] = "preflight_reader"
    writer_role: Literal["preflight_migrator"] = "preflight_migrator"
    table: Literal["public.customers"] = "public.customers"
    row_count: Literal[1000] = 1000
    postgres_major: Literal[18] = 18
    fixture_version: Literal["synthetic-customers-1"] = "synthetic-customers-1"


class SeedApproval(StrictModel):
    operation: Literal["seed_fresh_synthetic_source"]
    plan_sha256: Digest
    account_id: str
    region: str
    source_instance_id: ResourceId
    owner: str
    seed_authorized: Literal[True]


def _check_refs(plan):
    refs = [plan.admin_secret_arn, plan.reader_secret_arn, plan.writer_secret_arn]
    prefix = f"arn:aws:secretsmanager:{plan.region}:{plan.account_id}:secret:"
    if len(set(refs)) != 3 or any(
        not ref.startswith(prefix)
        or not re.fullmatch(r"[A-Za-z0-9/_+=.@-]{1,512}", ref[len(prefix) :])
        for ref in refs
    ):
        raise PreflightError("SEED_SECRET_REFERENCE_INVALID")


def build_plan(operator: dict, admin_secret_arn: str, sslrootcert: str) -> SeedPlan:
    try:
        aws, policy = operator["aws"], operator["database_policy"]
        source = aws["source_instance_id"]
        if policy["source_allowlist"] != [source] or policy["table_allowlist"] != [
            "public.customers"
        ]:
            raise PreflightError("SEED_TARGET_NOT_ALLOWLISTED")
        authorization = aws.get("seed_or_reset_synthetic_source_authorized", False)
        if type(authorization) is not bool:
            raise PreflightError("SEED_AUTHORIZATION_INVALID")
        plan = SeedPlan(
            account_id=aws["account_id"],
            region=aws["region"],
            source_instance_id=source,
            database=aws["database_name"],
            owner=aws.get("resource_owner_label") or operator["operator"]["label"],
            admin_secret_arn=admin_secret_arn,
            reader_secret_arn=aws["source_read_secret_arn"],
            writer_secret_arn=aws["migration_writer_secret_arn"],
            sslrootcert=sslrootcert,
            source_seed_authorized=authorization,
        )
        _check_refs(plan)
        return plan
    except PreflightError:
        raise
    except Exception:
        raise PreflightError("SEED_PLAN_CONFIGURATION_INVALID") from None


def plan_envelope(plan: SeedPlan):
    payload = plan.model_dump(mode="json")
    return {"plan": payload, "plan_sha256": sha256(canonical_json(payload))}


def approve_plan(envelope: dict, operator: dict, approval: dict) -> SeedPlan:
    try:
        if approval.get("seed_authorized") is not True:
            raise PreflightError("SOURCE_SEED_NOT_AUTHORIZED")
        if set(envelope) != {"plan", "plan_sha256"}:
            raise PreflightError("SEED_PLAN_INVALID")
        plan = SeedPlan.model_validate(envelope["plan"])
        expected = plan_envelope(plan)
        if (
            envelope != expected
            or build_plan(operator, plan.admin_secret_arn, plan.sslrootcert) != plan
        ):
            raise PreflightError("SEED_PLAN_CHANGED")
        accepted = SeedApproval.model_validate(approval)
        if (
            not plan.source_seed_authorized
            or any(
                getattr(accepted, key) != getattr(plan, key)
                for key in ["operation", "account_id", "region", "source_instance_id", "owner"]
            )
            or accepted.plan_sha256 != expected["plan_sha256"]
        ):
            raise PreflightError("SOURCE_SEED_NOT_AUTHORIZED")
        return plan
    except PreflightError:
        raise
    except Exception:
        raise PreflightError("SEED_APPROVAL_INVALID") from None


def _narrow_role(conn, name):
    row = conn.execute(
        """SELECT rolcanlogin,rolsuper,rolcreatedb,rolcreaterole,rolreplication,rolbypassrls
        FROM pg_catalog.pg_roles WHERE rolname=%s""",
        (name,),
    ).fetchone()
    if not row:
        return False
    if not row[0] or any(row[1:]):
        raise PreflightError("SEED_RUNTIME_ROLE_UNSAFE")
    if conn.execute(
        """SELECT EXISTS(SELECT 1 FROM pg_catalog.pg_auth_members m
        JOIN pg_catalog.pg_roles r ON r.oid=m.member WHERE r.rolname=%s)""",
        (name,),
    ).fetchone()[0]:
        raise PreflightError("SEED_RUNTIME_ROLE_MEMBERSHIP_UNSAFE")
    if conn.execute(
        """SELECT EXISTS(SELECT 1 FROM pg_catalog.pg_default_acl a
        JOIN pg_catalog.pg_roles r ON r.oid=a.defaclrole WHERE r.rolname=%s)""",
        (name,),
    ).fetchone()[0]:
        raise PreflightError("SEED_RUNTIME_DEFAULT_PRIVILEGES_UNSAFE")
    if conn.execute(
        """SELECT EXISTS(SELECT 1 FROM pg_catalog.pg_namespace n JOIN pg_catalog.pg_roles r ON r.oid=n.nspowner WHERE r.rolname=%s),
        EXISTS(SELECT 1 FROM pg_catalog.pg_database d JOIN pg_catalog.pg_roles r ON r.oid=d.datdba WHERE r.rolname=%s),
        pg_catalog.has_database_privilege(%s,current_database(),'CREATE'),
        pg_catalog.has_schema_privilege(%s,'public','CREATE')""",
        (name, name, name, name),
    ).fetchone() != (False, False, False, False):
        raise PreflightError("SEED_RUNTIME_ROLE_SCOPE_UNSAFE")
    return True


def seed_fresh(
    connection,
    *,
    writer_role,
    reader_role,
    writer_password,
    reader_password,
    expected_database,
    backend="local_postgres_test",
):
    """Admin-only setup; one transaction, fresh tables only, no reset/retry behavior."""
    if (
        backend not in {"local_postgres_test", "aws_rds"}
        or backend == "local_postgres_test"
        and connection.info.host not in {"127.0.0.1", "localhost", "::1"}
    ):
        raise PreflightError("SEED_BACKEND_UNSAFE")
    if (
        connection.info.server_version // 10000 != 18
        or connection.info.dbname != expected_database
        or not connection.autocommit
        or connection.info.transaction_status != TransactionStatus.IDLE
    ):
        raise PreflightError("SEED_DATABASE_SESSION_INVALID")
    if (
        writer_role == reader_role
        or connection.info.user in {writer_role, reader_role}
        or any(
            not re.fullmatch(r"preflight_[a-z][a-z0-9_]{0,44}", role)
            for role in [writer_role, reader_role]
        )
        or any(
            not isinstance(password, str) or not 16 <= len(password) <= 1024
            for password in [writer_password, reader_password]
        )
    ):
        raise PreflightError("SEED_ROLE_CONFIGURATION_INVALID")
    commit_started = False
    try:
        connection.execute("BEGIN")
        connection.execute("SET LOCAL search_path=pg_catalog")
        connection.execute("SET LOCAL statement_timeout='15s'")
        connection.execute("SET LOCAL lock_timeout='3s'")
        # Never emit credential-bearing DDL into statement/error logs. Fail closed
        # if the admin cannot set these session privacy controls.
        connection.execute("SET LOCAL log_statement='none'")
        connection.execute("SET LOCAL log_min_error_statement='panic'")
        connection.execute("SELECT pg_catalog.pg_advisory_xact_lock(18360318)")
        if connection.execute("SELECT current_database()").fetchone()[0] != expected_database:
            raise PreflightError("SEED_DATABASE_SESSION_INVALID")
        if connection.execute("""SELECT EXISTS(SELECT 1 FROM pg_catalog.pg_class c
            JOIN pg_catalog.pg_namespace n ON n.oid=c.relnamespace
            WHERE n.nspname NOT IN ('pg_catalog','information_schema') AND n.nspname NOT LIKE 'pg_toast%'
            AND c.relkind IN ('r','p','v','m','f','S'))""").fetchone()[0]:
            raise PreflightError("SEED_REQUIRES_EMPTY_FRESH_DATABASE")
        if connection.execute(
            "SELECT EXISTS(SELECT 1 FROM pg_catalog.pg_event_trigger WHERE evtenabled<>'D')"
        ).fetchone()[0]:
            raise PreflightError("SEED_EVENT_TRIGGER_UNSAFE")
        exists = {name: _narrow_role(connection, name) for name in [writer_role, reader_role]}
        # PostgreSQL 15+ public schema can be owned by pg_database_owner. Never
        # grant runtime roles schema ownership or CREATE; remove the PUBLIC grant
        # only in this verified empty dedicated demo database.
        connection.execute("REVOKE CREATE ON SCHEMA public FROM PUBLIC")
        for name, password in [(writer_role, writer_password), (reader_role, reader_password)]:
            if not exists[name]:
                verifier = connection.pgconn.encrypt_password(
                    password.encode(), name.encode(), b"scram-sha-256"
                ).decode()
                connection.execute(
                    sql.SQL(
                        "CREATE ROLE {} LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS PASSWORD {}"
                    ).format(sql.Identifier(name), sql.Literal(verifier))
                )
            _narrow_role(connection, name)
            connection.execute(
                sql.SQL("GRANT CONNECT ON DATABASE {} TO {}").format(
                    sql.Identifier(expected_database), sql.Identifier(name)
                )
            )
            connection.execute(
                sql.SQL("GRANT USAGE ON SCHEMA public TO {}").format(sql.Identifier(name))
            )
        connection.execute(
            sql.SQL("ALTER ROLE {} SET default_transaction_read_only=on").format(
                sql.Identifier(reader_role)
            )
        )
        # Ordinary RDS bootstrap administrators may need SET ROLE membership and
        # temporary schema CREATE to transfer ownership. Remove only our new
        # membership; all grants stay invisible until the transaction commits.
        admin_is_super = connection.execute(
            "SELECT rolsuper FROM pg_catalog.pg_roles WHERE rolname=current_user"
        ).fetchone()[0]
        temporary_membership = False
        if (
            not admin_is_super
            and not connection.execute(
                "SELECT pg_catalog.pg_has_role(current_user,%s,'SET')", (writer_role,)
            ).fetchone()[0]
        ):
            if (
                exists[writer_role]
                and connection.execute(
                    """SELECT EXISTS(SELECT 1 FROM pg_catalog.pg_auth_members m
                JOIN pg_catalog.pg_roles u ON u.oid=m.member JOIN pg_catalog.pg_roles r ON r.oid=m.roleid
                WHERE u.rolname=current_user AND r.rolname=%s)""",
                    (writer_role,),
                ).fetchone()[0]
            ):
                raise PreflightError("SEED_ADMIN_ROLE_TRANSFER_UNSUPPORTED")
            connection.execute(
                sql.SQL("GRANT {} TO {} WITH INHERIT FALSE, SET TRUE").format(
                    sql.Identifier(writer_role), sql.Identifier(connection.info.user)
                )
            )
            temporary_membership = True
        connection.execute(
            sql.SQL("GRANT CREATE ON SCHEMA public TO {}").format(sql.Identifier(writer_role))
        )
        connection.execute(sql.SQL("SET LOCAL ROLE {}").format(sql.Identifier(writer_role)))
        connection.execute(
            "CREATE TABLE public.customers (id integer PRIMARY KEY, email text NOT NULL, created_at timestamp with time zone NOT NULL)"
        )
        connection.execute("""INSERT INTO public.customers SELECT i,'customer-'||i::text||'@example.invalid',
            timestamptz '2026-01-01 00:00:00+00'+i*interval '1 second' FROM pg_catalog.generate_series(1,1000) i""")
        connection.execute("REVOKE ALL ON public.customers FROM PUBLIC")
        connection.execute(
            sql.SQL("GRANT SELECT ON public.customers TO {}").format(sql.Identifier(reader_role))
        )
        if connection.execute("SELECT count(*) FROM public.customers").fetchone()[0] != 1000:
            raise PreflightError("SEED_POSTCONDITION_FAILED")
        connection.execute("RESET ROLE")
        connection.execute(
            sql.SQL("REVOKE CREATE ON SCHEMA public FROM {}").format(sql.Identifier(writer_role))
        )
        if temporary_membership:
            connection.execute(
                sql.SQL("REVOKE {} FROM {}").format(
                    sql.Identifier(writer_role), sql.Identifier(connection.info.user)
                )
            )
        _narrow_role(connection, writer_role)
        _narrow_role(connection, reader_role)
        # Reader is not a member of the table owner, and gets no default ACLs.
        commit_started = True
        connection.execute("COMMIT")
        return {
            "outcome": "committed",
            "evidence_backend": backend,
            "fixture_version": "synthetic-customers-1",
            "database": expected_database,
            "table": "public.customers",
            "row_count": 1000,
            "writer_role": writer_role,
            "reader_role": reader_role,
        }
    except Exception as exc:
        if commit_started:
            raise PreflightError("SEED_OUTCOME_UNKNOWN") from None
        rollback_confirmed = False
        if not connection.closed:
            try:
                connection.execute("ROLLBACK")
                rollback_confirmed = connection.info.transaction_status == TransactionStatus.IDLE
            except Exception:
                pass
        if not rollback_confirmed:
            raise PreflightError("SEED_OUTCOME_UNKNOWN") from None
        if isinstance(exc, PreflightError):
            raise exc from None
        raise PreflightError("SEED_SETUP_ROLLED_BACK") from None


def apply_connected(plan: SeedPlan, *, sts, rds, secrets):
    """Connected bootstrap boundary. Tests inject adapters; this agent never calls AWS."""
    _check_refs(plan)
    if not plan.source_seed_authorized:
        raise PreflightError("SOURCE_SEED_NOT_AUTHORIZED")
    conn = None
    try:
        if sts.get_caller_identity()["Account"] != plan.account_id:
            raise PreflightError("SEED_ACCOUNT_MISMATCH")
        instances = rds.describe_db_instances(DBInstanceIdentifier=plan.source_instance_id)[
            "DBInstances"
        ]
        arn = f"arn:aws:rds:{plan.region}:{plan.account_id}:db:{plan.source_instance_id}"
        if len(instances) != 1:
            raise PreflightError("SEED_SOURCE_IDENTITY_INVALID")
        source = instances[0]
        if (
            source["DBInstanceIdentifier"] != plan.source_instance_id
            or source["DBInstanceArn"] != arn
            or source["DBInstanceStatus"] != "available"
            or source["DBName"] != plan.database
            or source["Engine"] != "postgres"
            or not source["EngineVersion"].startswith("18.")
            or source["PubliclyAccessible"] is not False
            or source["StorageEncrypted"] is not True
        ):
            raise PreflightError("SEED_SOURCE_IDENTITY_INVALID")
        tags = {
            t["Key"]: t["Value"] for t in rds.list_tags_for_resource(ResourceName=arn)["TagList"]
        }
        if any(
            tags.get(k) != v
            for k, v in {
                "Project": "Preflight",
                "Owner": plan.owner,
                "Purpose": "synthetic-source",
            }.items()
        ):
            raise PreflightError("SEED_SOURCE_OWNERSHIP_INVALID")
        credentials = []
        for ref in [plan.admin_secret_arn, plan.writer_secret_arn, plan.reader_secret_arn]:
            value = strict_json(
                secrets.get_secret_value(SecretId=ref)["SecretString"].encode(), 16384
            )
            if (
                not isinstance(value, dict)
                or set(value) - {"username", "password", "dbname"}
                or not isinstance(value.get("username"), str)
                or not isinstance(value.get("password"), str)
                or value.get("dbname", plan.database) != plan.database
            ):
                raise PreflightError("SEED_CREDENTIAL_CONFIGURATION_INVALID")
            credentials.append(value)
        admin, writer, reader = credentials
        if (
            admin["username"] != source["MasterUsername"]
            or writer["username"] != plan.writer_role
            or reader["username"] != plan.reader_role
        ):
            raise PreflightError("SEED_CREDENTIAL_CONFIGURATION_INVALID")
        endpoint = source["Endpoint"]
        if (
            not re.fullmatch(r"[a-zA-Z0-9.-]+\.rds\.amazonaws\.com", endpoint["Address"])
            or endpoint["Port"] != 5432
        ):
            raise PreflightError("SEED_ENDPOINT_INVALID")
        # Deliberately separate from the runtime's non-admin connection factory.
        conn = psycopg.connect(
            host=endpoint["Address"],
            port=5432,
            dbname=plan.database,
            user=admin["username"],
            password=admin["password"],
            sslmode="verify-full",
            sslrootcert=plan.sslrootcert,
            client_encoding="UTF8",
            connect_timeout=10,
            autocommit=True,
            application_name="preflight-source-bootstrap",
        )

        def probe_role(value):
            role_conn = connect_database(
                endpoint["Address"],
                5432,
                plan.database,
                value["username"],
                value["password"],
                plan.sslrootcert,
            )
            role_conn.close()

        # Check already-provisioned logins before making any fixture writes;
        # never rotate their passwords or seed through an administrative login.
        for value in [writer, reader]:
            if _narrow_role(conn, value["username"]):
                probe_role(value)
        result = seed_fresh(
            conn,
            writer_role=plan.writer_role,
            reader_role=plan.reader_role,
            writer_password=writer["password"],
            reader_password=reader["password"],
            expected_database=plan.database,
            backend="aws_rds",
        )
        try:
            for value in [writer, reader]:
                probe_role(value)
            result["runtime_login_verification"] = "VERIFIED"
        except PreflightError:
            # Setup already committed: no claimed rollback and no automatic retry.
            result["runtime_login_verification"] = "FAILED_AFTER_COMMIT"
        return result
    except PreflightError:
        raise
    except Exception:
        raise PreflightError("SEED_CONNECTED_SETUP_FAILED") from None
    finally:
        if conn is not None:
            conn.close()


def _write_once(path, value):
    missing = []
    ancestor = path.parent
    while not ancestor.exists():
        missing.append(ancestor)
        ancestor = ancestor.parent
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    with path.open("xb") as handle:
        path.chmod(0o600)
        handle.write(canonical_json(value) + b"\n")
        handle.flush()
        os.fsync(handle.fileno())
    if os.name != "nt":
        for directory in dict.fromkeys([path.parent, *(p.parent for p in missing)]):
            fd = os.open(directory, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
            try:
                os.fsync(fd)
            finally:
                os.close(fd)


def _intent_path(plan):
    # Stable per owned source, independent of chosen receipt path or plan revision.
    return (
        Path(__file__).resolve().parents[1]
        / "var"
        / "source-seed-attempts"
        / f"{plan.account_id}-{plan.region}-{plan.source_instance_id}.intent.json"
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    plan_cmd = commands.add_parser("plan", help="Offline: no network, secrets or DB connection")
    plan_cmd.add_argument("--operator", required=True, type=Path)
    plan_cmd.add_argument("--admin-secret-arn", required=True)
    plan_cmd.add_argument("--sslrootcert", required=True)
    plan_cmd.add_argument("--out", required=True, type=Path)
    apply_cmd = commands.add_parser("apply", help="Separately approved fresh source initialization")
    apply_cmd.add_argument("--operator", required=True, type=Path)
    apply_cmd.add_argument("--plan", required=True, type=Path)
    apply_cmd.add_argument("--approval", required=True, type=Path)
    apply_cmd.add_argument("--receipt", required=True, type=Path)
    args = parser.parse_args()
    try:
        operator = strict_json(args.operator.read_bytes(), 65536)
        if args.command == "plan":
            envelope = plan_envelope(build_plan(operator, args.admin_secret_arn, args.sslrootcert))
            _write_once(args.out, envelope)
            print(
                json.dumps(
                    {
                        "status": "PLANNED_OFFLINE",
                        "plan_sha256": envelope["plan_sha256"],
                        "source_seed_authorized": envelope["plan"]["source_seed_authorized"],
                    }
                )
            )
            return 0
        envelope = strict_json(args.plan.read_bytes(), 65536)
        plan = approve_plan(envelope, operator, strict_json(args.approval.read_bytes(), 16384))
        intent = _intent_path(plan)
        if args.receipt.exists() or intent.exists():
            raise PreflightError("SEED_ATTEMPT_EXISTS_MANUAL_RESOLUTION_REQUIRED")
        _write_once(
            intent,
            {
                "plan_sha256": envelope["plan_sha256"],
                "source_instance_id": plan.source_instance_id,
                "operation": plan.operation,
                "state": "SEED_INTENT",
                "created_at": datetime.now(timezone.utc).isoformat(),
            },
        )
        import boto3

        session = boto3.Session(region_name=plan.region)
        try:
            result = apply_connected(
                plan,
                sts=session.client("sts"),
                rds=session.client("rds"),
                secrets=session.client("secretsmanager"),
            )
        except PreflightError as exc:
            _write_once(
                args.receipt,
                {
                    "plan_sha256": envelope["plan_sha256"],
                    "status": "FAILED_OR_INCOMPLETE",
                    "reason_code": exc.code,
                    "automatic_retry": False,
                },
            )
            raise
        _write_once(
            args.receipt,
            {
                "plan_sha256": envelope["plan_sha256"],
                "source_instance_id": plan.source_instance_id,
                "result": result,
            },
        )
        verified = result.get("runtime_login_verification") == "VERIFIED"
        print(
            json.dumps(
                {
                    "status": "SEEDED" if verified else "SEEDED_LOGIN_CHECK_FAILED",
                    "row_count": 1000,
                    "automatic_retry": False,
                }
            )
        )
        return 0 if verified else 2
    except PreflightError as exc:
        print(json.dumps({"status": "BLOCKED", "reason_code": exc.code, "automatic_retry": False}))
        return 2
    except Exception:
        print(
            json.dumps(
                {
                    "status": "BLOCKED",
                    "reason_code": "SEED_OPERATION_FAILED",
                    "automatic_retry": False,
                }
            )
        )
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
