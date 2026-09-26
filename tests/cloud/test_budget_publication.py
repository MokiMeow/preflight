"""Synthetic operator/provider fixtures only; no actual AWS billing observation."""

import copy
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import boto3
import pytest
from botocore.stub import Stubber

from preflight.budget import BudgetLedger
from preflight.models import PreflightError
from scripts.publish_preflight_budget import (
    publish,
    read_protected_config,
    validate_operator_config,
)

NOW = datetime(2026, 9, 26, 1, tzinfo=UTC)
ACCOUNT = "123456789012"


@pytest.fixture
def config():
    return {
        "account_id": ACCOUNT,
        "continuation_start": "2026-09-25T00:00:00Z",
        "verified_at": NOW.isoformat(),
        "valid_until": (NOW + timedelta(hours=1)).isoformat(),
        "ceiling_usd": "100",
        "accrual_upper_bound_usd": "10",
        "retained_upper_bound_usd": "20",
        "safety_reserve_usd": "5",
        "max_billing_lag_seconds": 3600,
        "per_kind_quotes": {"snapshot": "2", "clone": "8"},
        "full_footprint_verified": True,
        "unbilled_entire_window_bounded": True,
        "future_retention_enforceable": True,
        "retention_enforcement": "SYNTHETIC test-only preauthorized independent retention mechanism",
        "pricing_provenance": "SYNTHETIC test-only verified entire-footprint prices",
        "inventory_provenance": "SYNTHETIC test-only all-account inventory",
        "retention_provenance": "SYNTHETIC test-only finite retained footprint",
    }


@pytest.fixture
def clients():
    session = boto3.Session(
        aws_access_key_id="unit-fixture",
        aws_secret_access_key="unit-fixture",
        region_name="us-east-1",
    )
    ce, sts = session.client("ce"), session.client("sts")
    with Stubber(ce) as cs, Stubber(sts) as ss:
        yield ce, sts, cs, ss
        cs.assert_no_pending_responses()
        ss.assert_no_pending_responses()


def queue_identity(ss, account=ACCOUNT):
    ss.add_response(
        "get_caller_identity",
        {"Account": account, "Arn": f"arn:aws:iam::{account}:user/unit", "UserId": "unit"},
        {},
    )


def request():
    return {
        "TimePeriod": {"Start": "2026-09-25", "End": "2026-09-26"},
        "Granularity": "DAILY",
        "Metrics": ["UnblendedCost"],
        "GroupBy": [{"Type": "DIMENSION", "Key": "LINKED_ACCOUNT"}],
    }


def response():
    return {
        "GroupDefinitions": [{"Type": "DIMENSION", "Key": "LINKED_ACCOUNT"}],
        "ResultsByTime": [
            {
                "TimePeriod": {"Start": "2026-09-25", "End": "2026-09-26"},
                "Estimated": False,
                "Total": {},
                "Groups": [
                    {
                        "Keys": [ACCOUNT],
                        "Metrics": {"UnblendedCost": {"Amount": "1.25", "Unit": "USD"}},
                    }
                ],
            }
        ],
    }


def test_provider_spend_operator_bounds_publish_without_reserving(config, clients, tmp_path):
    ce, sts, cs, ss = clients
    queue_identity(ss)
    cs.add_response("get_cost_and_usage", response(), request())
    path = tmp_path / "budget.sqlite"
    result = publish(config, ce, sts, path, now=NOW)
    assert result["status"] == "PUBLISHED"
    assert result["evidence_kind"] == "PROVIDER_REPORTED_SPEND_PLUS_TRUSTED_OPERATOR_BOUNDS"
    assert result["provider_costs_current_guaranteed"] is False
    assert result["native_hard_cap_enforced"] is False
    ledger = BudgetLedger(path)
    assert ledger.total_reserved_usd() == 0
    decision = ledger.authorize("unit:snapshot", "snapshot", NOW)
    assert decision.admitted and decision.accounted_usd == Decimal("36.25")
    assert ledger.total_reserved_usd() == Decimal(2)
    assert not ledger.authorize("unit:clone", "clone", NOW + timedelta(seconds=301)).admitted


@pytest.mark.parametrize(
    "error", ["DataUnavailableException", "AccessDeniedException", "LimitExceededException"]
)
def test_provider_error_has_no_ledger_or_raw_error(config, clients, tmp_path, error):
    ce, sts, cs, ss = clients
    queue_identity(ss)
    cs.add_client_error(
        "get_cost_and_usage", error, "SENSITIVE error must not escape", expected_params=request()
    )
    path = tmp_path / "absent.sqlite"
    with pytest.raises(PreflightError, match="BUDGET_PROVIDER_COST_UNAVAILABLE") as exc:
        publish(config, ce, sts, path, now=NOW)
    assert "SENSITIVE" not in str(exc.value)
    assert not path.exists()


