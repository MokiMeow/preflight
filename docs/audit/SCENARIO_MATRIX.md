# All 153 specified scenarios and 10 agent evaluations

Implementation: `9f75cc1`; frozen integrated gate: 485 passed, zero errors/failures/skips in 236.95s. Scenario judgments require each complete assertion; test count is not scenario count.

Counts: LOCAL_VERIFIED: 89, PARTIAL: 34, BLOCKED_EXTERNAL: 22, NOT_RUN: 8.

## U01 — Text/base64 intake with trailing newline, CRLF, Unicode comments

**LOCAL_VERIFIED**. Required: SHA-256 matches original bytes; no normalization

Observed scope: All required assertion clauses are covered by the listed tests in the observed unit gate.

Pending: None for the mapped local assertion; connected acceptance remains separate.

- `tests/postgres/test_database.py::test_exact_utf8_bytes_and_string_semantics`
- `tests/unit/test_audit_contract_boundaries.py::test_u01_registration_preserves_exact_utf8_crlf_comment_and_trailing_newline`

## U02 — Wrong expected hash, invalid UTF-8/base64/NUL/oversize/empty SQL

**LOCAL_VERIFIED**. Required: Candidate rejected before any DB action

Observed scope: All required assertion clauses are covered by the listed tests in the observed unit gate.

Pending: None for the mapped local assertion; connected acceptance remains separate.

- `tests/postgres/test_database.py::test_non_utf8_session_rejected_before_execution`
- `tests/unit/test_audit_contract_boundaries.py::test_u02_registration_rejects_invalid_bytes_before_runtime_or_publication`

## U03 — Canonical contract vs differently formatted input JSON

**LOCAL_VERIFIED**. Required: Same canonical hash, distinct optional raw-file hash; labels accurate

Observed scope: All required assertion clauses are covered by the listed tests in the observed unit gate.

Pending: None for the mapped local assertion; connected acceptance remains separate.

- `tests/unit/test_audit_contract_boundaries.py::test_u03_canonical_contract_hash_and_raw_file_hash_labels_are_distinct`

## U04 — Unknown contract fields, duplicate JSON keys, unsupported checks, missing PK coverage

**LOCAL_VERIFIED**. Required: Reject or explicit coverage WARN per schema; never a complete PASS

Observed scope: All required assertion clauses are covered by the listed tests in the observed unit gate.

Pending: None for the mapped local assertion; connected acceptance remains separate.

- `tests/postgres/test_database.py::test_legacy_missing_schema_is_incomplete`
- `tests/postgres/test_database.py::test_precommit_empty_or_implicit_return_rolls_back`
- `tests/unit/test_audit_contract_boundaries.py::test_u04_unsupported_checks_and_primary_key_coverage_fail_closed`
- `tests/unit/test_contracts.py::test_no_unknown_contract_or_duplicate_keys`
- `tests/unit/test_service_privacy.py::test_registration_reports_static_missing_coverage_without_echoing_sql`

## U05 — Same request ID repeated / same ID changed payload

**LOCAL_VERIFIED**. Required: Same safe result / IDEMPOTENCY_CONFLICT

Observed scope: All required assertion clauses are covered by the listed tests in the observed 90-test gate.

Pending: None for the mapped local assertion; connected acceptance remains separate.

- `tests/unit/test_storage.py::test_single_active_and_idempotency`

## U06 — Two concurrent start calls

**LOCAL_VERIFIED**. Required: Single active run; resource caps held transactionally

Observed scope: Two independent services race actual shared-SQLite run publication and two JobStore handles race BEGIN IMMEDIATE reservations; one run/intent wins and retained caps reject further work.

Pending: None for the mapped local assertion; connected acceptance remains separate.

- `tests/postgres/test_remaining_state_races.py::test_u06_simultaneous_service_starts_share_active_run_and_job_caps`
- `tests/postgres/test_remaining_state_races.py::test_u06_simultaneous_job_reservations_enforce_retained_clone_cap`

## U07 — Invalid run/candidate/source ID or path traversal

**PARTIAL**. Required: Refused without a file/DB/cloud side effect

Observed scope: The listed local assertions passed; the missing clause prevents full credit.

Pending: Traversal, missing run, invalid input, and unowned source refusals are asserted; invalid candidate/source/run variants and every side-effect boundary are not.

- `tests/cloud/test_rds.py::test_cleanup_static_refusals_no_aws`
- `tests/mcp/test_transport.py::test_ten_flat_strict_schemas_structured_error_and_no_source_write`
- `tests/unit/test_service_privacy.py::test_absent_cloud_scope_no_start_effects`
- `tests/unit/test_service_privacy.py::test_invalid_argument_sentinel_never_echoed`
- `tests/unit/test_storage.py::test_exact_bytes_immutable_and_traversal`

## U08 — Two workers race phase transition or candidate parent change

**LOCAL_VERIFIED**. Required: Only correct CAS wins; no stale attachment

Observed scope: Two services validate the same full baseline and parent before a forced publication CAS race; one child attaches, one receives STATE_CONFLICT, and no stale child is published.

Pending: None for the mapped local assertion; connected acceptance remains separate.

- `tests/postgres/test_remaining_state_races.py::test_u08_same_parent_race_publishes_one_revision_with_unchanged_full_baseline`

## U09 — Report envelope digest verification

**LOCAL_VERIFIED**. Required: Payload-only digest; no self-reference; tamper detected

Observed scope: All required assertion clauses are covered by the listed tests in the observed 90-test gate.

Pending: None for the mapped local assertion; connected acceptance remains separate.

- `tests/unit/test_reports.py::test_seal_hashes_payload_only_and_verifier_labels_anchor`
- `tests/unit/test_reports.py::test_verifier_detects_old_hash_and_rehashed_anchor_tampering`

## U10 — New candidate report and later apply receipt

**LOCAL_VERIFIED**. Required: Old report bytes/digest unchanged

Observed scope: Old candidate report hash remains after new candidate; sealed report digest remains after actual local source apply/receipt; ArtifactStore immutable bytes and report integrity checks.

Pending: None for the mapped local assertion; connected acceptance remains separate.

- `tests/postgres/test_service.py::test_bad_rollback_revision_good_pass_exact_report_and_disabled_source`
- `tests/postgres/test_service.py::test_source_service_guarded_apply_and_replay_receipt_local_only`
- `tests/unit/test_storage.py::test_exact_bytes_immutable_and_traversal`

## U11 — Crash between report file publication and SQLite reference

**LOCAL_VERIFIED**. Required: Orphan reconciled safely; no false PASS/approval

Observed scope: Injected interruption after JSON publication; exact bytes/timestamp retained; restart ERROR keeps historical proof without restoring current source eligibility.

Pending: None for the mapped local assertion; connected acceptance remains separate.

- `tests/postgres/test_service.py::test_report_publication_fault_retry_reuses_sealed_payload`
- `tests/postgres/test_service.py::test_report_restart_publication_retains_history_without_reenabling_source`

## U12 — Accidental public serialization of private evidence object

**LOCAL_VERIFIED**. Required: Raw keys, rows and private maps are absent

Observed scope: All required assertion clauses are covered by the listed tests in the observed 90-test gate.

Pending: None for the mapped local assertion; connected acceptance remains separate.

- `tests/unit/test_evidence.py::test_private_bundle_not_serializable`

## U13 — Service started against empty/wrong state directory with live resources

**PARTIAL**. Required: Doctor warns/fails; no accidental adoption/replay

Observed scope: Empty/new cloud store blocks creation when owner-filtered inventory discovers existing resources.

Pending: Actual Doctor/startup wrong-state live resources, eventual invisibility, and bootstrap EC2/EBS lost state not observed.

- `tests/cloud/test_inventory.py::test_new_database_cannot_create_with_unknown_owned_snapshot_below_cap`
- `tests/cloud/test_inventory.py::test_released_reservation_live_resource_refuses_creation`
- `tests/cloud/test_inventory.py::test_unknown_owned_clone_refuses_restore`

## P01 — bad.sql and good.sql

**LOCAL_VERIFIED**. Required: Both pass syntax policy; semantic failure remains observable on clone

Observed scope: Audited database/policy assertions; final integrated gate supersedes failed worker fixture gate.

Pending: None for the mapped local assertion; connected acceptance remains separate.

- `tests/postgres/test_database.py::test_bad_rolls_back_complete_baseline`
- `tests/postgres/test_database.py::test_good_commits_real_notnull`

## P02 — Quoted semicolon/comment with word COMMIT

**BLOCKED_EXTERNAL**. Required: AST interprets correctly; no naive string splitting

Observed scope: Audited database/policy assertions; final integrated gate supersedes failed worker fixture gate.

Pending: Requires actual TrueForge/model/Daytona/human trace or outage/denial behavior; local parsing/guards do not satisfy this runtime assertion.

- `tests/unit/test_sql_policy.py::test_comments_semicolons_and_protected_update`

## P03 — Explicit BEGIN/COMMIT/ROLLBACK, psql backslash command

**LOCAL_VERIFIED**. Required: Reject

Observed scope: BEGIN/COMMIT/ROLLBACK, psql backslash commands, SAVEPOINT and SET TRANSACTION are all rejected by the recursive parser tests; no executable plan is returned.

Pending: None for the mapped local assertion; connected acceptance remains separate.

- `tests/unit/test_sql_policy.py::test_recursive_rejection`
- `tests/unit/test_remaining_sql_boundaries.py::test_p03_through_p08_unsupported_candidate_is_rejected`

## P04 — DO/CALL/COPY/SELECT/DELETE/INSERT/TRUNCATE/GRANT/CREATE/DROP

**LOCAL_VERIFIED**. Required: Reject

Observed scope: The recursive and remaining-boundary cases cover every named forbidden statement, including the separate ordinary CREATE TABLE AST variant, without returning a plan.

Pending: None for the mapped local assertion; connected acceptance remains separate.

- `tests/unit/test_sql_policy.py::test_recursive_rejection`
- `tests/unit/test_remaining_sql_boundaries.py::test_p03_through_p08_unsupported_candidate_is_rejected`
- `tests/unit/test_remaining_verdict_boundaries.py::test_p04_create_table_statement_is_rejected_without_a_plan`

