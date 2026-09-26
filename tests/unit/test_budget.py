"""Synthetic arithmetic fixtures only: no claimed AWS prices/spend or clients."""

from dataclasses import FrozenInstanceError, replace
from datetime import UTC, datetime, timedelta, timezone
from decimal import Decimal, localcontext

import pytest

from preflight.budget import BudgetLedger, BudgetSnapshot, accrue_usd, admit
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


def funded_ledger(path):
    ledger = BudgetLedger(path)
    ledger.record_observation(
        known(),
        {"snapshot": Decimal("5"), "clone": Decimal("5"), "recovery": Decimal("5")},
        "synthetic unit facts; not actual AWS cost/pricing",
    )
    return ledger


def test_ledger_no_observation_or_missing_quote_never_reserves(tmp_path):
    ledger = BudgetLedger(tmp_path / "budget.sqlite")
    assert (
        ledger.authorize("run:snapshot", "snapshot", NOW).reason_code
        == "BUDGET_OBSERVATION_UNKNOWN"
    )
    ledger.record_observation(known(), {}, "synthetic missing quote")
    assert ledger.authorize("run:snapshot", "snapshot", NOW).reason_code == "BUDGET_QUOTE_UNKNOWN"
    assert ledger.total_reserved_usd() == 0


def test_ledger_reserves_before_return_and_preserves_same_key_across_restart(tmp_path):
    path = tmp_path / "budget.sqlite"
    ledger = funded_ledger(path)
    first = ledger.authorize("run:snapshot", "snapshot", NOW)
    assert first.admitted and first.projected_usd == Decimal(100)
    restarted = BudgetLedger(path)
    assert restarted.total_reserved_usd() == Decimal(5)
    assert restarted.authorize("run:snapshot", "snapshot", NOW).admitted
    assert restarted.total_reserved_usd() == Decimal(5)
    assert restarted.authorize("run:clone", "clone", NOW).reason_code == "BUDGET_EXCEEDED"
    assert restarted.authorize("run:recovery", "recovery", NOW).reason_code == "BUDGET_EXCEEDED"


def test_ledger_baseline_future_reserve_plus_ledger_sum_not_overwritten(tmp_path):
    ledger = funded_ledger(tmp_path / "budget.sqlite")
    assert ledger.authorize("snapshot", "snapshot", NOW).admitted
    ledger.record_observation(
        replace(known(), spent_usd=Decimal("15")),
        {"snapshot": Decimal(5)},
        "synthetic billed later; outstanding reservation retained conservatively",
    )
    refusal = ledger.authorize("snapshot", "snapshot", NOW)
    assert refusal.reason_code == "BUDGET_EXCEEDED"
    assert refusal.accounted_usd == Decimal(105)
    assert ledger.total_reserved_usd() == Decimal(5)


@pytest.mark.parametrize(
    "changes,reason",
    [
        ({"spent_usd": None}, "BUDGET_COST_UNKNOWN"),
        ({"accrual_upper_bound_usd": None}, "BUDGET_COST_UNKNOWN"),
        ({"scope_complete": False}, "BUDGET_SCOPE_INCOMPLETE"),
        ({"ongoing_costs_bounded": False}, "BUDGET_ONGOING_COST_UNBOUNDED"),
        ({"observed_at": NOW - timedelta(seconds=301)}, "BUDGET_OBSERVATION_STALE"),
    ],
)
def test_ledger_even_existing_key_requires_current_complete_cost_facts(tmp_path, changes, reason):
    ledger = funded_ledger(tmp_path / "budget.sqlite")
    assert ledger.authorize("snapshot", "snapshot", NOW).admitted
    ledger.record_observation(
        replace(known(), **changes), {"snapshot": Decimal(5)}, "synthetic invalidated observation"
    )
    assert ledger.authorize("snapshot", "snapshot", NOW).reason_code == reason
    assert ledger.authorize("additional", "snapshot", NOW).reason_code == reason
    assert ledger.total_reserved_usd() == Decimal(5)


def test_ledger_quote_changes_cannot_reuse_or_silently_expand_old_reservation(tmp_path):
    ledger = funded_ledger(tmp_path / "budget.sqlite")
    assert ledger.authorize("shared-key", "snapshot", NOW).admitted
    assert (
        ledger.authorize("shared-key", "clone", NOW).reason_code
        == "BUDGET_RESERVATION_KEY_CONFLICT"
    )
    ledger.record_observation(known(), {"snapshot": Decimal(6)}, "synthetic larger maximum")
    assert (
        ledger.authorize("shared-key", "snapshot", NOW).reason_code
        == "BUDGET_RESERVATION_BOUND_CHANGED"
    )
    ledger.record_observation(
        known(), {"snapshot": Decimal(1)}, "synthetic smaller maximum; no refund"
    )
    assert ledger.authorize("shared-key", "snapshot", NOW).admitted
    ledger.record_observation(known(), {}, "synthetic now unknown quote")
    assert ledger.authorize("shared-key", "snapshot", NOW).reason_code == "BUDGET_QUOTE_UNKNOWN"
    assert ledger.total_reserved_usd() == Decimal(5)