@pytest.mark.parametrize(
    "variant,code",
    [
        ("estimated", "BUDGET_PROVIDER_COST_ESTIMATED"),
        ("currency", "BUDGET_PROVIDER_CURRENCY_INVALID"),
        ("missing", "BUDGET_PROVIDER_SCOPE_INCOMPLETE"),
        ("duplicate", "BUDGET_PROVIDER_SCOPE_INCOMPLETE"),
        ("wrong_date", "BUDGET_PROVIDER_SCOPE_INCOMPLETE"),
        ("other_account", "BUDGET_ACCOUNT_SCOPE_AMBIGUOUS"),
        ("empty_groups", "BUDGET_ACCOUNT_SCOPE_AMBIGUOUS"),
        ("pagination", "BUDGET_PROVIDER_SCOPE_INCOMPLETE"),
        ("negative", "BUDGET_PROVIDER_COST_INVALID"),
        ("nan", "BUDGET_PROVIDER_COST_INVALID"),
    ],
)
def test_incomplete_ambiguous_or_estimated_cost_never_published(
    config, clients, tmp_path, variant, code
):
    ce, sts, cs, ss = clients
    queue_identity(ss)
    data = response()
    bucket = data["ResultsByTime"][0]
    metric = bucket["Groups"][0]["Metrics"]["UnblendedCost"]
    if variant == "estimated":
        bucket["Estimated"] = True
    elif variant == "currency":
        metric["Unit"] = "EUR"
    elif variant == "missing":
        data["ResultsByTime"] = []
    elif variant == "duplicate":
        data["ResultsByTime"].append(copy.deepcopy(bucket))
    elif variant == "wrong_date":
        bucket["TimePeriod"]["Start"] = "2026-09-24"
    elif variant == "other_account":
        bucket["Groups"][0]["Keys"] = ["999999999999"]
    elif variant == "empty_groups":
        bucket["Groups"] = []
    elif variant == "pagination":
        data["NextPageToken"] = "more"
    elif variant == "negative":
        metric["Amount"] = "-1"
    elif variant == "nan":
        metric["Amount"] = "NaN"
    cs.add_response("get_cost_and_usage", data, request())
    with pytest.raises(PreflightError, match=code):
        publish(config, ce, sts, tmp_path / "absent.sqlite", now=NOW)
    assert not (tmp_path / "absent.sqlite").exists()


@pytest.mark.parametrize(
    "field,value",
    [
        ("spent_usd", "0"),
        ("full_footprint_verified", False),
        ("future_retention_enforceable", False),
        ("unbilled_entire_window_bounded", False),
        ("retention_enforcement", "ExpiresAt tags"),
        ("retention_provenance", ""),
        ("pricing_provenance", ""),
        ("ceiling_usd", "101"),
        ("per_kind_quotes", {"snapshot": "1"}),
        ("accrual_upper_bound_usd", None),
        ("valid_until", NOW.isoformat()),
        ("valid_until", (NOW + timedelta(seconds=299)).isoformat()),
        ("verified_at", (NOW - timedelta(seconds=301)).isoformat()),
        ("verified_at", (NOW + timedelta(seconds=1)).isoformat()),
        ("max_billing_lag_seconds", True),
    ],
)
def test_invalid_operator_config_no_provider_call_or_ledger(
    config, clients, tmp_path, field, value
):
    config[field] = value
    ce, sts, _, _ = clients
    with pytest.raises(PreflightError):
        publish(config, ce, sts, tmp_path / "absent.sqlite", now=NOW)
    assert not (tmp_path / "absent.sqlite").exists()


def test_zero_lag_default_cannot_treat_fetch_time_as_fresh(config, clients, tmp_path):
    config["max_billing_lag_seconds"] = 0
    ce, sts, _, _ = clients
    with pytest.raises(PreflightError, match="BUDGET_BILLING_COVERAGE_STALE"):
        publish(config, ce, sts, tmp_path / "absent.sqlite", now=NOW)
    assert not (tmp_path / "absent.sqlite").exists()


def test_wrong_identity_never_queries_costs(config, clients, tmp_path):
    ce, sts, _, ss = clients
    queue_identity(ss, "999999999999")
    with pytest.raises(PreflightError, match="BUDGET_ACCOUNT_SCOPE_MISMATCH"):
        publish(config, ce, sts, tmp_path / "absent.sqlite", now=NOW)
    assert not (tmp_path / "absent.sqlite").exists()


def test_unknown_billing_preserves_existing_observation_and_reservations(config, clients, tmp_path):
    ce, sts, cs, ss = clients
    path = tmp_path / "budget.sqlite"
    queue_identity(ss)
    cs.add_response("get_cost_and_usage", response(), request())
    publish(config, ce, sts, path, now=NOW)
    ledger = BudgetLedger(path)
    assert ledger.authorize("unit:snapshot", "snapshot", NOW).admitted
    queue_identity(ss)
    cs.add_client_error("get_cost_and_usage", "DataUnavailableException", expected_params=request())
    with pytest.raises(PreflightError):
        publish(config, ce, sts, path, now=NOW)
    assert ledger.total_reserved_usd() == 2
    assert ledger.authorize("unit:snapshot", "snapshot", NOW).admitted