## P05 — CREATE INDEX CONCURRENTLY or unsupported ALTER subcommand

**LOCAL_VERIFIED**. Required: Reject

Observed scope: Concurrent index creation plus unsupported index/drop/default/conditional-add/trigger/rename ALTER surfaces are rejected.

Pending: None for the mapped local assertion; connected acceptance remains separate.

- `tests/unit/test_sql_policy.py::test_recursive_rejection`
- `tests/unit/test_remaining_sql_boundaries.py::test_p03_through_p08_unsupported_candidate_is_rejected`

## P06 — UPDATE with CTE, FROM, RETURNING, nested query or function call

**LOCAL_VERIFIED**. Required: Reject recursively

Observed scope: Recursive negatives cover CTE, FROM, RETURNING, subquery, function, CASE, EXISTS, IN, LIKE, array and collation branches.

Pending: None for the mapped local assertion; connected acceptance remains separate.

- `tests/unit/test_sql_policy.py::test_recursive_rejection`
- `tests/unit/test_remaining_sql_boundaries.py::test_p03_through_p08_unsupported_candidate_is_rejected`

## P07 — Default/generated/identity expression or user-defined cast/operator/type

**LOCAL_VERIFIED**. Required: Reject

Observed scope: Default/generated/identity, custom casts/operators, array types and qualified builtin-lookalike surfaces are rejected.

Pending: None for the mapped local assertion; connected acceptance remains separate.

- `tests/unit/test_sql_policy.py::test_recursive_rejection`
- `tests/unit/test_remaining_sql_boundaries.py::test_p03_through_p08_unsupported_candidate_is_rejected`
- `tests/unit/test_remaining_sql_boundaries.py::test_p07_custom_builtin_lookalike_does_not_expand_grammar`

## P08 — Wrong schema/table, unqualified target, unknown column, PK mutation

**LOCAL_VERIFIED**. Required: Reject

Observed scope: Wrong or unqualified targets, PK mutation, and unknown write/read/predicate columns all fail closed.

Pending: None for the mapped local assertion; connected acceptance remains separate.

- `tests/unit/test_sql_policy.py::test_recursive_rejection`
- `tests/unit/test_sql_policy.py::test_unknown_metadata_column`
- `tests/unit/test_remaining_sql_boundaries.py::test_p08_unknown_target_read_or_predicate_column_refused_at_metadata`

## P09 — Multiple statements where later statement is forbidden

**LOCAL_VERIFIED**. Required: Entire candidate rejected before execution

Observed scope: A later COMMIT, CALL, TRUNCATE or DROP rejects the whole candidate before registration or execution and returns no plan.

Pending: None for the mapped local assertion; connected acceptance remains separate.

- `tests/unit/test_sql_policy.py::test_recursive_rejection`
- `tests/unit/test_remaining_sql_boundaries.py::test_p09_forbidden_later_statement_rejects_entire_candidate`

## P10 — Supported statement plus malicious SQL-comment instructions

**BLOCKED_EXTERNAL**. Required: Comments remain inert; tool/approval policy unchanged

Observed scope: Audited database/policy assertions; final integrated gate supersedes failed worker fixture gate.

Pending: Requires actual TrueForge/model/Daytona/human trace or outage/denial behavior; local parsing/guards do not satisfy this runtime assertion.

- `tests/unit/test_sql_policy.py::test_comments_semicolons_and_protected_update`

## P11 — Unreviewed triggers/rules/event triggers, RLS, foreign-key/cascade graph, partitions/inheritance

**LOCAL_VERIFIED**. Required: Object policy refuses support, never disables the feature

Observed scope: Disposable PostgreSQL catalog checks cover trigger, rule, event-trigger, RLS, FK/cascade, partition and inheritance families; policy refuses rather than disables them.

Pending: None for the mapped local assertion; connected acceptance remains separate.

- `tests/postgres/test_database.py::test_trigger_and_inheritance_rejected`
- `tests/postgres/test_database.py::test_semantic_unsafe_objects`
- `tests/postgres/test_remaining_catalog_boundaries.py::test_p11_p12_unsupported_catalog_capability_never_returns_evidence`
- `tests/postgres/test_remaining_catalog_boundaries.py::test_p11_enabled_event_trigger_rejected_without_firing_it`

## P12 — Unsafe CHECK/exclusion constraint or expression/partial index, user-defined collation

**LOCAL_VERIFIED**. Required: Reject unsupported execution surface

Observed scope: Disposable PostgreSQL catalog checks reject CHECK/exclusion/expression/partial-index/custom-collation and custom-opclass surfaces without returning evidence.

Pending: None for the mapped local assertion; connected acceptance remains separate.

- `tests/postgres/test_database.py::test_semantic_unsafe_objects`
- `tests/postgres/test_remaining_catalog_boundaries.py::test_p11_p12_unsupported_catalog_capability_never_returns_evidence`
- `tests/postgres/test_remaining_catalog_boundaries.py::test_p12_user_defined_operator_class_rejected`

## P13 — Supported UPDATE of a protected non-PK value

**LOCAL_VERIFIED**. Required: Syntax accepted; preservation violation caught by comparator

Observed scope: Audited database/policy assertions; final integrated gate supersedes failed worker fixture gate.

Pending: None for the mapped local assertion; connected acceptance remains separate.

- `tests/postgres/test_database.py::test_wrong_data_committed_then_block`

## P14 — Parser/database major mismatch

**LOCAL_VERIFIED**. Required: Readiness fails before migration

Observed scope: Wrong pglast/parser major is refused before parsing or execution; actual disposable PostgreSQL separately proves server-major readiness refusal.

Pending: None for the mapped local assertion; connected acceptance remains separate.

- `tests/unit/test_remaining_verdict_boundaries.py::test_p14_parser_mismatch_refused_before_parse_or_execution`
- `tests/postgres/test_database.py::test_tls_hostname_ca_major_and_role`

## D01 — Add a NOT NULL text column to populated table without backfill

**LOCAL_VERIFIED**. Required: PostgreSQL failure; confirmed rollback; pre-state preserved

Observed scope: Audited database/policy assertions; final integrated gate supersedes failed worker fixture gate.

Pending: None for the mapped local assertion; connected acceptance remains separate.

- `tests/postgres/test_database.py::test_bad_rolls_back_complete_baseline`
- `tests/postgres/test_database.py::test_good_commits_real_notnull`
- `tests/postgres/test_database.py::test_wrong_data_committed_then_block`

## D02 — Add nullable column, backfill, set NOT NULL

**LOCAL_VERIFIED**. Required: SQL commits and schema flag truly NOT NULL

Observed scope: Audited database/policy assertions; final integrated gate supersedes failed worker fixture gate.

Pending: None for the mapped local assertion; connected acceptance remains separate.

- `tests/postgres/test_database.py::test_bad_rolls_back_complete_baseline`
- `tests/postgres/test_database.py::test_good_commits_real_notnull`
- `tests/postgres/test_database.py::test_wrong_data_committed_then_block`

## D03 — Correct row count but one altered protected email

**LOCAL_VERIFIED**. Required: SQL can commit; preserved-hash check fails; verdict BLOCK

Observed scope: Audited database/policy assertions; final integrated gate supersedes failed worker fixture gate.

Pending: None for the mapped local assertion; connected acceptance remains separate.

- `tests/postgres/test_database.py::test_bad_rolls_back_complete_baseline`
- `tests/postgres/test_database.py::test_good_commits_real_notnull`
- `tests/postgres/test_database.py::test_wrong_data_committed_then_block`

## D04 — Equal row count but different primary-key set

**LOCAL_VERIFIED**. Required: Missing/extra keys reported as counts; not treated as unchanged

Observed scope: Audited database/policy assertions; final integrated gate supersedes failed worker fixture gate.

Pending: Safe missing/extra/changed counts now asserted exactly.

- `tests/postgres/test_database.py::test_aggregate_missing_extra_and_changed_rows_are_safe_counts`
- `tests/postgres/test_database.py::test_changed_keys_and_order_and_full_drift`

## D05 — Same rows inserted/retrieved in different order

**LOCAL_VERIFIED**. Required: Canonical aggregate roots match

Observed scope: A descending-index CLUSTER demonstrably changes the first physical row while canonical full evidence remains identical; reversed map insertion order also preserves roots.

Pending: None for the mapped local assertion; connected acceptance remains separate.

- `tests/postgres/test_remaining_transaction_boundaries.py::test_d05_real_physical_row_order_changes_without_changing_roots`
- `tests/unit/test_evidence.py::test_domain_length_and_order`

## D06 — Integer 1 vs text "1", NULL vs empty text vs text "null"

**LOCAL_VERIFIED**. Required: Distinct encodings/digests

Observed scope: Audited database/policy assertions; final integrated gate supersedes failed worker fixture gate.

Pending: Equivalent timestamp/null/type encodings; BC/infinity values unsupported conversion remain unproven.

- `tests/unit/test_evidence.py::test_type_tags_are_distinct`
- `tests/unit/test_evidence.py::test_unsupported_no_stringification`
- `tests/unit/test_evidence.py::test_utc_microseconds`

## D07 — Equivalent timestamptz values in different offsets

**LOCAL_VERIFIED**. Required: Same UTC microsecond encoding

Observed scope: Audited database/policy assertions; final integrated gate supersedes failed worker fixture gate.

Pending: Equivalent timestamp/null/type encodings; BC/infinity values unsupported conversion remain unproven.

- `tests/unit/test_evidence.py::test_type_tags_are_distinct`
- `tests/unit/test_evidence.py::test_unsupported_no_stringification`
- `tests/unit/test_evidence.py::test_utc_microseconds`

## D08 — Naive timestamp or unsupported float/JSON/array/custom type

**LOCAL_VERIFIED**. Required: Coverage incomplete; never silent stringification/PASS

Observed scope: Audited database/policy assertions; final integrated gate supersedes failed worker fixture gate.

Pending: Equivalent timestamp/null/type encodings; BC/infinity values unsupported conversion remain unproven.

