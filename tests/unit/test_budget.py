"""Synthetic arithmetic fixtures only: no claimed AWS prices/spend or clients."""

from dataclasses import FrozenInstanceError, replace
from datetime import UTC, datetime, timedelta, timezone
from decimal import Decimal, localcontext

import pytest

from preflight.budget import BudgetSnapshot, accrue_usd, admit
from preflight.models import PreflightError

NOW = datetime(2026, 9, 26, 12, tzinfo=UTC)


def known():
    # Synthetic costs; they are deliberately not estimates of this AWS account.
    return BudgetSnapshot(
        Decimal("100"),
        Decimal("10"),
        Decimal("15"),
        Decimal("60"),
        Decimal("10"),
        NOW,
        scope_complete=True,
        ongoing_costs_bounded=True,
    )


def decide(snapshot=None, proposed=Decimal("5"), **kwargs):
    return admit(snapshot or known(), proposed, now=NOW, max_age_seconds=60, **kwargs)


def test_exact_ceiling_includes_spent_unbilled_existing_reservations_and_safety_funds():
    decision = decide()
    assert decision.admitted and decision.reason_code == "BUDGET_ADMITTED"
    assert decision.accounted_usd == Decimal("95")
    assert decision.projected_usd == Decimal("100")
    assert decision.remaining_usd == Decimal("0")
    assert decision.max_authorized_ceiling_usd == Decimal("100")
    assert decision.native_hard_cap_enforced is False
    assert not decide(proposed=Decimal("5.000000001")).admitted


def test_subcent_costs_round_up_and_never_disappear_at_limit():
    snapshot = replace(
        known(),
        spent_usd=Decimal("99.99"),
        accrual_upper_bound_usd=Decimal("0.000001"),
        reserved_usd=Decimal(0),
        safety_reserve_usd=Decimal(0),
    )
    decision = decide(snapshot, Decimal("0.000001"))
    assert decision.reason_code == "BUDGET_EXCEEDED"
    assert decision.projected_usd == Decimal("100.01")
    assert decision.remaining_usd == Decimal("-0.01")


@pytest.mark.parametrize(
    "component", ["spent_usd", "accrual_upper_bound_usd", "reserved_usd", "safety_reserve_usd"]
)
@pytest.mark.parametrize(
    "missing", [None, Decimal("NaN"), Decimal("Infinity"), Decimal("-1"), 0.0, "0", False]
)
def test_unknown_or_nondecimal_component_refuses_without_fabricating_totals(component, missing):
    decision = decide(replace(known(), **{component: missing}))
    assert not decision.admitted and decision.reason_code == "BUDGET_COST_UNKNOWN"
    assert decision.projected_usd is decision.accounted_usd is decision.remaining_usd is None


@pytest.mark.parametrize("proposal", [None, Decimal("NaN"), Decimal("-0.01"), 0, 0.0, True])
def test_unknown_proposed_maximum_refuses(proposal):
    assert decide(proposed=proposal).reason_code == "BUDGET_COST_UNKNOWN"


@pytest.mark.parametrize("ceiling", [None, Decimal(0), Decimal("NaN"), Decimal("-1"), 100.0])
def test_missing_ceiling_is_not_authorization(ceiling):
    assert decide(replace(known(), ceiling_usd=ceiling)).reason_code == "BUDGET_CEILING_UNKNOWN"


def test_configured_ceiling_cannot_expand_operator_authorization():
    assert (
        decide(replace(known(), ceiling_usd=Decimal("100.01"))).reason_code
        == "BUDGET_CEILING_NOT_AUTHORIZED"
    )
    assert (
        decide(max_authorized_ceiling_usd=Decimal("90")).reason_code
        == "BUDGET_CEILING_NOT_AUTHORIZED"
    )
    decision = decide(
        replace(known(), ceiling_usd=Decimal("90")), max_authorized_ceiling_usd=Decimal("90")
    )
    assert not decision.admitted and decision.max_authorized_ceiling_usd == Decimal("90")


@pytest.mark.parametrize(
    "authorized", [Decimal(0), Decimal("NaN"), Decimal("Infinity"), Decimal("-1"), 100.0, None]
)
def test_invalid_operator_authorization_refused(authorized):
    assert (
        decide(max_authorized_ceiling_usd=authorized).reason_code == "BUDGET_AUTHORIZATION_INVALID"
    )


