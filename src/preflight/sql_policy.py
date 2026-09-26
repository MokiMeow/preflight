"""Positive PostgreSQL 18 grammar. Never execute a deparsed AST."""
import re
import pglast
from pglast import parse_sql
from .models import Contract, CoverageEntry, PreflightError, SqlPlan, WriteEntry


def _deny():
    raise PreflightError("SQL_POLICY_REJECTED")


def _fields(node, allowed):
    # Unknown parser fields fail closed even when their value is empty.
    if set(node) - set(allowed) - {"@", "location"}:
        _deny()


def _name(value):
    if not isinstance(value, str) or not re.fullmatch(r"[a-z_][a-z0-9_]{0,62}", value):
        _deny()
    return value


def _expr(n, predicate=False):
    """Return reads; only these exact expression node shapes are supported."""
    kind = n.get("@")
    if kind == "ColumnRef":
        _fields(n, {"fields"})
        if len(n["fields"]) != 1 or n["fields"][0]["@"] != "String":
            _deny()
        return {_name(n["fields"][0]["sval"])}
    if kind == "A_Const":
        _fields(n, {"isnull", "val"})
        if not n["isnull"] and n["val"]["@"] not in {"String", "Integer"}:
            _deny()
        return set()
    if predicate and kind == "BoolExpr":
        _fields(n, {"boolop", "args"})
        op = n["boolop"]["name"]
        if op not in {"AND_EXPR", "OR_EXPR", "NOT_EXPR"}:
            _deny()
        if len(n["args"]) < (1 if op == "NOT_EXPR" else 2):
            _deny()
        if op == "NOT_EXPR" and len(n["args"]) != 1:
            _deny()
        return set().union(*(_expr(x, True) for x in n["args"]))
    if predicate and kind == "NullTest":
        _fields(n, {"arg", "nulltesttype", "argisrow"})
        if n["argisrow"] or n["arg"]["@"] != "ColumnRef" or n["nulltesttype"]["name"] not in {"IS_NULL", "IS_NOT_NULL"}:
            _deny()
        return _expr(n["arg"])
    if predicate and kind == "A_Expr":
        _fields(n, {"kind", "name", "lexpr", "rexpr", "rexpr_list_start", "rexpr_list_end"})
        if n["kind"]["name"] != "AEXPR_OP" or n["name"] != ({"@": "String", "sval": "="},):
            _deny()
        if n["lexpr"]["@"] != "ColumnRef" or n["rexpr"]["@"] not in {"A_Const", "ColumnRef"}:
            _deny()
        return _expr(n["lexpr"]) | _expr(n["rexpr"])
    _deny()