- `tests/unit/test_evidence.py::test_type_tags_are_distinct`
- `tests/unit/test_evidence.py::test_unsupported_no_stringification`
- `tests/unit/test_evidence.py::test_utc_microseconds`

## D09 — Missing PK/table/column or inaccessible metadata

**LOCAL_VERIFIED**. Required: Specific failure/not_run, no fabricated zero count

Observed scope: Missing table/PK/columns and inaccessible catalog/rows produce specific failures; none fabricates zero evidence or returns an EvidenceBundle.

Pending: None for the mapped local assertion; connected acceptance remains separate.

- `tests/postgres/test_remaining_catalog_boundaries.py::test_d09_missing_table_primary_key_or_preserved_column_is_specific`
- `tests/postgres/test_remaining_catalog_boundaries.py::test_d09_inaccessible_catalog_does_not_fabricate_metadata`
- `tests/postgres/test_remaining_catalog_boundaries.py::test_d09_inaccessible_rows_do_not_become_zero_count`
- `tests/postgres/test_remaining_catalog_boundaries.py::test_d09_missing_full_baseline_column_is_not_silently_omitted`

## D10 — Scan exceeds rows, bytes or deadline

**LOCAL_VERIFIED**. Required: Stops within budget and cannot PASS

Observed scope: Row, serialized-byte, catalog, fetch/CPU and whole-capture deadline overruns stop without partial evidence or PASS; fresh captures roll back.

Pending: None for the mapped local assertion; connected acceptance remains separate.

- `tests/postgres/test_database.py::test_scan_budget_and_huge_cell`
- `tests/postgres/test_remaining_catalog_boundaries.py::test_d10_serialized_budget_excludes_escape_expansion_overrun`
- `tests/postgres/test_remaining_catalog_boundaries.py::test_d10_whole_capture_deadline_includes_row_processing`
- `tests/postgres/test_remaining_catalog_boundaries.py::test_d10_whole_capture_deadline_includes_catalog_processing`
- `tests/postgres/test_remaining_catalog_boundaries.py::test_d10_baseline_query_timeout_cannot_return_partial_evidence`

## D11 — All required checks absent/not_run

**LOCAL_VERIFIED**. Required: WARN or BLOCK according to cause, never PASS

Observed scope: Audited database/policy assertions; final integrated gate supersedes failed worker fixture gate.

Pending: Strict adapter callbacks checked; verdict missing-check manifest logic belongs lead lane.

- `tests/postgres/test_database.py::test_precommit_empty_or_implicit_return_rolls_back`
- `tests/postgres/test_database.py::test_precommit_typed_manifest_fail_closed`

## D12 — Multiple statements: first mutates, second fails

**LOCAL_VERIFIED**. Required: First mutation rolled back too

Observed scope: Audited database/policy assertions; final integrated gate supersedes failed worker fixture gate.

Pending: None for the mapped local assertion; connected acceptance remains separate.

- `tests/postgres/test_database.py::test_lock_timeout_and_no_leak`
- `tests/postgres/test_database.py::test_multiple_statement_failure_rolls_back_first`
- `tests/postgres/test_database.py::test_whole_script_deadline_across_quick_updates`

## D13 — Several individually quick statements exceed whole-script limit

**LOCAL_VERIFIED**. Required: Deadline enforced; no PASS based only on statement timeout

Observed scope: Audited database/policy assertions; final integrated gate supersedes failed worker fixture gate.

Pending: None for the mapped local assertion; connected acceptance remains separate.

- `tests/postgres/test_database.py::test_lock_timeout_and_no_leak`
- `tests/postgres/test_database.py::test_multiple_statement_failure_rolls_back_first`
- `tests/postgres/test_database.py::test_whole_script_deadline_across_quick_updates`

## D14 — Lock contention or cancellation

**LOCAL_VERIFIED**. Required: Safe timeout/known-outcome classification, no leaked DETAIL

Observed scope: Audited database/policy assertions; final integrated gate supersedes failed worker fixture gate.

Pending: None for the mapped local assertion; connected acceptance remains separate.

- `tests/postgres/test_database.py::test_lock_timeout_and_no_leak`
- `tests/postgres/test_database.py::test_multiple_statement_failure_rolls_back_first`
- `tests/postgres/test_database.py::test_whole_script_deadline_across_quick_updates`

## D15 — DB error that embeds a row value/password-like sentinel

**LOCAL_VERIFIED**. Required: Tool/log/report output contains only safe classification

Observed scope: An actual PostgreSQL NotNullViolation contains the private sentinel internally, while tool, baseline, report JSON/Markdown and captured logs retain only safe SQLSTATE classification.

Pending: None for the mapped local assertion; connected acceptance remains separate.

- `tests/postgres/test_remaining_transaction_boundaries.py::test_d15_private_database_error_value_absent_from_tool_logs_and_reports`

## D16 — Legacy contract missing explicit schema expectations

**LOCAL_VERIFIED**. Required: Incomplete coverage; propose revision, never silent upgrade

Observed scope: Audited database/policy assertions; final integrated gate supersedes failed worker fixture gate.

Pending: None for the mapped local assertion; connected acceptance remains separate.

- `tests/postgres/test_database.py::test_legacy_missing_schema_is_incomplete`
- `tests/postgres/test_database.py::test_zero_nulls_is_not_notnull`

## D17 — A nullable column happens to contain no NULLs

**LOCAL_VERIFIED**. Required: no_nulls may pass but column_not_null/schema check fails

Observed scope: Audited database/policy assertions; final integrated gate supersedes failed worker fixture gate.

Pending: None for the mapped local assertion; connected acceptance remains separate.

- `tests/postgres/test_database.py::test_legacy_missing_schema_is_incomplete`
- `tests/postgres/test_database.py::test_zero_nulls_is_not_notnull`

## D18 — Consistent source/clone state but different irrelevant OIDs

**LOCAL_VERIFIED**. Required: Normalized schema fingerprints match

Observed scope: Independent databases have different table and primary-index OIDs but identical normalized full baselines. Real snapshot-restored RDS normalization remains separate connected evidence.

Pending: None for the mapped local assertion; connected acceptance remains separate.

- `tests/postgres/test_remaining_transaction_boundaries.py::test_d18_independent_table_and_index_oids_do_not_change_normalized_roots`

## D19 — A failed candidate followed by an accepted same-contract revision

**LOCAL_VERIFIED**. Required: Full unchanged baseline checked before clone reuse

Observed scope: Accepted same-contract reuse requires the unchanged full baseline; unpreserved drift changes the full root and refuses attachment without changing the current candidate.

Pending: None for the mapped local assertion; connected acceptance remains separate.

- `tests/postgres/test_service.py::test_bad_rollback_revision_good_pass_exact_report_and_disabled_source`
- `tests/postgres/test_remaining_transaction_boundaries.py::test_d19_d20_revision_requires_private_maps_and_full_unchanged_baseline`

## D20 — Committed-but-invalid clone or lost baseline maps

**LOCAL_VERIFIED**. Required: Same-clone revision refused; fresh rehearsal required

Observed scope: Committed-invalid clone reuse and direct private-map loss are both refused without changing the current attachment; a fresh rehearsal is required.

Pending: None for the mapped local assertion; connected acceptance remains separate.

- `tests/postgres/test_service.py::test_committed_wrong_data_blocks_and_revision_refused`
- `tests/postgres/test_remaining_transaction_boundaries.py::test_d19_d20_revision_requires_private_maps_and_full_unchanged_baseline`

## A01 — Source apply feature disabled

**LOCAL_VERIFIED**. Required: Refuse before source writer acquired

Observed scope: Disabled source feature refuses before local source writer acquisition.

Pending: None for the mapped local assertion; connected acceptance remains separate.

- `tests/postgres/test_service.py::test_bad_rollback_revision_good_pass_exact_report_and_disabled_source`
- `tests/postgres/test_service.py::test_source_service_guarded_apply_and_replay_receipt_local_only`

## A02 — Wrong source/account/database or source equal to clone

**LOCAL_VERIFIED**. Required: Refuse

Observed scope: Wrong source/database/source-equals-clone scopes fail before writer acquisition or durable intent; inert botocore Stubber proves wrong-account adapter refusal without an AWS call.

Pending: None for the mapped local assertion; connected acceptance remains separate.

- `tests/postgres/test_remaining_transaction_boundaries.py::test_a02_source_scope_refusal_precedes_writer`
- `tests/cloud/test_rds.py::test_wrong_account_before_resource_call`

## A03 — Wrong migration/report hash, altered stored contract or report

**LOCAL_VERIFIED**. Required: Refuse, no write

Observed scope: Both supplied digests plus canonical contract file, stored contract record and report file are independently tampered; every variant refuses with zero source writer and no apply intent.

Pending: None for the mapped local assertion; connected acceptance remains separate.

- `tests/postgres/test_remaining_transaction_boundaries.py::test_a03_approved_artifact_changes_refused_without_writer`

## A04 — Non-current candidate or WARN/BLOCK/incomplete run

**LOCAL_VERIFIED**. Required: Refuse

Observed scope: Noncurrent, incomplete, BLOCK and actual committed WARN runs all refuse with zero source writers and no apply intent, even when all declared weak checks pass.

Pending: None for the mapped local assertion; connected acceptance remains separate.

- `tests/postgres/test_remaining_transaction_boundaries.py::test_a04_ineligible_run_refused_without_writer`
- `tests/postgres/test_remaining_transaction_boundaries.py::test_a04_warn_with_passing_weak_checks_refuses_source_writer`

## A05 — Source schema drift

**LOCAL_VERIFIED**. Required: STALE; no migration applied

Observed scope: Supported source index drift after PASS yields STALE, confirmed rollback and no intended column; independent tests cover index semantic drift variants.

Pending: None for the mapped local assertion; connected acceptance remains separate.

- `tests/postgres/test_remaining_transaction_boundaries.py::test_a05_a07_source_drift_stales_before_migration`
- `tests/postgres/test_database.py::test_index_semantic_drift_changes_schema_root`

## A06 — Source preserved-data drift

**LOCAL_VERIFIED**. Required: STALE; no migration applied

Observed scope: Committed preserved-data drift is compared under source locks and yields STALE/rolled_back.