def test_root_protected_config_required(tmp_path, monkeypatch):
    # Deterministic host-context refusal; never make the real test runner root.
    import scripts.publish_preflight_budget as module

    monkeypatch.setattr(module.os, "geteuid", lambda: 1000, raising=False)
    with pytest.raises(PreflightError, match="BUDGET_OPERATOR_CONTEXT_REQUIRED"):
        read_protected_config(tmp_path / "missing.json")


def test_bounds_cover_full_ledger_freshness_horizon(config):
    config["valid_until"] = (NOW + timedelta(seconds=300)).isoformat()
    assert validate_operator_config(config, NOW)[2] == NOW + timedelta(seconds=300)


@pytest.mark.parametrize("invalid", ["owner", "world_read", "symlink", "writable_parent"])
def test_ledger_writer_refuses_unprotected_existing_state(monkeypatch, invalid):
    import stat
    import sys
    from pathlib import Path
    from types import SimpleNamespace

    import scripts.publish_preflight_budget as module

    mutations = []
    monkeypatch.setattr(
        module,
        "os",
        SimpleNamespace(
            name="posix",
            geteuid=lambda: 0,
            setgroups=lambda value: mutations.append(("groups", value)),
            setgid=lambda value: mutations.append(("gid", value)),
            setuid=lambda value: mutations.append(("uid", value)),
        ),
    )
    monkeypatch.setitem(
        sys.modules,
        "pwd",
        SimpleNamespace(getpwnam=lambda _: SimpleNamespace(pw_uid=9001, pw_gid=9002)),
    )
    path = Path("/var/lib/preflight/budget.sqlite").absolute()

    def metadata(target):
        if target == path:
            mode = stat.S_IFREG | 0o600
            if invalid == "world_read":
                mode |= 0o004
            if invalid == "symlink":
                mode = stat.S_IFLNK | 0o777
            return SimpleNamespace(st_uid=0 if invalid == "owner" else 9001, st_mode=mode)
        return SimpleNamespace(
            st_uid=0, st_mode=stat.S_IFDIR | (0o777 if invalid == "writable_parent" else 0o755)
        )

    monkeypatch.setattr(Path, "lstat", metadata)
    with pytest.raises(PreflightError, match="BUDGET_RUNTIME_LEDGER_UNPROTECTED"):
        module.prepare_ledger_writer(path)
    assert mutations == []


def test_cli_blocked_result_sanitizes_and_constructs_no_clients(monkeypatch, capsys):
    import sys

    import scripts.publish_preflight_budget as module

    monkeypatch.setattr(sys, "argv", ["publish", "--ledger", "unused.sqlite"])
    monkeypatch.setattr(
        module,
        "read_protected_config",
        lambda _: (_ for _ in ()).throw(RuntimeError("SECRET detail")),
    )
    monkeypatch.setattr(boto3, "Session", lambda **kwargs: pytest.fail("No clients allowed"))
    assert module.main() == 2
    output = capsys.readouterr().out
    assert '"status":"BLOCKED"' in output
    assert "SECRET" not in output


def test_ledger_writer_uses_existing_runtime_identity_and_drops_groups(monkeypatch):
    import stat
    import sys
    from pathlib import Path
    from types import SimpleNamespace

    import scripts.publish_preflight_budget as module

    events = []
    monkeypatch.setattr(
        module,
        "os",
        SimpleNamespace(
            name="posix",
            geteuid=lambda: 0,
            setgroups=lambda value: events.append(("groups", value)),
            setgid=lambda value: events.append(("gid", value)),
            setuid=lambda value: events.append(("uid", value)),
        ),
    )
    monkeypatch.setitem(
        sys.modules,
        "pwd",
        SimpleNamespace(getpwnam=lambda _: SimpleNamespace(pw_uid=9001, pw_gid=9002)),
    )
    path = Path("/var/lib/preflight/budget.sqlite").absolute()
    monkeypatch.setattr(
        Path,
        "lstat",
        lambda target: SimpleNamespace(
            st_uid=9001 if target == path else 0,
            st_mode=(stat.S_IFREG | 0o600) if target == path else (stat.S_IFDIR | 0o755),
        ),
    )
    module.prepare_ledger_writer(path)
    assert events == [("groups", []), ("gid", 9002), ("uid", 9001)]


def test_short_billing_window_is_not_invented_as_zero(config, clients, tmp_path):
    config["continuation_start"] = "2026-09-26T00:00:00Z"
    ce, sts, _, _ = clients
    with pytest.raises(PreflightError, match="BUDGET_COST_WINDOW_UNAVAILABLE"):
        publish(config, ce, sts, tmp_path / "absent.sqlite", now=NOW)
    assert not (tmp_path / "absent.sqlite").exists()
