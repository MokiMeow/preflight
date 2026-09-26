"""USD admission arithmetic and durable ledger; no AWS clients or hard-cap claim.

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

import re
import sqlite3
from collections.abc import Mapping
from contextlib import contextmanager
from dataclasses import dataclass, replace
from datetime import datetime
from decimal import ROUND_CEILING, ROUND_FLOOR, Decimal, DecimalException, localcontext
from pathlib import Path
from typing import Literal

from .artifacts import canonical_json, strict_json
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

    The default maximum is a conservative100 USD bounded-workflow allowance.
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


class BudgetLedger:
    """Trusted server bookkeeping with durable, never auto-released reservations.

    This is not a model tool, configuration parser, billing fetcher, credit
    calculator or native AWS hard cap. Only a trusted owner may publish verified
    complete observations/quotes. Missing facts remain missing. Provenance must
    be nonsecret; this API does not accept credentials or evaluate their contents.
    The observation's reserved_usd is the baseline future-resource allowance;
    ALL ledger reservations are added conservatively, even after later billing
    observations include their cost. Unknown create outcomes do not free funds.
    """

    def __init__(self, path: str | Path, ceiling: Decimal = Decimal("100")):
        if not _known_amount(ceiling) or ceiling == 0:
            raise PreflightError("BUDGET_AUTHORIZATION_INVALID")
        self.path = Path(path).resolve()
        self._ceiling = ceiling
        self.path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        with self._transaction() as connection:
            connection.execute(
                "CREATE TABLE IF NOT EXISTS budget_metadata (key TEXT PRIMARY KEY,value TEXT NOT NULL)"
            )
            connection.execute(
                "CREATE TABLE IF NOT EXISTS budget_observation (id INTEGER PRIMARY KEY CHECK(id=1),snapshot BLOB NOT NULL,quotes BLOB NOT NULL,provenance TEXT NOT NULL)"
            )
            connection.execute(
                "CREATE TABLE IF NOT EXISTS budget_reservations (key TEXT PRIMARY KEY,kind TEXT NOT NULL,amount TEXT NOT NULL,created_at TEXT NOT NULL)"
            )
            previous = connection.execute(
                "SELECT value FROM budget_metadata WHERE key='ceiling_usd'"
            ).fetchone()
            if previous is None:
                connection.execute(
                    "INSERT INTO budget_metadata VALUES('ceiling_usd',?)", (str(ceiling),)
                )
            elif Decimal(previous[0]) != ceiling:
                raise PreflightError("BUDGET_CEILING_MISMATCH")

    @property
    def ceiling(self) -> Decimal:
        return self._ceiling

    def _assert_ceiling(self, connection) -> None:
        stored = connection.execute(
            "SELECT value FROM budget_metadata WHERE key='ceiling_usd'"
        ).fetchone()
        if stored is None or Decimal(stored[0]) != self.ceiling:
            raise PreflightError("BUDGET_CEILING_MISMATCH")

    @contextmanager
    def _transaction(self):
        connection = None
        try:
            connection = sqlite3.connect(self.path, timeout=5, isolation_level=None)
            connection.execute("PRAGMA journal_mode=WAL")
            connection.execute("PRAGMA synchronous=FULL")
            connection.execute("PRAGMA busy_timeout=5000")
            connection.execute("BEGIN IMMEDIATE")
            yield connection
            connection.commit()
        except PreflightError:
            raise
        except Exception:
            raise PreflightError("BUDGET_LEDGER_FAILED") from None
        finally:
            if connection is not None:
                connection.close()  # uncommitted SQLite transactions roll back

    def record_observation(
        self,
        snapshot: BudgetSnapshot,
        per_kind_quotes: Mapping[str, Decimal],
        provenance: str,
    ) -> None:
        """Publish trusted nonsecret facts; None costs persist as unknown.

        No environment/CLI/model input path exists here. Calling this method is
        not evidence that observations or provider prices were actually verified.
        The caller owns the continuation window, resource inventory and provenance.
        """
        if snapshot.ceiling_usd != self.ceiling:
            raise PreflightError("BUDGET_CEILING_MISMATCH")
        if not isinstance(provenance, str) or not provenance.strip() or len(provenance) > 4096:
            raise PreflightError("BUDGET_PROVENANCE_INVALID")
        quotes = {}
        for kind, amount in per_kind_quotes.items():
            if (
                not isinstance(kind, str)
                or not re.fullmatch(r"[a-z][a-z0-9_]{0,63}", kind)
                or not _known_amount(amount)
            ):
                raise PreflightError("BUDGET_QUOTE_INVALID")
            quotes[kind] = str(amount)
        data = dict(snapshot.__dict__)
        for field in (
            "ceiling_usd",
            "spent_usd",
            "accrual_upper_bound_usd",
            "reserved_usd",
            "safety_reserve_usd",
        ):
            value = data[field]
            if value is not None and not isinstance(value, Decimal):
                raise PreflightError("BUDGET_OBSERVATION_INVALID")
            data[field] = str(value) if value is not None else None
        if snapshot.observed_at is not None and not isinstance(snapshot.observed_at, datetime):
            raise PreflightError("BUDGET_OBSERVATION_INVALID")
        data["observed_at"] = snapshot.observed_at.isoformat() if snapshot.observed_at else None
        with self._transaction() as connection:
            self._assert_ceiling(connection)
            connection.execute(
                "INSERT INTO budget_observation VALUES(1,?,?,?) ON CONFLICT(id) DO UPDATE SET snapshot=excluded.snapshot,quotes=excluded.quotes,provenance=excluded.provenance",
                (canonical_json(data), canonical_json(quotes), provenance),
            )

    @staticmethod
    def _total(connection) -> Decimal:
        with localcontext() as context:
            context.prec = 50
            context.rounding = ROUND_CEILING
            amounts = [
                Decimal(row[0])
                for row in connection.execute("SELECT amount FROM budget_reservations")
            ]
            if not all(_known_amount(amount) for amount in amounts):
                raise PreflightError("BUDGET_LEDGER_FAILED")
            return sum(amounts, Decimal(0))

    def total_reserved_usd(self) -> Decimal:
        with self._transaction() as connection:
            return self._total(connection)

    def authorize(
        self,
        reservation_key: str,
        kind: str,
        now: datetime,
        max_age_seconds: int = 300,
    ) -> BudgetDecision:
        """Atomically check fresh facts and persist funds before a billable intent.

        Keys identify exact billable intents; snapshot/clone/recovery are distinct.
        An existing key is not permission to skip freshness/ceiling guards. A
        current quote larger than its existing reservation refuses instead of
        adding funds or reusing an insufficient bound. There is no release method.
        """

        def refuse(code: str) -> BudgetDecision:
            return BudgetDecision(False, code, self.ceiling)

        if (
            not isinstance(reservation_key, str)
            or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.:/-]{0,255}", reservation_key)
            or not isinstance(kind, str)
            or not re.fullmatch(r"[a-z][a-z0-9_]{0,63}", kind)
        ):
            return refuse("BUDGET_RESERVATION_ID_INVALID")
        with self._transaction() as connection:
            self._assert_ceiling(connection)
            row = connection.execute(
                "SELECT snapshot,quotes FROM budget_observation WHERE id=1"
            ).fetchone()
            if row is None:
                return refuse("BUDGET_OBSERVATION_UNKNOWN")
            data = strict_json(bytes(row[0]))
            for field in (
                "ceiling_usd",
                "spent_usd",
                "accrual_upper_bound_usd",
                "reserved_usd",
                "safety_reserve_usd",
            ):
                data[field] = Decimal(data[field]) if data[field] is not None else None
            data["observed_at"] = (
                datetime.fromisoformat(data["observed_at"]) if data["observed_at"] else None
            )
            snapshot = BudgetSnapshot(**data)
            if snapshot.ceiling_usd != self.ceiling:
                return refuse("BUDGET_CEILING_MISMATCH")
            quotes = strict_json(bytes(row[1]))
            quote = Decimal(quotes[kind]) if kind in quotes else None
            if not _known_amount(quote):
                return refuse("BUDGET_QUOTE_UNKNOWN")
            assert quote is not None
            existing = connection.execute(
                "SELECT kind,amount FROM budget_reservations WHERE key=?", (reservation_key,)
            ).fetchone()
            if existing and existing[0] != kind:
                return refuse("BUDGET_RESERVATION_KEY_CONFLICT")
            if existing and quote > Decimal(existing[1]):
                return refuse("BUDGET_RESERVATION_BOUND_CHANGED")
            with localcontext() as context:
                context.prec = 50
                context.rounding = ROUND_CEILING
                reserved = (
                    snapshot.reserved_usd + self._total(connection)
                    if isinstance(snapshot.reserved_usd, Decimal)
                    and _known_amount(snapshot.reserved_usd)
                    else None
                )
            decision = admit(
                replace(snapshot, reserved_usd=reserved),
                Decimal(0) if existing else quote,
                now=now,
                max_age_seconds=max_age_seconds,
                max_authorized_ceiling_usd=self.ceiling,
            )
            if decision.admitted and not existing:
                with localcontext() as context:
                    context.prec = 50
                    amount = quote.quantize(CENT, rounding=ROUND_CEILING)
                connection.execute(
                    "INSERT INTO budget_reservations VALUES(?,?,?,?)",
                    (reservation_key, kind, str(amount), now.isoformat()),
                )
            return decision