Pending: None for the mapped local assertion; connected acceptance remains separate.

- `tests/postgres/test_service.py::test_source_locked_drift_refused_and_backup_before_writer`

## A07 — Pre-existing nonpreserved column drift

**LOCAL_VERIFIED**. Required: Full-data guard catches it even though preservation subset matches

Observed scope: The locked source recheck observes equal preserved root but changed full root, returns STALE, rolls back and leaves the intended column absent.

Pending: None for the mapped local assertion; connected acceptance remains separate.

- `tests/postgres/test_remaining_transaction_boundaries.py::test_a05_a07_source_drift_stales_before_migration`

## A08 — Missing/failed/wrong-source recovery snapshot

**LOCAL_VERIFIED**. Required: Refuse

Observed scope: The real RdsAdapter with inert Stubber rejects missing, failed and wrong-source recovery snapshots; service refusal occurs before source writer acquisition.

Pending: None for the mapped local assertion; connected acceptance remains separate.

- `tests/unit/test_remaining_verdict_boundaries.py::test_a08_recovery_snapshot_refusal_uses_actual_adapter_without_network`
- `tests/postgres/test_service.py::test_source_locked_drift_refused_and_backup_before_writer`

## A09 — Competing source writer before versus after table locks

**LOCAL_VERIFIED**. Required: Post-lock comparison is authoritative; no check/write window

Observed scope: Real concurrent PostgreSQL writer beforelocks detected; writer afterlocks observed waiting inpg_stat_activity until commit.

Pending: None for the mapped local assertion; connected acceptance remains separate.

- `tests/postgres/test_database.py::test_lock_timeout_and_no_leak`
- `tests/postgres/test_database.py::test_repeatable_read_snapshot_survives_concurrent_writer`
- `tests/postgres/test_source_concurrency.py::test_writer_after_source_locks_waits_until_transaction_finishes`
- `tests/postgres/test_source_concurrency.py::test_writer_committed_before_source_locks_is_detected`

## A10 — Two concurrently allowed apply requests

**LOCAL_VERIFIED**. Required: Only one accepted source attempt; other refused

Observed scope: Two concurrent calls: one accepted/sourcewriter, one durable replay refusal.

Pending: None for the mapped local assertion; connected acceptance remains separate.

- `tests/postgres/test_database.py::test_lock_timeout_and_no_leak`
- `tests/postgres/test_database.py::test_repeatable_read_snapshot_survives_concurrent_writer`
- `tests/postgres/test_source_concurrency.py::test_two_concurrent_source_requests_accept_exactly_one`

## A11 — Same/new request ID after committed source apply

**LOCAL_VERIFIED**. Required: Refuse replay regardless of request ID

Observed scope: After a local APPLIED outcome, both same and new request IDs are refused and exactly one writer acquisition remains. This is not a human UI-gate demonstration.

Pending: None for the mapped local assertion; connected acceptance remains separate.

- `tests/postgres/test_remaining_transaction_boundaries.py::test_a11_same_and_new_request_ids_cannot_reexecute_committed_source`

## A12 — Source mandatory check fails before commit

**LOCAL_VERIFIED**. Required: Confirmed rollback → APPLY_FAILED

Observed scope: Audited database/policy assertions; final integrated gate supersedes failed worker fixture gate.

Pending: Adapter source-style precommit rollback real; service integration return protocol fixed by dependency.

- `tests/postgres/test_database.py::test_precommit_typed_manifest_fail_closed`
- `tests/postgres/test_database.py::test_source_precommit_wrong_data_rolls_back`

## A13 — Source commit confirmed, read-only confirmation fails

**LOCAL_VERIFIED**. Required: APPLIED_NEEDS_ATTENTION; no retry

Observed scope: Real source transaction committed; injected source-read confirmation failure yields attention, no replay.

Pending: None for the mapped local assertion; connected acceptance remains separate.

- `tests/postgres/test_database.py::test_commit_response_loss_is_unknown_not_rollback`
- `tests/postgres/test_seed_demo.py::test_commit_response_loss_is_honest_unknown`
- `tests/postgres/test_source_concurrency.py::test_source_postcommit_confirmation_failure_never_retries`

## A14 — Commit acknowledgement lost

**LOCAL_VERIFIED**. Required: APPLY_OUTCOME_UNKNOWN; no retry or automated cleanup

Observed scope: Actual COMMIT succeeds then proxy dropsack; durableUNKNOWN/replay/cleanup refused and committedschema inspected.

Pending: None for the mapped local assertion; connected acceptance remains separate.

- `tests/cloud/test_rds.py::test_cleanup_static_refusals_no_aws`
- `tests/postgres/test_database.py::test_commit_response_loss_is_unknown_not_rollback`
- `tests/postgres/test_seed_demo.py::test_commit_response_loss_is_honest_unknown`
- `tests/postgres/test_source_concurrency.py::test_source_lost_commit_acknowledgement_remains_unknown`

## A15 — Process restarts from durable APPLYING

**LOCAL_VERIFIED**. Required: Unknown until manual resolution; execution count not incremented

Observed scope: A fresh service reconstructed from durable APPLYING reports APPLY_OUTCOME_UNKNOWN and refuses same/new IDs; actual committed-but-unknown source behavior is independently exercised.

Pending: None for the mapped local assertion; connected acceptance remains separate.

- `tests/postgres/test_remaining_transaction_boundaries.py::test_a15_a16_restart_after_durable_intent_without_sql_never_replays`
- `tests/postgres/test_source_concurrency.py::test_source_lost_commit_acknowledgement_remains_unknown`

## A16 — Crash before SQL after intent persisted

**LOCAL_VERIFIED**. Required: Conservative unknown/manual resolution is allowed; never guess safe retry

Observed scope: A persisted intent before any writer exists remains conservatively unknown after restart; same/new IDs never replay and the source column stays absent.

Pending: None for the mapped local assertion; connected acceptance remains separate.

- `tests/postgres/test_remaining_transaction_boundaries.py::test_a15_a16_restart_after_durable_intent_without_sql_never_replays`

## A17 — Clone migration interrupted

**LOCAL_VERIFIED**. Required: No automatic replay, no blind “rolled back” claim

Observed scope: Audited database/policy assertions; final integrated gate supersedes failed worker fixture gate.

Pending: Real backend termination reports unknown; service restart replay behavior outside this test.

- `tests/postgres/test_database.py::test_connection_loss_before_commit_is_unknown`

## A18 — Report was PASS, then clone deleted

**BLOCKED_EXTERNAL**. Required: Current eligibility false; historical report unchanged

Observed scope: Audited database/policy assertions; final integrated gate supersedes failed worker fixture gate.

Pending: Requires actual TrueForge/model/Daytona/human trace or outage/denial behavior; local parsing/guards do not satisfy this runtime assertion.

- `external human/provider/resource tests`

## A19 — Denied request in the real UI

**BLOCKED_EXTERNAL**. Required: No service execution/write connection; source unchanged

Observed scope: Audited database/policy assertions; final integrated gate supersedes failed worker fixture gate.

Pending: Requires actual TrueForge/model/Daytona/human trace or outage/denial behavior; local parsing/guards do not satisfy this runtime assertion.

- `external human/provider/resource tests`

## A20 — Model/provider failure after a sealed report

**BLOCKED_EXTERNAL**. Required: Report immutable; agent workflow incomplete, no invented apply

Observed scope: Audited database/policy assertions; final integrated gate supersedes failed worker fixture gate.

Pending: Actual provider outage after a sealed report has not been observed; local restart retention alone is insufficient.

- `external human/provider/resource tests`

## C01 — Restore request construction

**LOCAL_VERIFIED**. Required: New ID, exact snapshot, explicit subnet/SG/private settings and run tags

Observed scope: Stubber asserts exact new clone ID, snapshot, subnet/SG/private settings and run+snapshot tags.

Pending: Real AWS authorization and restored-resource provenance remain blocked; scenario request-construction assertion is local.

- `tests/cloud/test_rds.py::test_restore_private_exact_args_then_restart_reconciles`

## C02 — Ambiguous snapshot/restore create response

**PARTIAL**. Required: Describe exact existing ID before retry; no duplicate random names

Observed scope: Snapshot lost-response reconcile and generic scheduling uncertainty retain same intent.

Pending: No analogous lost clone-restore response fault test or real AWS ambiguity induced.

- `tests/cloud/test_jobs.py::test_ambiguous_or_throttled_keep_same_intent`
- `tests/cloud/test_rds_reconciliation.py::test_lost_snapshot_response_reconciles_no_duplicate`

## C03 — Restart while snapshot/clone pending

**PARTIAL**. Required: Resume observation with same resource IDs

Observed scope: Reopened SQLite scheduling and repeated adapter calls retain deterministic IDs.

Pending: No actual process crash/restart in both pending AWS phases; repeated call is not full restart proof.

- `tests/cloud/test_jobs.py::test_restart_durable_request_and_caps`
- `tests/cloud/test_jobs.py::test_tick_available_is_not_database_ready_and_poll_is_read_only`
- `tests/cloud/test_rds.py::test_restore_private_exact_args_then_restart_reconciles`
- `tests/cloud/test_rds.py::test_snapshot_create_exact_reconciled_once`

## C04 — Name exists with another run/account/tag

**PARTIAL**. Required: Refuse adoption/deletion

Observed scope: Snapshot wrong owner and wrong account ARN/source metadata refuse.

Pending: Direct clone-collision/wrong-run/missing-tag deletion path coverage thinner; no AWS ownership observations.

- `tests/cloud/test_inventory.py::test_cross_account_mapping_never_described`
- `tests/cloud/test_rds.py::test_snapshot_collision_wrong_owner_blocks`
- `tests/cloud/test_rds.py::test_source_negative_before_tags`

## C05 — Throttling, denied IAM/KMS, unsupported class/engine, deadline

**PARTIAL**. Required: Bounded error/backoff, no admin privilege escalation

Observed scope: Sanitized denial/throttle, backoff/deadline and no admin policy accepted.

Pending: KMS-specific denied operation, unsupported actual class/region, real latency cancellation and deployed IAM not observed.