def inspect_sql(sql_bytes: bytes, contract: Contract) -> SqlPlan:
    if pglast.__version__ != "v8.4" or pglast.get_postgresql_version()[0] != 18:
        raise PreflightError("PARSER_MAJOR_MISMATCH")
    if not sql_bytes or len(sql_bytes) > 65536 or b"\0" in sql_bytes:
        raise PreflightError("INVALID_SQL_BYTES")
    try:
        statements = parse_sql(sql_bytes.decode("utf-8", errors="strict"))
    except Exception:
        raise PreflightError("SQL_PARSE_REJECTED") from None
    if not statements or len(statements) > 128:
        _deny()
    tables = {t.name: t for t in contract.tables}
    writes = []
    added = {name: set() for name in tables}
    for raw in statements:
        n = raw()["stmt"]
        if n["@"] not in {"AlterTableStmt", "UpdateStmt"}:
            _deny()
        rel = n["relation"]
        _fields(rel, {"catalogname", "schemaname", "relname", "inh", "relpersistence", "alias"})
        if rel["catalogname"] or rel["alias"] or not rel["inh"] or rel["relpersistence"] != "p":
            _deny()
        table = f'{_name(rel["schemaname"])}.{_name(rel["relname"])}'
        if table not in tables:
            _deny()
        tc = tables[table]
        if n["@"] == "UpdateStmt":
            _fields(n, {"relation", "targetList", "whereClause", "fromClause", "returningClause", "withClause"})
            if n["fromClause"] or n["returningClause"] or n["withClause"]:
                _deny()
            reads = _expr(n["whereClause"], True) if n["whereClause"] else set()
            for target in n["targetList"]:
                _fields(target, {"name", "indirection", "val"})
                col = _name(target["name"])
                if target["indirection"] or col in tc.primary_key:
                    _deny()
                writes.append(WriteEntry(table=table, column=col, operation="update", read_columns=sorted(reads | _expr(target["val"]))))
        else:
            _fields(n, {"relation", "cmds", "objtype", "missing_ok"})
            if n["missing_ok"] or n["objtype"]["name"] != "OBJECT_TABLE":
                _deny()
            for cmd in n["cmds"]:
                _fields(cmd, {"subtype", "name", "num", "newowner", "def_", "behavior", "missing_ok", "recurse"})
                if cmd["missing_ok"] or cmd["newowner"] or cmd["num"] or cmd["recurse"] or cmd["behavior"]["name"] != "DROP_RESTRICT":
                    _deny()
                op = cmd["subtype"]["name"]
                if op == "AT_SetNotNull" and cmd["def_"] is None:
                    col = _name(cmd["name"])
                    operation = "set_not_null"
                elif op == "AT_AddColumn":
                    d = cmd["def_"]
                    if d["@"] != "ColumnDef":
                        _deny()
                    # Every field is explicitly inspected; harmless parser defaults are fixed.
                    permitted = {"colname", "typeName", "constraints", "location", "@"}
                    defaults = {"compression": None, "inhcount": 0, "is_local": True, "is_not_null": False, "is_from_type": False, "storage": "\0", "storage_name": None, "raw_default": None, "cooked_default": None, "identity": "\0", "identitySequence": None, "generated": "\0", "collClause": None, "fdwoptions": None}
                    if set(d) - permitted - set(defaults) or any(d.get(k) != v for k,v in defaults.items()):
                        _deny()
                    typ = d["typeName"]
                    _fields(typ, {"names", "setof", "pct_type", "typmods", "typemod", "arrayBounds"})
                    if typ["names"] not in [({"@":"String", "sval":"text"},), ({"@":"String", "sval":"pg_catalog"}, {"@":"String", "sval":"text"})] or typ["setof"] or typ["pct_type"] or typ["typmods"] or typ["arrayBounds"] or typ["typemod"] != -1:
                        _deny()
                    for constraint in d["constraints"] or ():
                        # Match the complete parser shape of plain NOT NULL, not just its tag.
                        template = parse_sql("ALTER TABLE public.x ADD COLUMN y text NOT NULL")[0]()["stmt"]["cmds"][0]["def_"]["constraints"][0]
                        if {k:v for k,v in constraint.items() if k != "location"} != {k:v for k,v in template.items() if k != "location"}:
                            _deny()
                    col = _name(d["colname"])
                    if not tc.expected_schema or col not in {c.name for c in tc.expected_schema.added_columns} or col in added[table]:
                        _deny()
                    added[table].add(col)
                    operation = "add_column"
                else:
                    _deny()
                writes.append(WriteEntry(table=table, column=col, operation=operation))
    return SqlPlan(statement_count=len(statements), writes=writes, tables=sorted({w.table for w in writes}))


def resolve_coverage(plan: SqlPlan, contract: Contract, columns: dict[str, list[str]]) -> list[CoverageEntry]:
    tables = {t.name:t for t in contract.tables}
    result = []
    for w in plan.writes:
        t = tables[w.table]
        existing = columns.get(w.table, [])
        expected = {c.name:c for c in t.expected_schema.added_columns} if t.expected_schema else {}
        if w.column not in existing and w.column not in expected or not set(w.read_columns) <= set(existing) | set(expected):
            raise PreflightError("UNKNOWN_COLUMN")
        if w.operation == "add_column" and w.column in existing:
            raise PreflightError("COLUMN_ALREADY_EXISTS")
        rule = "missing"
        if w.operation == "update" and w.column in existing and w.column in t.preserve_columns:
            rule = "preserved"
        elif w.operation == "set_not_null":
            if w.column in expected and not expected[w.column].nullable and all(any(c.type == typ and getattr(c,"column",None) == w.column for c in t.checks) for typ in ["column_not_null", "no_nulls"]):
                rule = "schema"
        elif any(c.type == "all_equal" and c.column == w.column for c in t.checks):
            if w.operation != "add_column" or w.column in expected:
                rule = "all_equal"
        result.append(CoverageEntry(table=w.table, column=w.column, operation=w.operation, rule=rule, complete=rule != "missing", reason_code="COVERAGE_INCOMPLETE" if rule == "missing" else None))
    return result
