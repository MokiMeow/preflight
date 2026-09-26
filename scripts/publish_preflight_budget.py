"""Operator-only cost publication; no MCP tool, defaults or invented cost facts.

Run on the private Linux host as root with a root-owned, nonwritable config and
directory chain. No operational config is shipped. Cost Explorer is delayed:
https://docs.aws.amazon.com/cost-management/latest/userguide/ce-what-is.html
The API date end is exclusive and Estimated costs are not final:
https://docs.aws.amazon.com/aws-cost-management/latest/APIReference/API_GetCostAndUsage.html

Provider amounts and trusted operator bounds are explicitly different evidence.
The operator must substantiate full-footprint retention and an unbilled upper
bound covering the ENTIRE continuation window, not merely an expiry tag. This
script cannot enforce cleanup, confer human approval, or guarantee a hard cap.
It deliberately refuses absent/estimated/ambiguous billing and leaves the
ledger untouched. AWS read calls themselves can have a cost; authorize those
separately before invoking this admin script. Import and tests make no AWS call.
"""

import argparse
import os
import re
import stat
from datetime import UTC, datetime, timedelta
from decimal import ROUND_CEILING, Decimal, localcontext
from pathlib import Path

from preflight.artifacts import canonical_json, sha256, strict_json
from preflight.budget import BudgetLedger, BudgetSnapshot, admit
from preflight.models import PreflightError


def _refuse(code):
    raise PreflightError(code)


def _amount(value):
    if not isinstance(value, str):
        _refuse("BUDGET_OPERATOR_CONFIGURATION_INVALID")
    try:
        amount = Decimal(value)
    except Exception:
        _refuse("BUDGET_OPERATOR_CONFIGURATION_INVALID")
    if not amount.is_finite() or amount < 0:
        _refuse("BUDGET_OPERATOR_CONFIGURATION_INVALID")
    return amount


def _time(value):
    try:
        result = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if result.utcoffset() != timedelta(0):
            raise ValueError
        return result
    except Exception:
        _refuse("BUDGET_OPERATOR_CONFIGURATION_INVALID")


def validate_operator_config(config, now):
    """Validate attestations, never claim they are provider-measured guarantees."""
    required = {
        "account_id",
        "continuation_start",
        "valid_until",
        "verified_at",
        "ceiling_usd",
        "accrual_upper_bound_usd",
        "retained_upper_bound_usd",
        "safety_reserve_usd",
        "max_billing_lag_seconds",
        "per_kind_quotes",
        "full_footprint_verified",
        "unbilled_entire_window_bounded",
        "future_retention_enforceable",
        "retention_enforcement",
        "pricing_provenance",
        "inventory_provenance",
        "retention_provenance",
    }
    if not isinstance(config, dict) or set(config) != required:
        _refuse("BUDGET_OPERATOR_CONFIGURATION_INVALID")
    if not isinstance(config["account_id"], str) or not re.fullmatch(
        r"\d{12}", config["account_id"]
    ):
        _refuse("BUDGET_OPERATOR_CONFIGURATION_INVALID")
    for name in (
        "full_footprint_verified",
        "unbilled_entire_window_bounded",
        "future_retention_enforceable",
    ):
        if config[name] is not True:
            _refuse("BUDGET_OPERATOR_BOUND_UNKNOWN")
    for name in (
        "retention_enforcement",
        "pricing_provenance",
        "inventory_provenance",
        "retention_provenance",
    ):
        if (
            not isinstance(config[name], str)
            or not config[name].strip()
            or len(config[name]) > 2048
        ):
            _refuse("BUDGET_OPERATOR_BOUND_UNKNOWN")
    if (
        "expiresat" in config["retention_enforcement"].lower()
        or "expiry tag" in config["retention_enforcement"].lower()
    ):
        _refuse("BUDGET_OPERATOR_BOUND_UNKNOWN")
    start, verified, until = (
        _time(config[k]) for k in ("continuation_start", "verified_at", "valid_until")
    )
    if (
        now.utcoffset() != timedelta(0)
        or not start <= verified <= now < until
        or (now - verified).total_seconds() > 300
    ):
        _refuse("BUDGET_OPERATOR_OBSERVATION_STALE")
    if until < verified + timedelta(seconds=300):
        _refuse("BUDGET_OPERATOR_BOUND_EXPIRES_EARLY")
    lag = config["max_billing_lag_seconds"]
    if type(lag) is not int or lag < 0:
        _refuse("BUDGET_OPERATOR_CONFIGURATION_INVALID")
    for key in (
        "ceiling_usd",
        "accrual_upper_bound_usd",
        "retained_upper_bound_usd",
        "safety_reserve_usd",
    ):
        _amount(config[key])
    if not 0 < _amount(config["ceiling_usd"]) <= 100:
        _refuse("BUDGET_CEILING_NOT_AUTHORIZED")
    quotes = config["per_kind_quotes"]
    if not isinstance(quotes, dict) or set(quotes) != {"snapshot", "clone"}:
        _refuse("BUDGET_QUOTE_UNKNOWN")
    for quote in quotes.values():
        _amount(quote)
    return start, verified, until