- `tests/cloud/test_bootstrap_driver.py::test_runtime_admin_policy_refused`
- `tests/cloud/test_inventory.py::test_expired_job_retains_counts_does_not_delete`
- `tests/cloud/test_jobs.py::test_ambiguous_or_throttled_keep_same_intent`
- `tests/cloud/test_jobs.py::test_job_failure_retains_exact_cleanup_names`
- `tests/cloud/test_rds.py::test_provider_message_sanitized`
- `tests/cloud/test_rds_reconciliation.py::test_throttle_is_sanitized_retryable`

## C06 — AWS available but DB TLS connection unavailable

**PARTIAL**. Required: Not READY/BASELINED/PASS

Observed scope: Pure adapter job AVAILABLE is explicitly not READY.

Pending: Does not inject unavailable TLS into actual AWS-to-service readiness promotion; RDS TLS unavailable.

- `tests/cloud/test_jobs.py::test_tick_available_is_not_database_ready_and_poll_is_read_only`

## C07 — Wrong cleanup clone/snapshot or source ID substituted

**LOCAL_VERIFIED**. Required: No delete call

Observed scope: Wrong supplied source/clone/snapshot/exact selections reject before any AWS delete.

Pending: No live deletion performed; local selection invariant fully asserted.

- `tests/cloud/test_rds.py::test_cleanup_static_refusals_no_aws`

## C08 — Missing tag or live ARN mismatch

**PARTIAL**. Required: No delete call

Observed scope: Ownership/ARN rejection helpers and all-selected preflight-before-delete assertions exist.

Pending: No direct parameterized deletion-target missingRunId/cloneARN tampering test; no live target tags.

- `tests/cloud/test_rds.py::test_preflight_all_selections_before_any_delete`
- `tests/cloud/test_rds.py::test_snapshot_collision_wrong_owner_blocks`
- `tests/cloud/test_rds.py::test_source_negative_before_tags`

## C09 — Source applied/attempted, no independent pre-apply recovery backup

**LOCAL_VERIFIED**. Required: Snapshot deletion blocked

Observed scope: Source attempt with arbitrary backup name cannot delete; independent callback and same-source snapshot metadata positive control.

Pending: Local policy guard only; no real preapply-equivalent recovery asset or gate.

- `tests/cloud/test_rds.py::test_source_apply_attempt_retains_backup_without_independent_attestation`
- `tests/cloud/test_rds.py::test_verified_preapply_independent_backup`

## C10 — Unknown transaction outcome

**LOCAL_VERIFIED**. Required: Automated cleanup blocked

Observed scope: APPLY_OUTCOME_UNKNOWN/CLONE_OUTCOME_UNKNOWN/APPLYING/MIGRATING/dependentactive reject without AWS calls.

Pending: Actual transaction ambiguity classifications belong to DB/service lane; cloud policy refusal fully local.

- `tests/cloud/test_rds.py::test_cleanup_static_refusals_no_aws`

## C11 — Approved known disposable clone deletion

**BLOCKED_EXTERNAL**. Required: Observe DELETING then actual absence, if performed

Observed scope: Stubbed exact delete, DELETING and absence/reservation effects.

Pending: Whole assertion requires actual authorized live deletion/observed absence; no AWS or human approval.

- `tests/cloud/test_rds.py::test_delete_exact_clone_then_observe_absence`
- `tests/cloud/test_rds_reconciliation.py::test_cleanup_observation_frees_only_proven_absence`

## C12 — Retained clone for judging

**BLOCKED_EXTERNAL**. Required: Exact owner/reason/status recorded; no claim deletion occurred

Observed scope: No actual owned judging clone exists in audited evidence.

Pending: Actual retained ID/owner/reason/status/operator decision missing; fixture tags are not retention decision.

## C13 — Cleanup after sealed report

**LOCAL_VERIFIED**. Required: Report and separate receipts still verify

Observed scope: Actual disposable clone deletion retains byte-identical sealed report and a separate canonical cleanup receipt; both verify against independently retained digests, without claiming RDS deletion or live eligibility.

Pending: None for the mapped local assertion; connected acceptance remains separate.

- `tests/postgres/test_remaining_state_races.py::test_c13_actual_local_clone_deletion_retains_anchored_report_and_receipt`

## C14 — Resource cap reached

**LOCAL_VERIFIED**. Required: No extra creation merely to evade a failed run

Observed scope: Reservations survive errors, unknown/released-present resources block creation, retained snapshot counted across next run.

Pending: Tag inventory eventually consistent; actual lost-state AWS/EC2 resources not observed.

- `tests/cloud/test_inventory.py::test_expired_job_retains_counts_does_not_delete`
- `tests/cloud/test_inventory.py::test_new_database_cannot_create_with_unknown_owned_snapshot_below_cap`
- `tests/cloud/test_inventory.py::test_read_only_cleanup_keeps_retained_snapshot_reservation_for_new_run`
- `tests/cloud/test_inventory.py::test_released_reservation_live_resource_refuses_creation`
- `tests/cloud/test_inventory.py::test_unknown_owned_clone_refuses_restore`
- `tests/cloud/test_jobs.py::test_restart_durable_request_and_caps`

## M01 — Official client initializes Streamable HTTP server

**LOCAL_VERIFIED**. Required: Real protocol handshake and documented structured result

Observed scope: All required assertion clauses are covered by the listed tests in the observed 90-test gate.

Pending: None for the mapped local assertion; connected acceptance remains separate.

- `tests/mcp/test_transport.py::test_ten_flat_strict_schemas_structured_error_and_no_source_write`

## M02 — tools/list

**LOCAL_VERIFIED**. Required: Exactly ten business tools with strict input/output schemas

Observed scope: All required assertion clauses are covered by the listed tests in the observed 90-test gate.

Pending: None for the mapped local assertion; connected acceptance remains separate.

- `tests/mcp/test_transport.py::test_ten_flat_strict_schemas_structured_error_and_no_source_write`

## M03 — Invalid/unknown/oversize tool input

**PARTIAL**. Required: Typed error, no hidden effect

Observed scope: The listed local assertions passed; the missing clause prevents full credit.

Pending: Unknown extra input yields typed INVALID_INPUT with no source write; oversized payload and unknown tool name are not exercised over MCP.

- `tests/mcp/test_transport.py::test_ten_flat_strict_schemas_structured_error_and_no_source_write`

## M04 — Real local end-to-end via MCP

**LOCAL_VERIFIED**. Required: Full bad/revision/good/report flow, not direct Python-only calls

Observed scope: Actual HTTP official MCP bad/revision/good/report causal chain on disposable real PostgreSQL.

Pending: None for the mapped local assertion; connected acceptance remains separate.

- `tests/postgres/test_service.py::test_real_http_mcp_bad_revision_good_report`

## M05 — TrueForge saved agent uses actual OpenAI provider

**BLOCKED_EXTERNAL**. Required: Successful real provider/tool trace

Observed scope: Local components may be covered, but connected acceptance was not run.

Pending: Requires actual TrueForge/model/Daytona/human trace or outage/denial behavior; local parsing/guards do not satisfy this runtime assertion.

## M06 — Generated Daytona Python chains actual Preflight MCP tools

**BLOCKED_EXTERNAL**. Required: Real sandbox execution and useful orchestration, no credentials

Observed scope: Local components may be covered, but connected acceptance was not run.

Pending: Requires actual TrueForge/model/Daytona/human trace or outage/denial behavior; local parsing/guards do not satisfy this runtime assertion.

## M07 — Code Mode calls gated source apply

**BLOCKED_EXTERNAL**. Required: Same actual human pause as direct call

Observed scope: Local components may be covered, but connected acceptance was not run.

Pending: Requires actual TrueForge/model/Daytona/human trace or outage/denial behavior; local parsing/guards do not satisfy this runtime assertion.

## M08 — Literal gate configuration survives agent save/reload

**PARTIAL**. Required: Both source apply and cleanup visibly gated

Observed scope: The listed local assertions passed; the missing clause prevents full credit.

Pending: Template and negative literal-gate validation are asserted; actual TrueForge save/reload persistence is not.

- `tests/trueforge/test_config.py::test_config_probe_rejects_removed_literal_gate`
- `tests/trueforge/test_config.py::test_saved_agent_template_preserves_ten_tools_and_two_literal_gates`

## M09 — Annotation missing/wrong in a controlled negative test

**BLOCKED_EXTERNAL**. Required: Literal names still govern the selected tools

Observed scope: No qualifying executed assertion mapped.

Pending: Requires actual TrueForge/model/Daytona/human trace or outage/denial behavior; local parsing/guards do not satisfy this runtime assertion.

## M10 — Engineer denies then later explicitly allows

**BLOCKED_EXTERNAL**. Required: Real denied/no-write and allowed/exact-write observations

Observed scope: Local components may be covered, but connected acceptance was not run.

Pending: Requires actual TrueForge/model/Daytona/human trace or outage/denial behavior; local parsing/guards do not satisfy this runtime assertion.

## M11 — Streaming/progress output

**BLOCKED_EXTERNAL**. Required: Actual states, bounded polling, no invented percentage/time

Observed scope: Local components may be covered, but connected acceptance was not run.

Pending: Requires a real provider, sandbox, cloud, private deployment, recording, or genuine human-gate observation unavailable to this local gate.

## M12 — Source-read tool used after Allow

**BLOCKED_EXTERNAL**. Required: Correct new schema/aggregates and matching execution receipt

Observed scope: Local components may be covered, but connected acceptance was not run.

Pending: Requires actual TrueForge/model/Daytona/human trace or outage/denial behavior; local parsing/guards do not satisfy this runtime assertion.

## N01 — Installed Codex and effective configuration

**PARTIAL**. Required: Record actual version/model/permissions; unsupported fields cause an explicit setup failure, not ignored configuration.

Observed scope: Own turn_context gpt-6-sol/high and actual checkout/permissions observed.

Pending: Actual installed Codex version and unsupported config field failure not tested here.

## N02 — Role model and effort precedence

**PARTIAL**. Required: A task-specific setting is actually effective; a conflicting role file cannot silently override the intended route.