def test_ledger_persisted_ceiling_cannot_be_changed_or_exceed_authorization(tmp_path):
    path = tmp_path / "budget.sqlite"
    ledger = funded_ledger(path)
    assert ledger.authorize("snapshot", "snapshot", NOW).admitted
    with pytest.raises(PreflightError, match="BUDGET_CEILING_MISMATCH"):
        BudgetLedger(path, Decimal(90))
    with pytest.raises(PreflightError, match="BUDGET_AUTHORIZATION_INVALID"):
        BudgetLedger(path, Decimal("100.01"))
    with pytest.raises(PreflightError, match="BUDGET_CEILING_MISMATCH"):
        ledger.record_observation(
            replace(known(), ceiling_usd=Decimal(101)),
            {"snapshot": Decimal(0)},
            "synthetic mismatched ceiling",
        )
    assert BudgetLedger(path).total_reserved_usd() == Decimal(5)


def test_ledger_live_handle_refuses_changed_persisted_ceiling(tmp_path):
    import sqlite3

    path = tmp_path / "budget.sqlite"
    ledger = funded_ledger(path)
    with pytest.raises(AttributeError):
        ledger.ceiling = Decimal(200)
    with sqlite3.connect(path) as connection:
        connection.execute("UPDATE budget_metadata SET value='50' WHERE key='ceiling_usd'")
    with pytest.raises(PreflightError, match="BUDGET_CEILING_MISMATCH"):
        ledger.authorize("snapshot", "snapshot", NOW)
    assert ledger.total_reserved_usd() == 0


@pytest.mark.parametrize(
    "key,kind",
    [
        (None, "snapshot"),
        ("", "snapshot"),
        ("run", ""),
        ("run", "snapshot;DELETE"),
        ("x" * 257, "snapshot"),
    ],
)
def test_ledger_invalid_identity_cannot_reserve(tmp_path, key, kind):
    ledger = funded_ledger(tmp_path / "budget.sqlite")
    assert ledger.authorize(key, kind, NOW).reason_code == "BUDGET_RESERVATION_ID_INVALID"
    assert ledger.total_reserved_usd() == 0


def test_ledger_storage_failure_never_echoes_private_path(tmp_path):
    path = tmp_path / "PRIVATE_PATH_SENTINEL.sqlite"
    path.write_bytes(b"not a SQLite database")
    with pytest.raises(PreflightError, match="BUDGET_LEDGER_FAILED") as error:
        BudgetLedger(path)
    assert "PRIVATE_PATH_SENTINEL" not in str(error.value)


def test_ledger_unknown_cost_observation_survives_restart(tmp_path):
    path = tmp_path / "budget.sqlite"
    ledger = funded_ledger(path)
    ledger.record_observation(
        replace(known(), spent_usd=None), {"snapshot": Decimal(5)}, "synthetic missing billing data"
    )
    restarted = BudgetLedger(path)
    assert restarted.authorize("snapshot", "snapshot", NOW).reason_code == "BUDGET_COST_UNKNOWN"
    assert restarted.total_reserved_usd() == 0


@pytest.mark.parametrize("quote", [None, "5", 5.0, Decimal("NaN"), Decimal("-1")])
def test_ledger_invalid_quote_publication_has_safe_failure(tmp_path, quote):
    ledger = BudgetLedger(tmp_path / "budget.sqlite")
    with pytest.raises(PreflightError, match="BUDGET_QUOTE_INVALID"):
        ledger.record_observation(known(), {"snapshot": quote}, "synthetic invalid quote")
    assert ledger.authorize("snapshot", "snapshot", NOW).reason_code == "BUDGET_OBSERVATION_UNKNOWN"


def test_two_ledger_instances_cannot_both_reserve_last_headroom(tmp_path):
    import threading
    from concurrent.futures import ThreadPoolExecutor

    path = tmp_path / "budget.sqlite"
    ledgers = [funded_ledger(path), BudgetLedger(path)]
    barrier = threading.Barrier(2)

    def reserve(index):
        barrier.wait(timeout=3)
        return ledgers[index].authorize(f"run:{index}", "snapshot", NOW)

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(reserve, range(2)))
    assert sum(result.admitted for result in results) == 1
    assert {result.reason_code for result in results} == {"BUDGET_ADMITTED", "BUDGET_EXCEEDED"}
    assert BudgetLedger(path).total_reserved_usd() == Decimal(5)


def process_reserve_budget(path, key, barrier, queue):
    ledger = BudgetLedger(path)
    barrier.wait(timeout=10)
    decision = ledger.authorize(key, "snapshot", NOW)
    queue.put((decision.admitted, decision.reason_code))


@pytest.mark.parametrize("same_key", [False, True])
def test_independent_processes_atomically_reserve_without_overspend_or_duplicate(
    tmp_path, same_key
):
    import multiprocessing

    path = tmp_path / "budget.sqlite"
    funded_ledger(path)
    context = multiprocessing.get_context("spawn")
    barrier, queue = context.Barrier(2), context.Queue()
    keys = ["same", "same"] if same_key else ["first", "second"]
    workers = [
        context.Process(target=process_reserve_budget, args=(path, key, barrier, queue))
        for key in keys
    ]
    try:
        for worker in workers:
            worker.start()
        results = [queue.get(timeout=15) for _ in workers]
        assert sum(result[0] for result in results) == (2 if same_key else 1)
        assert BudgetLedger(path).total_reserved_usd() == Decimal(5)
        for worker in workers:
            worker.join(timeout=5)
            assert worker.exitcode == 0
    finally:
        for worker in workers:
            if worker.is_alive():
                worker.terminate()
                worker.join(timeout=5)
        queue.close()
        queue.join_thread()
