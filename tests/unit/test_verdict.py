from preflight.models import CheckResult, CoverageEntry
from preflight.verdict import evaluate, invariant_requirements


def test_missing_is_warn_failed_is_block_only_complete_pass():
    reqs = invariant_requirements()
    checks = [CheckResult(id=r.id, category="invariant", status="pass") for r in reqs]
    assert evaluate(checks, reqs, "committed", []) == "PASS"
    assert evaluate(checks[:-1], reqs, "committed", []) == "WARN"
    assert evaluate(checks, reqs, "unknown", []) == "WARN"
    assert evaluate(checks, reqs, "rolled_back", []) == "BLOCK"
    coverage = [CoverageEntry(table="public.customers", column="email", operation="update",
                              rule="missing", complete=False, reason_code="COVERAGE_INCOMPLETE")]
    assert evaluate(checks, reqs, "committed", coverage) == "WARN"
    checks[0] = checks[0].model_copy(update={"status": "fail"})
    assert evaluate(checks, reqs, "committed", coverage) == "BLOCK"


def test_duplicate_manifest_and_results_warn():
    reqs = invariant_requirements()
    checks = [CheckResult(id=r.id, category="invariant", status="pass") for r in reqs]
    assert evaluate(checks + [checks[0]], reqs, "committed", []) == "WARN"
    assert evaluate(checks, reqs + [reqs[0]], "committed", []) == "WARN"