Observed scope: Own effective model/effort matches role policy.

Pending: No intentionally conflicting role/task override observation; other roles actual traces not independently inspected.

## N03 — Independent worker checkouts

**PARTIAL**. Required: Each writer proves its cwd/base SHA/allowed paths; no shared-checkout overlap.

Observed scope: Own isolated checkout branch/base/HEAD and no product ownership writes verified.

Pending: All writers isolation evidence is not established by this one reviewer checkout.

## N04 — Child admission and thread retirement

**PARTIAL**. Required: At most three concurrent child threads; completed threads close; no grandchildren by workflow.

Observed scope: No descendants/delegation in this reviewer; workflow policy limits three child threads.

Pending: No automated admission/retirement test and no complete root thread lifecycle audit here.

## N05 — Goal pause/resume and fresh-session recovery

**NOT_RUN**. Required: Ledger remains correct; no false completion or replayed external mutation.

Observed scope: No qualifying executed assertion mapped.

Pending: No assertion in the executed unit/MCP/TrueForge gate covers the full required behavior.

## N06 — Skill discovery and narrow loading

**PARTIAL**. Required: Four valid frontmatter skills route to existing task docs without loading every specification.

Observed scope: Two narrow skills actually loaded and router paths exist; four entries are cataloged.

Pending: No automated full four-skill frontmatter/task-routing discovery exercise.

## N07 — Inherited connector permissions

**PARTIAL**. Required: Read-only reviewer/DB worker cannot use unrelated privileged MCP tools through inherited access.

Observed scope: Role/skills forbid inherited unrelated connectors; reviewer used none.

Pending: Filesystem read-only is not tool capability isolation; no actual per-connector denial capability demonstrated.

## N08 — Gateway route and model identity

**BLOCKED_EXTERNAL**. Required: Actual adapter/API family/upstream ID/saved model resource are recorded and distinct.

Observed scope: Local components may be covered, but connected acceptance was not run.

Pending: Route schema keeps adapter/API family/model/effort distinct, but actual Gateway route and saved model resource were unavailable.

- `tests/trueforge/test_gateway_probe.py::test_probe_does_not_execute_without_explicit_flag`

## N09 — Astra tool-call API mismatch

**NOT_RUN**. Required: Astra with Chat Completions tools is rejected at setup; no live-run discovery of this known mismatch. This is a setup/configuration rejection test only; V3 does not call Astra as a runtime model.

Observed scope: No qualifying executed assertion mapped.

Pending: No assertion in the executed unit/MCP/TrueForge gate covers the full required behavior.

## N10 — Sol compatible-route reasoning mismatch

**BLOCKED_EXTERNAL**. Required: Sol Chat Completions tools require explicit none; high is not silently sent or represented as working.

Observed scope: Local components may be covered, but connected acceptance was not run.

Pending: Requires a real provider, sandbox, cloud, private deployment, recording, or genuine human-gate observation unavailable to this local gate.

## N11 — Unsupported model parameters

**PARTIAL**. Required: Actual outgoing request omits unsupported sampling/log-probability options; permitted effort verified.

Observed scope: The listed local assertions passed; the missing clause prevents full credit.

Pending: A valid exact Sol/high route is parsed without execution; an actual outgoing request and rejection/omission of every unsupported parameter are not observed.

- `tests/trueforge/test_gateway_probe.py::test_probe_does_not_execute_without_explicit_flag`

## N12 — Streamed tool-call roundtrip

**PARTIAL**. Required: Complete JSON arguments, stable call ID, one harmless execution and linked result produce a continued response.

Observed scope: Component CONNECTED_VERIFIED: lead-held sanitized receipts show native TrueForge through configured Gateway Responses invoking strict read-only get_run and get_source_status, linking tool-call IDs to responses and continuing to turn.done/final text. Local stream-state tests cover complete JSON and stable-ID decoding.

Pending: The sanitized connected receipts do not retain streamed argument fragments for an independent end-to-end recheck of every assembly clause. The inline compatibility sessions are not the saved Daytona-backed product agent, so this scenario remains PARTIAL and T20 remains BLOCKED_EXTERNAL.

- `tests/trueforge/test_gateway_probe.py::test_responses_stream_state_machine`
- `tests/trueforge/test_responses_stream.mjs::decodes one linked streamed status tool call`
- `tests/trueforge/test_responses_stream.mjs::requires a completed continued final text response`
- `evidence/connected/native-compatibility.json (lead-held sanitized receipt)`
- `evidence/connected/native-source-status.json (lead-held sanitized receipt)`

## N13 — Provider auth/quota/timeout failure

**BLOCKED_EXTERNAL**. Required: Errors are visible and bounded; the stored run/SQL candidate are not recreated or replayed.

Observed scope: Local components may be covered, but connected acceptance was not run.

Pending: Missing-route and explicit-execute refusals are bounded; real auth, quota, timeout failures and durable run preservation are not observed.

- `tests/trueforge/test_gateway_probe.py::test_probe_blocks_without_ignored_route_config`
- `tests/trueforge/test_gateway_probe.py::test_probe_does_not_execute_without_explicit_flag`

## N14 — Semantic response cache versus prefix cache

**NOT_RUN**. Required: No cached action response crosses run/candidate/state; harmless prompt-prefix caching is not misclassified.

Observed scope: No qualifying executed assertion mapped.

Pending: No assertion in the executed unit/MCP/TrueForge gate covers the full required behavior.

## N15 — Provider log and export privacy

**BLOCKED_EXTERNAL**. Required: Gateway/OpenAI/Daytona settings and evidence expose no key, connection string or unintended row value.

Observed scope: Local components may be covered, but connected acceptance was not run.

Pending: Probe output omits the configured endpoint; actual Gateway/OpenAI/Daytona logs and exports were not inspected.

- `tests/trueforge/test_gateway_probe.py::test_probe_does_not_execute_without_explicit_flag`

## N16 — SDK OpenTelemetry leakage sentinel

**NOT_RUN**. Required: Automatic spans/log exporters do not transmit secret-bearing inputs/outputs; disabled/default behavior actually checked.

Observed scope: No qualifying executed assertion mapped.

Pending: No assertion in the executed unit/MCP/TrueForge gate covers the full required behavior.

## N17 — MCP v2 and Code Mode result shapes

**PARTIAL**. Required: Official client structured_content and harness bridge wrappers decoded according to their own actual schemas.

Observed scope: The listed local assertions passed; the missing clause prevents full credit.

Pending: Official MCP structured_content and installed client versions are asserted; actual Code Mode bridge wrapper shape is not.

- `tests/mcp/test_transport.py::test_ten_flat_strict_schemas_structured_error_and_no_source_write`
- `tests/trueforge/test_mcp_interop.py::test_trueforge_bundled_js_client_calls_python_mcp_2_2_0`
- `tests/trueforge/test_package.py::test_local_package_probe_reports_resolved_versions`

## N18 — Wire protocol interoperability

**LOCAL_VERIFIED**. Required: Actual TrueForge JS client and Python service negotiate successfully despite different package majors.

Observed scope: All required assertion clauses are covered by the listed tests in the observed 90-test gate.

Pending: None for the mapped local assertion; connected acceptance remains separate.

- `tests/trueforge/test_mcp_interop.py::test_trueforge_bundled_js_client_calls_python_mcp_2_2_0`

## N19 — MCP reconnection after partial delivery

**NOT_RUN**. Required: Business run remains durable; get_run observation is safe; no source SQL retry wrapper.

Observed scope: No qualifying executed assertion mapped.

Pending: No assertion in the executed unit/MCP/TrueForge gate covers the full required behavior.

## N20 — Private transport host/origin policy

**PARTIAL**. Required: Selected SDK deployment rejects disallowed host/origin exposure and remains loopback/private; negative test recorded.

Observed scope: The listed local assertions passed; the missing clause prevents full credit.

Pending: Server is reached on loopback; disallowed Host/Origin negative behavior and private deployment exposure are not asserted.

- `tests/mcp/test_transport.py::test_ten_flat_strict_schemas_structured_error_and_no_source_write`

## N21 — Long SQL/cloud work versus transport health

**LOCAL_VERIFIED**. Required: Health/status stay responsive with bounded jobs; cancellation does not falsely claim rollback.

Observed scope: Held apply-to-clone/source handlers prove typed phase-consistent get_run meets a one-second deadline without retry. The real loopback HTTP MCP/JS SDK ping and get_run remain responsive while the mutation lock is held; terminating client delivery leaves durable MIGRATING rather than falsely claiming rollback.

Pending: None for the mapped local assertion; connected acceptance remains separate.

- `tests/unit/test_remaining_verdict_boundaries.py::test_n21_run_status_remains_responsive_during_long_mutation`
- `tests/unit/test_remaining_verdict_boundaries.py::test_n21_run_status_envelope_uses_same_phase_snapshot`
- `tests/trueforge/test_status_transport_responsiveness.py::test_n21_http_status_remains_typed_and_responsive_while_mutation_lock_is_held`

## N22 — Partial/invalid streamed arguments

**PARTIAL**. Required: Incomplete tool arguments cannot create a candidate, run, write or cleanup operation.

Observed scope: The listed local assertions passed; the missing clause prevents full credit.

Pending: Malformed arguments and changed call identity are rejected by the stream state machine; incomplete delivery is not connected to service-side no-effect assertions.

- `tests/trueforge/test_gateway_probe.py::test_responses_stream_state_machine`
- `tests/trueforge/test_responses_stream.mjs::rejects changed call identity and malformed tool arguments`

## N23 — Wrong RDS CA and hostname

**LOCAL_VERIFIED**. Required: Both fail closed independently; successful TLS is hostname-verified, not encryption-only.

Observed scope: Audited database/policy assertions; final integrated gate supersedes failed worker fixture gate.

Pending: Server-major/TLS mismatch observed; parser-version monkeypatch readiness case not separately covered.

- `tests/postgres/test_database.py::test_tls_hostname_ca_major_and_role`

## N24 — Actual restored storage/encryption/network

**PARTIAL**. Required: Described clone matches approved private storage/KMS/SG settings; magnetic/unsupported configuration fails clearly.

