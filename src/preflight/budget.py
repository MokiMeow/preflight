"""Pure USD admission arithmetic; no AWS clients, pricing table or hard-cap claim.

All costs refer to the same operator-authorized continuation window and scope.
The caller must establish complete observed spend plus an upper bound for usage
not yet billed, all outstanding reservations and future retained-resource costs.
Missing Cost Explorer data or free-tier credits cannot establish zero spend.
Rates must come from verified current primary pricing for the actual resources;
this module cannot verify a rate, discovery completeness or a retention bound.

Admission is NOT a reservation or an AWS spending limit. The integrating owner
must atomically persist a reservation under its shared mutation lock before any
billable call, reconcile uncertain calls without releasing funds, and refresh
accrual. Existing resources continue billing; automatic cleanup would still need
its separate authorization/recovery guards. Unknown retention therefore refuses
new work. Budget alerts and estimated billing do not guarantee an instant stop.

Primary billing references (rates themselves remain caller observations):
https://docs.aws.amazon.com/cost-management/latest/userguide/budgets-managing-costs.html
https://docs.aws.amazon.com/cost-management/latest/userguide/ce-what-is.html
https://aws.amazon.com/rds/postgresql/pricing/
"""

from dataclasses import dataclass
from datetime import datetime
from decimal import ROUND_CEILING, ROUND_FLOOR, Decimal, DecimalException, localcontext
from typing import Literal

from .models import PreflightError

CENT = Decimal("0.01")


def _known_amount(value: object) -> bool:
    return isinstance(value, Decimal) and value.is_finite() and value >= 0


def accrue_usd(
    hourly_rate_usd: Decimal,
    elapsed_seconds: int,
    *,
    minimum_seconds: int,
) -> Decimal:
    """Conservative cents for one caller-verified rate and billing minimum.

    No minimum is assumed: e.g. RDS PostgreSQL currently requires600 seconds for
    instance compute. Storage, requests, traffic, burst credits, taxes and retained
    snapshots need their own verified bounds; compute alone is not a total quote.
    """
    if (
        not _known_amount(hourly_rate_usd)
        or type(elapsed_seconds) is not int
        or type(minimum_seconds) is not int
        or elapsed_seconds < 0
        or minimum_seconds < 0
    ):
        raise PreflightError("BUDGET_RATE_OR_DURATION_INVALID")
    try:
        with localcontext() as context:
            context.prec = 50
            context.rounding = ROUND_CEILING
            # Zero elapsed can still incur a provider's billable startup minimum.
            seconds = max(elapsed_seconds, minimum_seconds)
            return (hourly_rate_usd * Decimal(seconds) / Decimal(3600)).quantize(
                CENT, rounding=ROUND_CEILING
            )
    except (DecimalException, OverflowError):
        raise PreflightError("BUDGET_RATE_OR_DURATION_INVALID") from None


@dataclass(frozen=True)
class BudgetSnapshot:
    ceiling_usd: Decimal | None
    spent_usd: Decimal | None
    accrual_upper_bound_usd: Decimal | None
    reserved_usd: Decimal | None
    safety_reserve_usd: Decimal | None
    observed_at: datetime | None
    scope_complete: bool = False
    ongoing_costs_bounded: bool = False
    currency: str = "USD"


@dataclass(frozen=True)
class BudgetDecision:
    admitted: bool
    reason_code: str
    max_authorized_ceiling_usd: Decimal | None
    accounted_usd: Decimal | None = None
    projected_usd: Decimal | None = None
    remaining_usd: Decimal | None = None
    native_hard_cap_enforced: Literal[False] = False


def admit(
    snapshot: BudgetSnapshot,
    proposed_max_usd: Decimal | None,
    *,
    now: datetime,
    max_age_seconds: int,
    max_authorized_ceiling_usd: Decimal = Decimal("100"),
) -> BudgetDecision:
    """Refuse unknown/stale/incomplete/unbounded costs or projected overspend.

    The default maximum is this operator's100 USD continuation authorization.
    A different explicit maximum is a caller-provided authorization, never inferred
    from a configured ceiling, remaining credits or free-tier account status.
    reserved_usd must include bounded future costs of existing retained resources;
    proposed_max_usd must include every incremental billable component. Overlap is
    conservative; omitting unbilled usage or releasing an uncertain reservation is
    unsafe. observed_at is freshness of the complete combined observation, not a
    claim that a recently requested billing API response covers current usage.
    """
    authorized = max_authorized_ceiling_usd if _known_amount(max_authorized_ceiling_usd) else None

    def refuse(code: str) -> BudgetDecision:
        return BudgetDecision(False, code, authorized)

    if authorized is None or authorized == 0:
        return refuse("BUDGET_AUTHORIZATION_INVALID")
    if not _known_amount(snapshot.ceiling_usd) or snapshot.ceiling_usd == 0:
        return refuse("BUDGET_CEILING_UNKNOWN")
    assert snapshot.ceiling_usd is not None
    if snapshot.ceiling_usd > authorized:
        return refuse("BUDGET_CEILING_NOT_AUTHORIZED")
    amounts = (
        snapshot.spent_usd,
        snapshot.accrual_upper_bound_usd,
        snapshot.reserved_usd,
        snapshot.safety_reserve_usd,
        proposed_max_usd,
    )
    if not all(_known_amount(amount) for amount in amounts):
        return refuse("BUDGET_COST_UNKNOWN")
    if snapshot.currency != "USD" or snapshot.scope_complete is not True:
        return refuse("BUDGET_SCOPE_INCOMPLETE")
    if snapshot.ongoing_costs_bounded is not True:
        return refuse("BUDGET_ONGOING_COST_UNBOUNDED")
    observed = snapshot.observed_at
    if (
        not isinstance(now, datetime)
        or now.utcoffset() is None
        or not isinstance(observed, datetime)
        or observed.utcoffset() is None
        or type(max_age_seconds) is not int
        or max_age_seconds <= 0
    ):
        return refuse("BUDGET_OBSERVATION_INVALID")
    age = (now - observed).total_seconds()
    if age < 0 or age > max_age_seconds:
        return refuse("BUDGET_OBSERVATION_STALE")
    try:
        with localcontext() as context:
            context.prec = 50
            context.rounding = ROUND_CEILING
            known = [
                amount.quantize(CENT, rounding=ROUND_CEILING)
                for amount in amounts
                if isinstance(amount, Decimal)
            ]
            accounted = sum(known[:-1], Decimal(0))
            projected = accounted + known[-1]
            remaining = (snapshot.ceiling_usd - projected).quantize(CENT, rounding=ROUND_FLOOR)
    except (DecimalException, OverflowError):
        return refuse("BUDGET_COST_UNKNOWN")
    admitted = projected <= snapshot.ceiling_usd
    return BudgetDecision(
        admitted,
        "BUDGET_ADMITTED" if admitted else "BUDGET_EXCEEDED",
        authorized,
        accounted,
        projected,
        remaining,
    )
