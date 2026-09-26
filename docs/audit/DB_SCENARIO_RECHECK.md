# Database scenario assertion recheck

This packet rechecks the database-related `PARTIAL` entries in
[scenario-matrix.json](scenario-matrix.json) against the actual required assertions,
not the number of passing tests. The matrix's `221a79a` observations are stale for
the subsequent SQL/catalog deadline regressions. This supplement does not modify
the shared matrix or confer connected acceptance.

Checkout: `.worktrees/db`, branch `preflight/db-scenario-recheck`, base
`46a9eac836231cd28b493d37a1a1b44e075524e7`. Effective worker role remains GPT-6
Sol/high; no grandchildren or premium promotion. Owned changes are this document
and the two new test files below. No application code, shared schema, lockfile,
source configuration, AWS resources, credential or approval gate was changed.
The retained PostgreSQL18 cluster was already running on loopback port55438;
the lead released its exclusive lane before these tests. This worker neither
started nor stopped it.

Authority: [docs02 sections6–7](../02_CONTRACTS_AND_SAFETY.md#7-source-apply-guard-and-outcome),
[docs02 section11](../02_CONTRACTS_AND_SAFETY.md#11-v3-column-level-coverage-and-impact-summary),
[docs06 P/D/A/V assertions](../06_TEST_AND_EVIDENCE.md), and the
[preflight-db skill](../../.agents/skills/preflight-db/SKILL.md). The original PRD
and contract format remain unchanged. The prior whole-function accounting is in
[FILE_FUNCTION_INVENTORY.md](FILE_FUNCTION_INVENTORY.md); this packet examines
assertion gaps rather than treating that static inventory as execution proof.

## Exact proof names

The tables use these file aliases. A function name following an alias is its exact
pytest node before the parameter suffix; every parameter listed in that function
was exercised by the commands below.

| Alias | File |
|---|---|
| S | `tests/unit/test_sql_policy.py` |
| RS | `tests/unit/test_remaining_sql_boundaries.py` |
| E | `tests/unit/test_evidence.py` |
| RV | `tests/unit/test_remaining_verdict_boundaries.py` |
| DB | `tests/postgres/test_database.py` |
| RC | `tests/postgres/test_remaining_catalog_boundaries.py` |
| RT | `tests/postgres/test_remaining_transaction_boundaries.py` |
| SV | `tests/postgres/test_service.py` |
| SC | `tests/postgres/test_source_concurrency.py` |
| CL | `tests/cloud/test_rds.py` |

## PARTIAL entries now ready for LOCAL_VERIFIED

These statuses describe local parser, deterministic oracle, actual disposable
PostgreSQL, or inert botocore Stubber observations. They never describe real RDS
restore, provider execution, human approval or source eligibility. Combining an
adapter guard test and a service refusal test proves their local composition;
it does not claim either was exercised against AWS.

| ID | Required assertion and exact proof |
|---|---|
| P03 | Reject BEGIN/COMMIT/ROLLBACK and psql commands. S::`test_recursive_rejection` exercises all three; RS::`test_p03_through_p08_unsupported_candidate_is_rejected` exercises backslash include/copy, SAVEPOINT and SET TRANSACTION. |
| P04 | Reject DO/CALL/COPY/SELECT/DELETE/INSERT/TRUNCATE/GRANT/CREATE/DROP. S::`test_recursive_rejection` plus RS::`test_p03_through_p08_unsupported_candidate_is_rejected` cover all except ordinary CREATE TABLE; new RV::`test_p04_create_table_statement_is_rejected_without_a_plan` closes that distinct AST variant. |
| P05 | Reject concurrent index creation and unsupported ALTER. S::`test_recursive_rejection` covers concurrent index/drop/default/conditional add; RS::`test_p03_through_p08_unsupported_candidate_is_rejected` covers trigger enable and rename. |
| P06 | Recursively reject UPDATE CTE/FROM/RETURNING/subquery/function. S::`test_recursive_rejection` asserts every named clause; RS's negative cases additionally cover CASE, EXISTS, IN, LIKE, array and collation branches. |
| P07 | Reject default/generated/identity and custom cast/operator/type surfaces. S::`test_recursive_rejection` covers DEFAULT, casts and qualified custom operator; RS::`test_p03_through_p08_unsupported_candidate_is_rejected` and `test_p07_custom_builtin_lookalike_does_not_expand_grammar` cover generated/identity/custom lookalike/array types. |
| P08 | Reject wrong schema/table, unqualified targets, unknown columns and PK mutation. S::`test_recursive_rejection`, S::`test_unknown_metadata_column`, RS::`test_p08_unknown_target_read_or_predicate_column_refused_at_metadata` cover all named clauses and distinguish write/read/predicate unknown columns. |
| P09 | Later forbidden statement rejects the whole candidate. S::`test_recursive_rejection` covers later COMMIT; RS::`test_p09_forbidden_later_statement_rejects_entire_candidate` covers later CALL/TRUNCATE/DROP. No executable plan is returned. Registration requires accepted inspection before publishing a candidate or requesting any DB execution. |
| P11 | Refuse trigger/rule/event-trigger/RLS/FK-cascade/partition/inheritance capabilities. DB::`test_trigger_and_inheritance_rejected`, DB::`test_semantic_unsafe_objects`, RC::`test_p11_p12_unsupported_catalog_capability_never_returns_evidence`, RC::`test_p11_enabled_event_trigger_rejected_without_firing_it` cover all named families. Fresh capture uses read-only RR; catalog validation contains only queries and never disables unsupported objects. |
| P12 | Reject unsafe CHECK/exclusion/expression/partial-index/custom-collation execution surfaces. DB::`test_semantic_unsafe_objects`, RC::`test_p11_p12_unsupported_catalog_capability_never_returns_evidence`, RC::`test_p12_user_defined_operator_class_rejected` cover every named surface and custom opclass. |
| P14 | Parser/database major mismatch refuses migration. New RV::`test_p14_parser_mismatch_refused_before_parse_or_execution` covers wrong pglast version and wrong parser major with a forbidden parser-call spy. DB::`test_tls_hostname_ca_major_and_role` separately proves database-major refusal on actual PG. |
| D05 | Different retrieval/physical row order preserves canonical roots. New RT::`test_d05_real_physical_row_order_changes_without_changing_roots` proves the first physical row actually changes after descending-index CLUSTER, then requires identical full baseline. E::`test_domain_length_and_order` independently reverses map insertion order. |
| D09 | Missing table/PK/column/inaccessible metadata produces specific failure, never zero evidence. RC::`test_d09_missing_table_primary_key_or_preserved_column_is_specific`, `test_d09_inaccessible_catalog_does_not_fabricate_metadata`, `test_d09_inaccessible_rows_do_not_become_zero_count`, `test_d09_missing_full_baseline_column_is_not_silently_omitted`; no EvidenceBundle is returned. |
| D10 | Row/byte/deadline overrun stops and cannot PASS. DB::`test_scan_budget_and_huge_cell`; RC::`test_d10_serialized_budget_excludes_escape_expansion_overrun`, `test_d10_whole_capture_deadline_includes_row_processing` (CPU/fetch delay, fresh/caller-owned transactions), `test_d10_whole_capture_deadline_includes_catalog_processing`, `test_d10_baseline_query_timeout_cannot_return_partial_evidence`. Fresh snapshots roll back; caller-owned transaction rollback remains caller responsibility. The deadline fix is already integrated in the base. |
| D15 | DB error containing private value yields safe tool/log/report classification. New RT::`test_d15_private_database_error_value_absent_from_tool_logs_and_reports` first proves actual PG NotNullViolation DETAIL contains the synthetic private sentinel, rolls back that independent diagnostic transaction, then exercises the service. Outcome retains only SQLSTATE23502; tool/baseline/public report JSON/Markdown/captured logs omit the sentinel. |
| D18 | Irrelevant OIDs do not change schema roots. New RT::`test_d18_independent_table_and_index_oids_do_not_change_normalized_roots` explicitly verifies different table and primary-index OIDs in independent databases, then identical normalized full baselines. Real snapshot-restored RDS remains separate connected proof. |
| D19 | Same-contract revision requires unchanged full baseline. SV::`test_bad_rollback_revision_good_pass_exact_report_and_disabled_source` proves accepted unchanged reuse; new RT::`test_d19_d20_revision_requires_private_maps_and_full_unchanged_baseline` proves unpreserved-value drift changes full hash while preserved hash remains equal, and refusal leaves current candidate unchanged. |
| D20 | Committed-invalid clone or lost maps requires fresh rehearsal. SV::`test_committed_wrong_data_blocks_and_revision_refused` proves committed-invalid refusal; RT::`test_d19_d20_revision_requires_private_maps_and_full_unchanged_baseline` proves direct RAM-map loss refusal without changing candidate attachment. |
| A02 | Wrong source/account/database or source=clone refuses. New RT::`test_a02_source_scope_refusal_precedes_writer` covers source/database/collision with zero writer and no durable apply intent. CL::`test_wrong_account_before_resource_call` supplies actual adapter identity rejection using inert Stubber. |
| A03 | Wrong migration/report hash or altered stored contract/report refuses without writing. New RT::`test_a03_approved_artifact_changes_refused_without_writer` covers both supplied digests, canonical contract file, stored contract record, and report file independently; specific error, zero source writer, no apply intent. |
| A04 | Noncurrent candidate, WARN/BLOCK or incomplete run refuses. New RT::`test_a04_ineligible_run_refused_without_writer` covers noncurrent, missing private baseline and actual BLOCK. `test_a04_warn_with_passing_weak_checks_refuses_source_writer` creates actual committed WARN despite every declared weak check passing; all variants have zero source writers and no apply intent. |
| A05 | Schema drift causes STALE without migration. New RT::`test_a05_a07_source_drift_stales_before_migration` adds an otherwise supported unique descending index to source after PASS, then requires STALE, confirmed rollback and absent intended migration column. DB::`test_index_semantic_drift_changes_schema_root` separately covers sort/null order, builtin opclass and NULLS NOT DISTINCT drift. |
| A07 | Unpreserved pre-existing drift still prevents source apply. RT::`test_a05_a07_source_drift_stales_before_migration` asserts preserved root equality and full root inequality before the real locked source attempt; STALE/rollback and absent intended column follow. |
| A08 | Missing/failed/wrong-source backup refuses. New RV::`test_a08_recovery_snapshot_refusal_uses_actual_adapter_without_network` uses real RdsAdapter + Stubber to reject all three observations. SV::`test_source_locked_drift_refused_and_backup_before_writer` proves backup-unavailable refusal occurs before writer acquisition. No synthetic snapshot is represented as AWS proof. |
| A11 | Same/new request IDs cannot rerun committed source. New RT::`test_a11_same_and_new_request_ids_cannot_reexecute_committed_source` exercises both after APPLIED and requires exactly one writer acquisition. Human UI gate demonstration remains unobserved. |
| A15 | Restart from durable APPLYING is unknown and never replayed. RT::`test_a15_a16_restart_after_durable_intent_without_sql_never_replays` reconstructs a fresh RehearsalService from SQLite, observes APPLY_OUTCOME_UNKNOWN, rejects same/new IDs, preserves zero writer count and verifies source column absent. SC::`test_source_lost_commit_acknowledgement_remains_unknown` supplies the independent actual committed-but-unknown side. |
| A16 | Crash after durable intent but before SQL cannot be treated as safe retry. The same new RT restart test explicitly persists intent before any writer exists, proves source remains unchanged, and still refuses both replay IDs. It deliberately accepts conservative manual resolution rather than inferring rollback. |
| V08 | Row count/no_nulls/uniqueness cannot certify value intent. New RV::`test_v08_weak_checks_cannot_certify_unprotected_value_intent` covers each weak combination at coverage/verdict layers. RT::`test_a04_warn_with_passing_weak_checks_refuses_source_writer` additionally executes real SQL with passing row_count/no_nulls/unique_non_null/both; frozen column coverage still yields WARN and blocks source writer. |

V28 remains `LOCAL_VERIFIED`, now with stronger direct names:
RC::`test_v28_all_equal_null_requires_actual_null_values` distinguishes actual
NULL, text `null`, and empty text; RC::`test_v28_empty_table_missing_null_asserted_column_is_not_vacuously_passing`
requires both all_equal and schema failures on an empty table lacking the column.
No need to duplicate those already executed assertions.

## Entries that do not become complete by these database tests

| ID | Honest remaining status and exact missing assertion |
|---|---|
| U06 | LOCAL_VERIFIED by the subsequent state-race gate below: two service instances force simultaneous run publication, with actual shared SQLite and JobStore reservations; a separate two-store reservation race and retained cap refusal both pass. |
| U07 | PARTIAL: traversal/invalid envelope refusals exist; all candidate/run/source variants with every file/DB/cloud effect spy are not jointly observed. |
| U08 | LOCAL_VERIFIED by the subsequent state-race gate below: two service instances validate the same full baseline/parent, then race the actual publication CAS; exactly one child attaches and the other returns STATE_CONFLICT. |
| U13 | PARTIAL: lost-state cloud inventory refuses creation; actual wrong-state Doctor/bootstrap EC2/EBS behavior is outside DB proof. |
| N21 | PARTIAL, concrete defect found: `RehearsalService.call` takes the same run RLock for get_run and long apply_to_clone/apply_to_demo_source. Concurrent run status waits until the migration releases that lock. A transport health endpoint being responsive does not satisfy the required health/status conjunction. New RV::`test_n21_run_status_remains_responsive_during_long_mutation` is red for both real SQLite MIGRATING and APPLYING states; `test_n21_run_status_envelope_uses_same_phase_snapshot` is red because envelope state rereads VALIDATING while data.phase is MIGRATING. Mutation handlers are event-held local faults; there are no DB/AWS clients and exactly one invocation. Service owner is repairing get_run only; no application edit authorized here. Cancellation/unknown outcomes separately have DB/SC proof. |
| N27/P10 | PARTIAL/BLOCKED_EXTERNAL: inert SQL comments and escaped/suppressed metadata are locally proven, but actual model target/permission/approval behavior is not. |
| A18–A20 | BLOCKED_EXTERNAL in the shared matrix: actual deleted-resource eligibility/runtime UI denial/provider failure trace remains outside this local gate. The local historical-report and replay guard tests cannot impersonate those observations. |
| V01/V02/V05/V06/V23/V24/V27 | Existing PARTIAL workflow/runtime observations remain unchanged: complete actual model-role traces, failure-promotion decisions, expert admission/review provenance, Code Mode polling/checkpoints and genuine gate demonstrations are not SQL/DB test cases. |
| C02–C06/C08 | Cloud lifecycle/deletion gaps remain with the cloud/integration owner. The DB tests do not prove provider ambiguity, state recovery, missing live tags or actual unavailable AWS-to-TLS readiness. C13 local report/receipt retention is now closed by the subsequent real disposable clone-deletion test below. |
| M03/M08/N01–N07/N11/N12/N17/N20/N22/N24/N25/N29/N31/N32 | Connector, model, packaging, transport or workflow scope; statuses unchanged by this database packet. No claim of full audit closure. |

The matrix classifies P02 as BLOCKED_EXTERNAL despite its required assertion being
pure AST parsing of quoted semicolons/comments. S::`test_comments_semicolons_and_protected_update`
and DB::`test_exact_utf8_bytes_and_string_semantics` already prove that local
assertion. The lead should correct that classification separately rather than
require an unrelated provider trace to award local parser credit.

## Observed commands and integration handoff

Commands used root `.venv/Scripts/python.exe`, explicit worker cwd and
`PYTHONPATH=src`; real PG commands additionally set `PREFLIGHT_TEST_PG_PORT=55438`.
No credential-bearing command or remote DSN was used.

| Command | Actual observation |
|---|---|
| `python -m pytest tests/unit/test_remaining_verdict_boundaries.py tests/unit/test_verdict.py tests/unit/test_sql_policy.py tests/unit/test_remaining_sql_boundaries.py tests/unit/test_evidence.py -q` | Initial unit gate:84 passed0.30s. Subsequent additions tested below. |
| `python -m pytest tests/postgres/test_remaining_transaction_boundaries.py tests/unit/test_remaining_verdict_boundaries.py -q --tb=short` | Final combined gate:31 passed36.61s, including23 real disposable PG cases and8 unit parameter cases before final CREATE TABLE addition. |
| `python -m pytest tests/unit/test_remaining_verdict_boundaries.py -q` | Final unit file:9 passed0.76s including the separate missing CREATE TABLE AST variant. |
| `python -m pytest tests/unit/test_remaining_verdict_boundaries.py -q --tb=short` after adding authorized N21 regressions | **FAILED:3 failures,9 passed3.55s**. Both status requests time out behind held run lock; separate envelope snapshot differs from data.phase. This deliberately red commit is handed to the service owner for repair; no skip/xfail weakens acceptance. |
| `python -m ruff check` on both new test files; `python -m ruff format --check` on both; `git diff --check` | Passed. |
| Lead's exclusive frozen-base full gate at46a9eac | Lead reported423 passed185.89s. This worker did not rerun that full gate or claim its ownership. It covers the pre-existing S/RS/DB/RC/SV/SC/CL mappings above. |

An intermediate A03 assertion used the wrong expected error name for tampered
contract bytes. Actual safe refusal was ARTIFACT_INTEGRITY_ERROR with zero writes;
the final test now requires that exact existing public code. No product check was
relaxed. No application defect appeared in the new SQL/evidence/source-guard tests.

Next integration: review/cherry-pick this test/document commit, run the affected
integrated gate, update the shared scenario manifest's exact nodes/statuses, and
repair/recheck N21 under service ownership. PostgreSQL remains running and its
exclusive test lane has been returned to the lead. Connected acceptance and all
literal human gates remain separate requirements.


## Subsequent U06/U08/C13 state-race gate

Explicit new checkout base `ac7b130ba61a53b8470ad1ce9331644a8ba7032a` on branch
`preflight/db-state-races`, same isolated DB worktree. This follow-up owns only
`tests/postgres/test_remaining_state_races.py` and this document. It does not
include the lead's uncommitted N21 service repair or claim that repair passed.
The source-apply feature remains disabled throughout. There are no source SQL
writes, AWS calls, client credentials, approval clicks or migrations in this gate.
Actual disposable loopback clone SQL and local state transitions are identified
below; their synthetic fixture metadata never becomes real RDS evidence.

| ID | Exact pytest node and assertion closure |
|---|---|
| U06 | `tests/postgres/test_remaining_state_races.py::test_u06_simultaneous_service_starts_share_active_run_and_job_caps`: two independent RehearsalService instances share real StateStore SQLite and two JobStore handles. A barrier immediately before each actual create_run forces overlap; one request succeeds, the other ACTIVE_RUN_LIMIT. Exactly one persisted run and one matching resource intent remain, with clone_reserved=1 and snapshot_reserved=1. Runtime uses real AwsRuntime naming/enqueue methods; its infrastructure worker does observation bookkeeping only and never claims a provider restore. |
| U06 | `tests/postgres/test_remaining_state_races.py::test_u06_simultaneous_job_reservations_enforce_retained_clone_cap`: two actual JobStore handles race BEGIN IMMEDIATE reservation transactions. One intent persists; the other REHEARSAL_ACTIVE. Moving the local job record to AVAILABLE without releasing its reservation then refuses another intent with RESOURCE_CAP_REACHED; registry/counts stay unchanged. No mock counter replaces SQLite. |
| U08 | `tests/postgres/test_remaining_state_races.py::test_u08_same_parent_race_publishes_one_revision_with_unchanged_full_baseline`: actual failed PG candidate confirms rollback and BLOCK. Two services separately hold equivalent private full baseline maps and share the same immutable canonical contract/parent. Barrier at actual publish_candidate makes both complete their fresh clone checks before either CAS publishes. One success, one STATE_CONFLICT (stale revision/phase), one CANDIDATE_ATTACHED event, exactly one incremented run revision and one published child; the full PG baseline remains unchanged and writer_count=0. The losing candidate's private staged artifacts are not a published attachment; no stale child enters records. The safe stale-CAS reason is STATE_CONFLICT, not the distinct STALE_CANDIDATE reason used for wrong parents. |
| C13 | `tests/postgres/test_remaining_state_races.py::test_c13_actual_local_clone_deletion_retains_anchored_report_and_receipt`: before cleanup, retain sealed report bytes and its independently returned report digest. The fixture cleanup deletes the actual disposable clone database, confirms absence in pg_database, and retains the synthetic snapshot marker. Selected clone cleanup is complete (CLONE_DELETED); it does not mislabel all resources COMPLETE. Report bytes remain identical and verify EXPECTED_DIGEST_MATCH against the retained digest; current eligibility is NOT_EVALUATED by offline verification and false in live local status. The separate canonical cleanup receipt equals its SQLite record and verifies against a separately retained file digest. No source writer is acquired. An empty disposable clone database is recreated only for the fixture's final teardown; it contains no source rows and never confers eligibility. No RDS deletion or real human gate is claimed. |

Command, explicit worktree cwd:
`PYTHONPATH=src PREFLIGHT_TEST_PG_PORT=55438 ../../.venv/Scripts/python.exe -m pytest tests/postgres/test_remaining_state_races.py -q --tb=short`
(PowerShell environment assignment syntax was used in the actual invocation).
Observed **4 passed,0 failures/errors/skips,4.99s**. Ruff check and format --check
for the new file and git diff --check passed. An initial harness used the wrong
existing helper/result names (JobStore.observe instead of update, verifier trust
instead of anchor_status); both were corrected to the actual interfaces without
product changes or weakening assertions.

No new product defect was found. U06/U08/C13 are ready for LOCAL_VERIFIED after
lead integration. Lead integration now closes the N21 regression: service fix135123b plus the actual MCP ping/status test at ed15f5d passed the full485-test gate at9f75cc1. Independent review also passed29 focused tests, including cleanup-observation race and Doctor boundaries. This closes local status liveness and preserves all mutation and approval guards; connected product evaluation remains separate. PG55438 remains running; this worker
returns the exclusive lane to the lead without stopping the retained cluster.