Observed scope: Stubbed restore settings and wrong storage/private/encryption/engine/network negatives.

Pending: Actual restored RDS/KMS/storage/network observations absent.

- `tests/cloud/test_rds.py::test_restore_private_exact_args_then_restart_reconciles`
- `tests/cloud/test_rds.py::test_source_negative_before_tags`
- `tests/cloud/test_storage.py::test_snapshot_magnetic_storage_refused`
- `tests/cloud/test_storage.py::test_unsupported_or_unapproved_storage_refused`

## N25 — Lazy loading and clone timing labels

**PARTIAL**. Required: Available is not asserted warm; observed storage state/timing labels have no invented percent or production projection.

Observed scope: Actual stubbed storage mode retained; available not READY.

Pending: No lazy-loading/storage initialization/warmed scan timing observation on RDS.

- `tests/cloud/test_jobs.py::test_tick_available_is_not_database_ready_and_poll_is_read_only`
- `tests/cloud/test_storage.py::test_source_observation_records_real_mode`

## N26 — Missing trace identifiers

**NOT_RUN**. Required: Unavailable Gateway/AWS/sandbox trace fields stay NOT_OBSERVED; final report identity remains valid.

Observed scope: No qualifying executed assertion mapped.

Pending: No assertion in the executed unit/MCP/TrueForge gate covers the full required behavior.

## N27 — Prompt injection in SQL/comments/tool output

**PARTIAL**. Required: Instruction-like data cannot change checks, model permissions, targets or approval requirements.

Observed scope: The listed local assertions passed; the missing clause prevents full credit.

Pending: SQL comments remain inert and report/tool error strings are escaped or suppressed; model permissions, targets, and actual approval UI behavior are not exercised.

- `tests/cloud/test_rds.py::test_provider_message_sanitized`
- `tests/unit/test_reports.py::test_markdown_escapes_untrusted_content_and_is_deterministic`
- `tests/unit/test_service_privacy.py::test_invalid_argument_sentinel_never_echoed`
- `tests/unit/test_sql_policy.py::test_comments_semicolons_and_protected_update`

## N28 — Report markup injection

**LOCAL_VERIFIED**. Required: Metadata/error strings are escaped; no script/unsafe HTML/credential-bearing generated link in the native report.

Observed scope: All required assertion clauses are covered by the listed tests in the observed 90-test gate.

Pending: None for the mapped local assertion; connected acceptance remains separate.

- `tests/unit/test_reports.py::test_markdown_escapes_untrusted_content_and_is_deterministic`

## N29 — Dependency inventory and public license claims

**PARTIAL**. Required: Version/integrity/notices recorded; pglast GPL metadata not mislabeled MIT; no claim of legal clearance.

Observed scope: The listed local assertions passed; the missing clause prevents full credit.

Pending: Versions, inventory currency, pglast GPL, TrueForge MIT, and project UNDECIDED are asserted; all notice text and absence of legal-clearance claims are not test assertions.

- `tests/trueforge/test_dependency_inventory.py::test_installed_dependency_inventory_is_current`
- `tests/trueforge/test_dependency_inventory.py::test_inventory_records_project_pglast_and_trueforge_license_status`

## N30 — Final organizer requirements and provider fallback

**BLOCKED_EXTERNAL**. Required: Actual final rules recorded; Gateway used or explicit rules-compatible fallback disclosed; coding-start provenance honest.

Observed scope: Local components may be covered, but connected acceptance was not run.

Pending: Requires a real provider, sandbox, cloud, private deployment, recording, or genuine human-gate observation unavailable to this local gate.

## N31 — Recording and public repository privacy

**PARTIAL**. Required: Actual final artifacts reviewed for secrets/row values; publication performed only after authorization.

Observed scope: Distribution path/private/link rejection tests and earlier independently inspected clean archive.

Pending: Final current repository/history/recording/provider exports/publication authorization not reviewed as a whole here.

- `tests/unit/test_distribution.py::test_source_rejects_original_path_before_prefix_removal`
- `tests/unit/test_distribution.py::test_wheel_duplicate_or_link_refused`
- `tests/unit/test_distribution.py::test_wheel_inspects_every_member`

## N32 — Integrated patch evidence differs from worker evidence

**PARTIAL**. Required: Lead reviews allowed paths, merges exact changes and reruns affected integration; worker green alone is not final green.

Observed scope: Lead owns repairs; exact old commit and uncommitted root hashes reviewed independently.

Pending: Affected integrated cloud106 and unit37 independently pass at exact221a79a; no full integrated suite rerun by reviewer and no connected demonstration.

## V01 — Sol-only primary model policy

**PARTIAL**. Required: All 36 primary assignments and normal role defaults use 6 Sol or 5.6 Sol with High; actual runtime role observations agree.

Observed scope: Model-policy/task-index routes and ownSol/high trace agree.

Pending: All36 actual task/model-runtime traces not independently audited in this cloud lane.

## V02 — Automatic Astra or premium promotion

**PARTIAL**. Required: Model unavailability, slow tasks or normal errors do not promote to Astra, Fast, Pro/Ultra, xhigh or max.

Observed scope: No Astra/Fast/Pro/Ultra/xhigh/max promoted in this review; policy denies automatic promotion.

Pending: No unavailability/failure promotion regression exists or was induced.

## V03 — Expert slot admission and exhaustion

**NOT_RUN**. Required: Only unused A1/A2 tickets admit one focused Astra session; a critical investigation consumes a slot; a third requires explicit user extension.

Observed scope: No qualifying executed assertion mapped.

Pending: No assertion in the executed unit/MCP/TrueForge gate covers the full required behavior.

## V04 — Expert review scope and handoff

**NOT_RUN**. Required: Astra returns findings without implementation, delegation, cloud changes or approval clicks; Sol makes and tests repairs.

Observed scope: No qualifying executed assertion mapped.

Pending: No assertion in the executed unit/MCP/TrueForge gate covers the full required behavior.

## V05 — No-change final safety review

**PARTIAL**. Required: Unchanged safety boundary skips another Astra rescan; a material diff is reviewed using an available slot and exact commit.

Observed scope: Bounded independent Sol delta reviews and no Astra rescans used.

Pending: No prior A1/final unchanged-safety decision observation in this lane.

## V06 — Unknown usage or substituted review

**PARTIAL**. Required: No fabricated allowance numbers, savings percentages, Astra identity or performed review; independent Sol substitution is explicit.

Observed scope: Actual model/effort/commands/probes disclosed and connected absence preserved.

Pending: All-project usage/substitution claims and account telemetry not inspected.

## V07 — Unasserted existing value mutation

**LOCAL_VERIFIED**. Required: A valid UPDATE to a supported existing column outside preserve_columns and intended-value requirements cannot PASS.

Observed scope: All required assertion clauses are covered by the listed tests in the observed 90-test gate.

Pending: None for the mapped local assertion; connected acceptance remains separate.

- `tests/postgres/test_database.py::test_good_commits_real_notnull`
- `tests/postgres/test_database.py::test_new_column_null_assertion`
- `tests/postgres/test_database.py::test_unasserted_existing_column_and_explicit_control`
- `tests/postgres/test_database.py::test_wrong_data_committed_then_block`
- `tests/unit/test_sql_policy.py::test_missing_value_assertion`
- `tests/unit/test_verdict.py::test_missing_is_warn_failed_is_block_only_complete_pass`

## V08 — Weak checks do not cover value intent

**LOCAL_VERIFIED**. Required: Row count, no_nulls and uniqueness without supported intended-value coverage yield COVERAGE_INCOMPLETE/WARN for unprotected value updates.

Observed scope: Row-count, no-null, uniqueness and combined weak checks cannot cover unprotected value intent; actual committed SQL remains WARN and cannot acquire the source writer.

Pending: None for the mapped local assertion; connected acceptance remains separate.

- `tests/unit/test_remaining_verdict_boundaries.py::test_v08_weak_checks_cannot_certify_unprotected_value_intent`
- `tests/postgres/test_remaining_transaction_boundaries.py::test_a04_warn_with_passing_weak_checks_refuses_source_writer`

## V09 — Preserved wrong-data failure remains BLOCK

**LOCAL_VERIFIED**. Required: An allowed UPDATE changing a protected value remains executable on the clone and deterministic comparison forces BLOCK.

Observed scope: Audited database/policy assertions; final integrated gate supersedes failed worker fixture gate.

Pending: None for the mapped local assertion; connected acceptance remains separate.

- `tests/postgres/test_database.py::test_good_commits_real_notnull`
- `tests/postgres/test_database.py::test_new_column_null_assertion`
- `tests/postgres/test_database.py::test_unasserted_existing_column_and_explicit_control`
- `tests/postgres/test_database.py::test_wrong_data_committed_then_block`
- `tests/unit/test_sql_policy.py::test_comments_semicolons_and_protected_update`
- `tests/unit/test_verdict.py::test_missing_is_warn_failed_is_block_only_complete_pass`

## V10 — Explicit whole-column intended value

**LOCAL_VERIFIED**. Required: Supported mandatory all_equal plus complete schema/preservation requirements passes only when actual evidence matches.

Observed scope: Audited database/policy assertions; final integrated gate supersedes failed worker fixture gate.

Pending: None for the mapped local assertion; connected acceptance remains separate.

- `tests/postgres/test_database.py::test_good_commits_real_notnull`
- `tests/postgres/test_database.py::test_new_column_null_assertion`
- `tests/postgres/test_database.py::test_unasserted_existing_column_and_explicit_control`
- `tests/postgres/test_database.py::test_wrong_data_committed_then_block`
- `tests/unit/test_sql_policy.py::test_good_write_set`
- `tests/unit/test_verdict.py::test_missing_is_warn_failed_is_block_only_complete_pass`

## V11 — New-column coverage and real NOT NULL

**LOCAL_VERIFIED**. Required: An added column needs expected schema and mandatory value coverage; zero nulls does not substitute for a schema NOT NULL requirement.

Observed scope: Audited database/policy assertions; final integrated gate supersedes failed worker fixture gate.

Pending: None for the mapped local assertion; connected acceptance remains separate.