@pytest.mark.parametrize(
    "changes,reason",
    [
        ({"scope_complete": False}, "BUDGET_SCOPE_INCOMPLETE"),
        ({"scope_complete": 1}, "BUDGET_SCOPE_INCOMPLETE"),
        ({"currency": "EUR"}, "BUDGET_SCOPE_INCOMPLETE"),
        ({"ongoing_costs_bounded": False}, "BUDGET_ONGOING_COST_UNBOUNDED"),
        ({"ongoing_costs_bounded": 1}, "BUDGET_ONGOING_COST_UNBOUNDED"),
        ({"observed_at": None}, "BUDGET_OBSERVATION_INVALID"),
        ({"observed_at": NOW.replace(tzinfo=None)}, "BUDGET_OBSERVATION_INVALID"),
        ({"observed_at": NOW - timedelta(seconds=61)}, "BUDGET_OBSERVATION_STALE"),
        ({"observed_at": NOW + timedelta(microseconds=1)}, "BUDGET_OBSERVATION_STALE"),
    ],
)
def test_incomplete_inventory_delayed_observation_or_unbounded_retention_refuses(changes, reason):
    assert decide(replace(known(), **changes)).reason_code == reason


def test_zero_billing_figure_is_not_complete_current_spend_observation():
    # Even a just-requested response cannot fill missing unbilled charges/retention.
    snapshot = replace(known(), spent_usd=Decimal(0), accrual_upper_bound_usd=None)
    assert decide(snapshot).reason_code == "BUDGET_COST_UNKNOWN"


def test_equal_offset_observations_and_freshness_boundary():
    offset = NOW.astimezone(timezone(timedelta(hours=5, minutes=30))) - timedelta(seconds=60)
    assert decide(replace(known(), observed_at=offset)).admitted
    assert known().spent_usd == Decimal("10")  # admission does not mutate accounting
    with pytest.raises(FrozenInstanceError):
        known().reserved_usd = Decimal(0)


def test_billing_minimum_and_upward_rounding_use_only_supplied_synthetic_rate():
    assert accrue_usd(Decimal("6"), 1, minimum_seconds=600) == Decimal("1")
    assert accrue_usd(Decimal("6"), 0, minimum_seconds=600) == Decimal("1")
    assert accrue_usd(Decimal("6"), 601, minimum_seconds=600) == Decimal("1.01")
    assert accrue_usd(Decimal("0.01"), 1, minimum_seconds=0) == Decimal("0.01")
    assert accrue_usd(Decimal("6"), 0, minimum_seconds=0) == Decimal(0)


@pytest.mark.parametrize(
    "rate,seconds,minimum",
    [
        (None, 10, 0),
        (Decimal("NaN"), 10, 0),
        (Decimal("Infinity"), 10, 0),
        (Decimal("-1"), 10, 0),
        (6.0, 10, 0),
        (Decimal(6), -1, 0),
        (Decimal(6), 1.0, 0),
        (Decimal(6), True, 0),
        (Decimal(6), 1, -1),
        (Decimal(6), 1, False),
        (Decimal("1e1000000"), 1, 0),
    ],
)
def test_invalid_rate_or_duration_has_safe_failure(rate, seconds, minimum):
    with pytest.raises(PreflightError, match="BUDGET_RATE_OR_DURATION_INVALID"):
        accrue_usd(rate, seconds, minimum_seconds=minimum)


def test_callers_decimal_context_cannot_round_spending_down():
    with localcontext() as context:
        context.prec = 2
        decision = decide(proposed=Decimal("5.001"))
        assert decision.reason_code == "BUDGET_EXCEEDED"
        assert decision.projected_usd == Decimal("100.01")
        assert accrue_usd(Decimal(6), 601, minimum_seconds=600) == Decimal("1.01")


def test_unknown_usage_is_not_replaced_with_credits_or_a_network_query(monkeypatch):
    import socket

    monkeypatch.setattr(socket, "socket", lambda *a, **k: pytest.fail("pure budget network call"))
    unknown = replace(known(), spent_usd=None, accrual_upper_bound_usd=None)
    assert decide(unknown).reason_code == "BUDGET_COST_UNKNOWN"
