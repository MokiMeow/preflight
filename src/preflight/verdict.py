"""Pure verdict oracle; completeness outranks a model's explanation."""

from .models import CheckResult, CoverageEntry, Requirement

INVARIANTS = (
    "exact_candidate_bytes",
    "policy_accepted",
    "clone_provenance",
    "baseline_present",
    "source_matched_baseline",
    "coverage_complete",
    "pk_set_unchanged",
    "preserved_values_unchanged",
    "schema_expected",
    "declared_checks_complete",
    "within_budgets",
)


def invariant_requirements() -> list[Requirement]:
    return [
        Requirement(id=f"invariant:{kind}", kind=kind, policy_role="invariant")
        for kind in INVARIANTS
    ]


def evaluate(
    checks: list[CheckResult],
    requirements: list[Requirement],
    outcome: str,
    coverage: list[CoverageEntry],
) -> str:
    if outcome == "rolled_back" or any(c.status == "fail" for c in checks):
        return "BLOCK"
    ids = [r.id for r in requirements]
    result_ids = [r.id for r in checks]
    complete = bool(ids) and len(set(ids)) == len(ids) and len(set(result_ids)) == len(result_ids)
    complete = complete and set(ids) == set(result_ids)
    mandatory = {f"invariant:{kind}" for kind in INVARIANTS}
    complete = complete and mandatory <= set(ids)
    if (
        outcome != "committed"
        or not complete
        or any(c.status != "pass" for c in checks)
        or any(not item.complete for item in coverage)
    ):
        return "WARN"
    return "PASS"