- `tests/postgres/test_database.py::test_good_commits_real_notnull`
- `tests/postgres/test_database.py::test_new_column_null_assertion`
- `tests/postgres/test_database.py::test_unasserted_existing_column_and_explicit_control`
- `tests/postgres/test_database.py::test_wrong_data_committed_then_block`
- `tests/unit/test_contracts.py::test_fixture_and_ten_schemas`
- `tests/unit/test_sql_policy.py::test_good_write_set`

## V12 — Coverage fail-closed precedence

**LOCAL_VERIFIED**. Required: Known SQL/required-check failure is BLOCK even with a coverage gap; otherwise missing coverage is WARN, never PASS.

Observed scope: All required assertion clauses are covered by the listed tests in the observed 90-test gate.

Pending: None for the mapped local assertion; connected acceptance remains separate.

- `tests/postgres/test_database.py::test_precommit_typed_manifest_fail_closed`
- `tests/unit/test_sql_policy.py::test_missing_value_assertion`
- `tests/unit/test_verdict.py::test_missing_is_warn_failed_is_block_only_complete_pass`

## V13 — Requirement-result identity consistency

**LOCAL_VERIFIED**. Required: Duplicate/unknown/missing result IDs and a model-edited mandatory flag cannot evade the frozen requirement manifest.

Observed scope: All required assertion clauses are covered by the listed tests in the observed unit gate.

Pending: None for the mapped local assertion; connected acceptance remains separate.

- `tests/postgres/test_database.py::test_precommit_typed_manifest_fail_closed`
- `tests/unit/test_audit_contract_boundaries.py::test_v13_unknown_result_and_mandatory_false_cannot_evade_manifest`
- `tests/unit/test_reports.py::test_seal_refuses_an_incomplete_requirement_manifest`
- `tests/unit/test_reports.py::test_seal_refuses_requirement_kind_category_or_role_id_mismatch`
- `tests/unit/test_sql_policy.py::test_missing_value_assertion`
- `tests/unit/test_verdict.py::test_duplicate_manifest_and_results_warn`

## V14 — Consistent multi-read baseline

**LOCAL_VERIFIED**. Required: Within each DB capture, schema/count/hash measurements share the controlled read-only transaction; source and clone snapshots remain separate.

Observed scope: Audited database/policy assertions; final integrated gate supersedes failed worker fixture gate.

Pending: None for the mapped local assertion; connected acceptance remains separate.

- `tests/postgres/test_database.py::test_default_capture_refuses_existing_transaction`
- `tests/postgres/test_database.py::test_repeatable_read_snapshot_survives_concurrent_writer`

## V15 — Offline strict input parser

**LOCAL_VERIFIED**. Required: Invalid UTF-8, duplicate JSON keys, NaN/infinity, excessive size/depth and unsupported versions are rejected without side effects.

Observed scope: All required assertion clauses are covered by the listed tests in the observed unit gate.

Pending: None for the mapped local assertion; connected acceptance remains separate.

- `tests/unit/test_audit_contract_boundaries.py::test_v15_offline_rejects_unsupported_version_and_backend`
- `tests/unit/test_audit_contract_boundaries.py::test_v15_offline_strict_parser_rejects_remaining_invalid_inputs`
- `tests/unit/test_contracts.py::test_canonical_order_and_nonfinite`
- `tests/unit/test_contracts.py::test_no_unknown_contract_or_duplicate_keys`
- `tests/unit/test_reports.py::test_verifier_rejects_duplicate_keys_and_schema_failures`

## V16 — Offline unchanged trusted report

**LOCAL_VERIFIED**. Required: Valid report and separately provided matching digest yield EXPECTED_DIGEST_MATCH while current apply eligibility stays NOT_EVALUATED.

Observed scope: All required assertion clauses are covered by the listed tests in the observed 90-test gate.

Pending: None for the mapped local assertion; connected acceptance remains separate.

- `tests/unit/test_reports.py::test_seal_hashes_payload_only_and_verifier_labels_anchor`

## V17 — Offline payload modified old hash

**LOCAL_VERIFIED**. Required: Changed payload with old report hash fails integrity.

Observed scope: All required assertion clauses are covered by the listed tests in the observed 90-test gate.

Pending: None for the mapped local assertion; connected acceptance remains separate.

- `tests/unit/test_reports.py::test_verifier_detects_old_hash_and_rehashed_anchor_tampering`

## V18 — Offline forged payload with new self-hash

**LOCAL_VERIFIED**. Required: A report modified and rehashed fails against the original independently retained expected digest.

Observed scope: All required assertion clauses are covered by the listed tests in the observed 90-test gate.

Pending: None for the mapped local assertion; connected acceptance remains separate.

- `tests/unit/test_reports.py::test_verifier_detects_old_hash_and_rehashed_anchor_tampering`

## V19 — Offline unanchored report

**LOCAL_VERIFIED**. Required: No trusted expected hash yields SELF_CONSISTENT_UNANCHORED, never authenticated or proof of real AWS execution.

Observed scope: All required assertion clauses are covered by the listed tests in the observed 90-test gate.

Pending: None for the mapped local assertion; connected acceptance remains separate.

- `tests/unit/test_reports.py::test_seal_hashes_payload_only_and_verifier_labels_anchor`

## V20 — Offline historical BLOCK and missing checks

**LOCAL_VERIFIED**. Required: A truthful complete BLOCK artifact verifies as historical BLOCK; forged PASS or missing mandatory results fail semantic verification.

Observed scope: All required assertion clauses are covered by the listed tests in the observed 90-test gate.

Pending: None for the mapped local assertion; connected acceptance remains separate.

- `tests/unit/test_reports.py::test_valid_historical_block_is_verified_as_block`
- `tests/unit/test_reports.py::test_verifier_rejects_missing_results_and_forged_pass`

## V21 — Offline backend and zero network

**LOCAL_VERIFIED**. Required: Verifier preserves backend labels, rejects unknown schema/backend, and runs with no network, AWS/DB credentials or model client.

Observed scope: All required assertion clauses are covered by the listed tests in the observed unit gate.

Pending: None for the mapped local assertion; connected acceptance remains separate.

- `tests/unit/test_audit_contract_boundaries.py::test_v21_offline_preserves_backend_and_calls_no_connected_client`
- `tests/unit/test_reports.py::test_offline_verifier_makes_no_network_call`
- `tests/unit/test_reports.py::test_verifier_rejects_duplicate_keys_and_schema_failures`

## V22 — Review before real source mutation

**BLOCKED_EXTERNAL**. Required: T27 acceptance/critical findings closure precedes T24 live write; mocked/local tests do not impersonate human approval.

Observed scope: Local components may be covered, but connected acceptance was not run.

Pending: Requires a real provider, sandbox, cloud, private deployment, recording, or genuine human-gate observation unavailable to this local gate.

## V23 — Bounded Code Mode cloud observation

**PARTIAL**. Required: Batch limits/backoff/deadline bound polls; pending expiry preserves run and emits a checkpoint, not a new clone or replay.

Observed scope: Service job backoff/deadline/intent tests exist.

Pending: These are service ticks, not actual CodeMode batching/checkpoint execution; no CodeMode test located.

- `tests/cloud/test_jobs.py::test_ambiguous_or_throttled_keep_same_intent`
- `tests/cloud/test_jobs.py::test_tick_available_is_not_database_ready_and_poll_is_read_only`

## V24 — No mutation inside polling loop

**PARTIAL**. Required: Only observation tools run in polling batches; apply/cleanup remain separately visible literal human gates.

Observed scope: Template preserves literal apply/cleanup gates.

Pending: No actual polling batch proves only observation tools and separate visible real approvals; not run here.

- `tests/trueforge/test_config.py::test_saved_agent_template_preserves_ten_tools_and_two_literal_gates`

## V25 — Runtime stays on a tested Sol route

**BLOCKED_EXTERNAL**. Required: 6 Sol/high or tested 5.6 Sol/high; no runtime Astra; compatibility-none route needs explicit operator choice and truthful effort label.

Observed scope: Local components may be covered, but connected acceptance was not run.

Pending: Local config enforces a Sol/high Responses route and explicit execution, but no tested live route exists.

- `tests/trueforge/test_config.py::test_deployment_validation_rejects_placeholder_model`
- `tests/trueforge/test_gateway_probe.py::test_probe_does_not_execute_without_explicit_flag`

## V26 — Trace-based agent evaluation oracle

**BLOCKED_EXTERNAL**. Required: Actual tool/service/receipt evidence grades each behavior case; a model saying it passed cannot mark a case PASS.

Observed scope: Representative agent-evaluation plan remains a specification.

Pending: Requires actual TrueForge/model/Daytona/human trace or outage/denial behavior; local parsing/guards do not satisfy this runtime assertion.

## V27 — Material fixes invalidate stale review assurance

**PARTIAL**. Required: Safety-changing fixes after A1 receive targeted independent Sol recheck before any further live apply; A2 is conditional and does not waive findings.

Observed scope: All cloud findings A01-A07 closed by exact negative repros/tests at221a79a, including mixed conditional grant; material source interface/check/lock changes independently read. NoAstra consumed.

Pending: Local boundary recheck is not accepted connectedT27/human approval. Actual provider/cloud/source apply demonstration remains externally blocked.

## V28 — Nullable intended value semantics

**LOCAL_VERIFIED**. Required: The typed all_equal-to-null check uses explicit null semantics; SQL equality to NULL or vacuous missing-column behavior cannot produce PASS.

Observed scope: Audited database/policy assertions; final integrated gate supersedes failed worker fixture gate.

Pending: None for the mapped local assertion; connected acceptance remains separate.

- `tests/postgres/test_database.py::test_good_commits_real_notnull`
- `tests/postgres/test_database.py::test_new_column_null_assertion`
- `tests/postgres/test_database.py::test_unasserted_existing_column_and_explicit_control`
- `tests/postgres/test_database.py::test_wrong_data_committed_then_block`
- `tests/unit/test_evidence.py::test_type_tags_are_distinct`

## Agent evaluations E01–E10

All ten **NOT_RUN**. Actual saved-agent/tool/service traces are required. Exact requirements: `config/agent-evaluation-plan.json`.