def read_protected_config(path):
    """OS boundary: root only, no symlinks, no writable ancestor or config."""
    if os.name != "posix" or os.geteuid() != 0:
        _refuse("BUDGET_OPERATOR_CONTEXT_REQUIRED")
    try:
        path = Path(path).absolute()
        for target in (path, *path.parents):
            info = target.lstat()
            if stat.S_ISLNK(info.st_mode) or info.st_uid != 0 or info.st_mode & 0o022:
                _refuse("BUDGET_OPERATOR_CONFIGURATION_UNPROTECTED")
        info = path.stat()
        if not stat.S_ISREG(info.st_mode) or info.st_mode & 0o077:
            _refuse("BUDGET_OPERATOR_CONFIGURATION_UNPROTECTED")
        # O_NOFOLLOW closes the leaf symlink race; protected ancestors prevent swaps.
        descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
        with os.fdopen(descriptor, "rb") as handle:
            raw = handle.read(16385)
    except FileNotFoundError:
        _refuse("BUDGET_OPERATOR_CONFIGURATION_MISSING")
    except (OSError, ValueError, TypeError):
        _refuse("BUDGET_OPERATOR_CONFIGURATION_UNPROTECTED")
    return strict_json(raw, 16384)


def prepare_ledger_writer(path):
    """Use the runtime-created private ledger as its existing service account.

    Root-owned config remains inaccessible to the model/service. Publishing as
    the service uid avoids creating root-owned SQLite WAL/SHM beside its ledger.
    The ledger path is explicit operator input, never supplied by MCP/model.
    """
    if os.name != "posix" or os.geteuid() != 0:
        _refuse("BUDGET_OPERATOR_CONTEXT_REQUIRED")
    import pwd

    identity = pwd.getpwnam("preflight")
    path = Path(path).absolute()
    info = path.lstat()  # Refuse absent state; runtime owns ledger initialization.
    if (
        identity.pw_uid == 0
        or not stat.S_ISREG(info.st_mode)
        or info.st_uid != identity.pw_uid
        or info.st_mode & 0o077
    ):
        _refuse("BUDGET_RUNTIME_LEDGER_UNPROTECTED")
    for parent in path.parents:
        info = parent.lstat()
        if (
            not stat.S_ISDIR(info.st_mode)
            or info.st_uid not in {0, identity.pw_uid}
            or info.st_mode & 0o022
        ):
            _refuse("BUDGET_RUNTIME_LEDGER_UNPROTECTED")
    os.setgroups([])
    os.setgid(identity.pw_gid)
    os.setuid(identity.pw_uid)


