"""Verified connections, catalog confinement and honest transaction outcomes."""
import hashlib
import threading
import time
import psycopg
from psycopg import sql
from psycopg.pq import TransactionStatus
from .models import Contract, PreflightError, SqlPlan, TxOutcome

SUPPORTED_TYPES = {20:"bigint", 21:"smallint", 23:"integer", 25:"text", 1184:"timestamp with time zone"}


def connect_database(host, port, database, user, password, sslrootcert, postgres_major=18):
    try:
        conn = psycopg.connect(host=host, port=port, dbname=database, user=user,
                               password=password, sslmode="verify-full", sslrootcert=sslrootcert,
                               connect_timeout=10, autocommit=True, application_name="preflight")
        if conn.info.server_version // 10000 != postgres_major or postgres_major != 18:
            conn.close()
            raise PreflightError("DATABASE_MAJOR_MISMATCH")
        with conn.cursor() as cur:
            cur.execute("SELECT rolsuper FROM pg_catalog.pg_roles WHERE rolname=current_user")
            if cur.fetchone()[0] or not conn.pgconn.ssl_in_use:
                conn.close()
                raise PreflightError("DATABASE_SESSION_UNSAFE")
        return conn
    except PreflightError:
        raise
    except Exception:
        raise PreflightError("DATABASE_CONNECTION_FAILED") from None


def validate_catalog(connection, contract: Contract, plan: SqlPlan | None = None):
    """No name-prefix exceptions. Returns normalized supported catalog only."""
    if connection.info.server_version // 10000 != 18:
        raise PreflightError("DATABASE_MAJOR_MISMATCH")
    result = {}
    with connection.cursor() as cur:
        cur.execute("SELECT EXISTS(SELECT 1 FROM pg_catalog.pg_event_trigger WHERE evtenabled <> 'D')")
        if cur.fetchone()[0]:
            raise PreflightError("UNSUPPORTED_EVENT_TRIGGER")
        for table in contract.tables:
            schema, name = table.name.split(".")
            cur.execute("""SELECT c.oid,c.relkind,c.relpersistence,c.relrowsecurity,c.relforcerowsecurity,c.relispartition
                FROM pg_catalog.pg_class c JOIN pg_catalog.pg_namespace n ON n.oid=c.relnamespace
                WHERE n.nspname=%s AND c.relname=%s""", (schema,name))
            row = cur.fetchone()
            if not row:
                raise PreflightError("TABLE_MISSING")
            oid, kind, persistence, rls, force, partition = row
            if kind != "r" or persistence != "p" or rls or force or partition:
                raise PreflightError("UNSUPPORTED_TABLE")
            cur.execute("""SELECT
                EXISTS(SELECT 1 FROM pg_catalog.pg_trigger WHERE tgrelid=%s),
                EXISTS(SELECT 1 FROM pg_catalog.pg_rewrite WHERE ev_class=%s),
                EXISTS(SELECT 1 FROM pg_catalog.pg_inherits WHERE inhrelid=%s OR inhparent=%s),
                EXISTS(SELECT 1 FROM pg_catalog.pg_constraint WHERE (conrelid=%s OR confrelid=%s) AND contype NOT IN ('p','u','n'))""", (oid,oid,oid,oid,oid,oid))
            if any(cur.fetchone()):
                raise PreflightError("UNSUPPORTED_OBJECT_CAPABILITY")
            cur.execute("""SELECT a.attname,a.atttypid,a.attnotnull,a.attnum,a.attgenerated,a.attidentity,
                EXISTS(SELECT 1 FROM pg_catalog.pg_attrdef d WHERE d.adrelid=a.attrelid AND d.adnum=a.attnum),
                a.attcollation,co.collnamespace,co.collname,a.atttypmod
                FROM pg_catalog.pg_attribute a LEFT JOIN pg_catalog.pg_collation co ON co.oid=a.attcollation
                WHERE a.attrelid=%s AND a.attnum>0 AND NOT a.attisdropped ORDER BY a.attnum""", (oid,))
            columns = []
            for col, typeoid, notnull, position, generated, identity, default, collation, collns, collname, typmod in cur.fetchall():
                if typeoid not in SUPPORTED_TYPES or generated or identity or default or typmod != -1:
                    raise PreflightError("UNSUPPORTED_COLUMN")
                if collation and not (collns == 11 and collname == "default"):
                    raise PreflightError("UNSUPPORTED_COLLATION")
                columns.append({"name":col,"type":SUPPORTED_TYPES[typeoid],"nullable":not notnull,"position":position,"default":False})
            cur.execute("""SELECT contype,conkey,condeferrable,condeferred,convalidated,conenforced
                FROM pg_catalog.pg_constraint WHERE conrelid=%s ORDER BY contype,conkey""", (oid,))
            constraints = []
            pk = None
            bynum = {c["position"]:c["name"] for c in columns}
            for kind, keys, defer, deferred, valid, enforced in cur.fetchall():
                if kind not in {"p","u","n"} or defer or deferred or not valid or not enforced:
                    raise PreflightError("UNSUPPORTED_CONSTRAINT")
                names = [bynum[k] for k in keys or []]
                if kind == "p":
                    pk = names
                # PG18 built-in NOT NULL is represented by column nullable already.
                if kind != "n":
                    constraints.append({"kind":kind,"columns":names})
            if pk != table.primary_key:
                raise PreflightError("PRIMARY_KEY_MISMATCH")
            if not set(table.preserve_columns) <= {c["name"] for c in columns}:
                raise PreflightError("PRESERVED_COLUMN_MISSING")
            cur.execute("""SELECT i.indkey::smallint[],i.indisunique,i.indisprimary,i.indisvalid,i.indisready,
                i.indexprs IS NOT NULL,i.indpred IS NOT NULL,am.amname,i.indnkeyatts,i.indnatts,
                EXISTS(SELECT 1 FROM unnest(i.indclass::oid[]) x JOIN pg_catalog.pg_opclass o ON o.oid=x WHERE o.opcnamespace<>11),
                EXISTS(SELECT 1 FROM unnest(i.indcollation::oid[]) x JOIN pg_catalog.pg_collation co ON co.oid=x WHERE co.collnamespace<>11 OR co.collname<>'default')
                FROM pg_catalog.pg_index i JOIN pg_catalog.pg_class c ON c.oid=i.indexrelid
                JOIN pg_catalog.pg_am am ON am.oid=c.relam WHERE i.indrelid=%s ORDER BY i.indkey::text""", (oid,))
            indexes = []
            for keys, unique, primary, valid, ready, expression, partial, method, nkeys, natts, customop, customcoll in cur.fetchall():
                if not unique or not valid or not ready or expression or partial or method != "btree" or nkeys != natts or customop or customcoll or any(k <= 0 for k in keys):
                    raise PreflightError("UNSUPPORTED_INDEX")
                indexes.append({"columns":[bynum[k] for k in keys],"unique":unique,"primary":primary,"method":method})
            result[table.name] = {"columns":columns,"constraints":constraints,"indexes":indexes}
    if plan:
        from .sql_policy import resolve_coverage
        resolve_coverage(plan, contract, {t:[c["name"] for c in m["columns"]] for t,m in result.items()})
        for w in plan.writes:
            if w.operation == "set_not_null":
                found = next((c for c in result[w.table]["columns"] if c["name"] == w.column), None)
                if found and found["type"] != "text":
                    raise PreflightError("UNSUPPORTED_ALTER_TYPE")
    return result


def execute_migration(connection, sql_bytes: bytes, plan: SqlPlan, limits: Contract,
                      checks_before_commit=None, precheck=None) -> TxOutcome:
    from .sql_policy import inspect_sql
    if inspect_sql(sql_bytes, limits) != plan:
        raise PreflightError("SQL_PLAN_MISMATCH")
    if not connection.autocommit or connection.info.transaction_status != TransactionStatus.IDLE:
        raise PreflightError("TRANSACTION_SESSION_NOT_FRESH")
    start = time.monotonic()
    expired = threading.Event()
    def cancel():
        expired.set()
        try:
            connection.cancel()
        except Exception:
            pass
    timer = threading.Timer(limits.max_migration_seconds, cancel)
    timer.daemon = True
    timer.start()
    commit_started = False
    code = None
    state = None
    try:
        with connection.cursor() as cur:
            cur.execute("BEGIN ISOLATION LEVEL READ COMMITTED")
            cur.execute("SELECT pg_catalog.set_config('search_path','pg_catalog',true), pg_catalog.set_config('statement_timeout',%s,true), pg_catalog.set_config('lock_timeout',%s,true)", (str(limits.max_migration_seconds*1000),str(min(2000, limits.max_migration_seconds*1000))))
            if precheck:
                if precheck(connection) is False:
                    raise PreflightError("PRECHECK_FAILED")
            validate_catalog(connection, limits, plan)
            cur.execute(sql_bytes.decode("utf-8"), prepare=False)
            while cur.nextset():
                if cur.description:
                    while cur.fetchmany(128):
                        pass
            if checks_before_commit:
                checks = checks_before_commit(connection)
                if checks is False or hasattr(checks,"checks") and any(c.status != "pass" for c in checks.checks):
                    raise PreflightError("PRECOMMIT_CHECK_FAILED")
            if expired.is_set() or time.monotonic()-start >= limits.max_migration_seconds:
                raise PreflightError("MIGRATION_DEADLINE_EXCEEDED")
            commit_started = True
            cur.execute("COMMIT")
        outcome = "committed"
    except Exception as exc:
        state = getattr(exc,"sqlstate",None)
        code = exc.code if isinstance(exc,PreflightError) else "DATABASE_EXECUTION_FAILED"
        outcome = "unknown"
        # Never issue ROLLBACK after an uncertain COMMIT, nor infer rollback from disconnect.
        if not commit_started and not connection.closed:
            try:
                connection.execute("ROLLBACK")
                if connection.info.transaction_status == TransactionStatus.IDLE:
                    outcome = "rolled_back"
            except Exception:
                pass
    finally:
        timer.cancel()
        timer.join()
    return TxOutcome(outcome=outcome,elapsed_ms=int((time.monotonic()-start)*1000),sqlstate=state,reason_code=code)