def publish(config, ce, sts, ledger_path, *, now, ledger_factory=BudgetLedger):
    """Fetch whole-account costs; create/update ledger ONLY after all checks.

    Clients/config injection is for deterministic tests/trusted admin composition,
    never exposed through a model tool. No user-supplied spent/freshness fields.
    """
    start, verified, until = validate_operator_config(config, now)
    end = now.date()
    first = start.date()  # Earlier same-day costs conservatively count as spent.
    coverage_end = datetime.combine(end, datetime.min.time(), UTC)
    if first >= end:
        _refuse("BUDGET_COST_WINDOW_UNAVAILABLE")
    if (now - coverage_end).total_seconds() > config["max_billing_lag_seconds"]:
        _refuse("BUDGET_BILLING_COVERAGE_STALE")
    try:
        identity = sts.get_caller_identity()
        if identity.get("Account") != config["account_id"]:
            _refuse("BUDGET_ACCOUNT_SCOPE_MISMATCH")
        response = ce.get_cost_and_usage(
            TimePeriod={"Start": first.isoformat(), "End": end.isoformat()},
            Granularity="DAILY",
            Metrics=["UnblendedCost"],
            GroupBy=[{"Type": "DIMENSION", "Key": "LINKED_ACCOUNT"}],
        )
    except PreflightError:
        raise
    except Exception:
        _refuse("BUDGET_PROVIDER_COST_UNAVAILABLE")
    if response.get("NextPageToken") or response.get("GroupDefinitions") != [
        {"Type": "DIMENSION", "Key": "LINKED_ACCOUNT"}
    ]:
        _refuse("BUDGET_PROVIDER_SCOPE_INCOMPLETE")
    buckets = response.get("ResultsByTime")
    if not isinstance(buckets, list) or len(buckets) != (end - first).days:
        _refuse("BUDGET_PROVIDER_SCOPE_INCOMPLETE")
    spent = Decimal(0)
    expected = first
    for bucket in buckets:
        if bucket.get("Estimated") is not False:
            _refuse("BUDGET_PROVIDER_COST_ESTIMATED")
        following = expected + timedelta(days=1)
        if bucket.get("TimePeriod") != {
            "Start": expected.isoformat(),
            "End": following.isoformat(),
        }:
            _refuse("BUDGET_PROVIDER_SCOPE_INCOMPLETE")
        groups = bucket.get("Groups")
        if (
            not isinstance(groups, list)
            or len(groups) != 1
            or groups[0].get("Keys") != [config["account_id"]]
        ):
            _refuse("BUDGET_ACCOUNT_SCOPE_AMBIGUOUS")
        metrics = groups[0].get("Metrics", {}).get("UnblendedCost", {})
        if metrics.get("Unit") != "USD":
            _refuse("BUDGET_PROVIDER_CURRENCY_INVALID")
        try:
            provider_amount = _amount(metrics.get("Amount"))
        except PreflightError:
            _refuse("BUDGET_PROVIDER_COST_INVALID")
        with localcontext() as context:
            context.prec = 50
            context.rounding = ROUND_CEILING
            spent += provider_amount
        expected = following
    snapshot = BudgetSnapshot(
        _amount(config["ceiling_usd"]),
        spent,
        _amount(config["accrual_upper_bound_usd"]),
        _amount(config["retained_upper_bound_usd"]),
        _amount(config["safety_reserve_usd"]),
        verified,
        scope_complete=True,
        ongoing_costs_bounded=True,
    )
    decision = admit(snapshot, Decimal(0), now=now, max_age_seconds=300)
    if not decision.admitted:
        _refuse(decision.reason_code)
    provenance = canonical_json(
        {
            "kind": "PROVIDER_REPORTED_SPEND_PLUS_TRUSTED_OPERATOR_BOUNDS",
            "config_sha256": sha256(canonical_json(config)),
            "provider_period_start": first.isoformat(),
            "provider_period_end_exclusive": end.isoformat(),
            "operator_verified_at": verified.isoformat(),
            "operator_bound_valid_until": until.isoformat(),
            "provider_response_sha256": sha256(canonical_json(buckets)),
        }
    ).decode()
    ledger = ledger_factory(ledger_path, snapshot.ceiling_usd)
    ledger.record_observation(
        snapshot, {k: _amount(v) for k, v in config["per_kind_quotes"].items()}, provenance
    )
    return {
        "status": "PUBLISHED",
        "evidence_kind": "PROVIDER_REPORTED_SPEND_PLUS_TRUSTED_OPERATOR_BOUNDS",
        "provider_costs_current_guaranteed": False,
        "native_hard_cap_enforced": False,
        "billing_coverage_end_exclusive": end.isoformat(),
        "operator_bound_valid_until": until.isoformat(),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--config", type=Path, default=Path("/etc/preflight/budget-publication.json")
    )
    parser.add_argument(
        "--ledger", type=Path, required=True, help="Exact existing runtime-owned budget.sqlite path"
    )
    args = parser.parse_args()
    try:
        config = read_protected_config(args.config)
        now = datetime.now(UTC)
        validate_operator_config(config, now)  # Refuse before constructing clients.
        prepare_ledger_writer(args.ledger)
        import boto3
        from botocore.config import Config

        options = Config(connect_timeout=5, read_timeout=10, retries={"max_attempts": 0})
        session = boto3.Session()
        result = publish(
            config,
            session.client("ce", region_name="us-east-1", config=options),
            session.client("sts", region_name="us-east-1", config=options),
            args.ledger,
            now=now,
        )
    except Exception as exc:
        print(
            canonical_json(
                {
                    "status": "BLOCKED",
                    "reason_code": exc.code
                    if isinstance(exc, PreflightError)
                    else "BUDGET_PUBLICATION_FAILED",
                    "native_hard_cap_enforced": False,
                }
            ).decode()
        )
        return 2
    print(canonical_json(result).decode())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
