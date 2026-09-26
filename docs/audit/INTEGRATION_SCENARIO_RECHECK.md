# Integration scenario recheck: N20, N21, N22, N29

This packet records the bounded local recheck requested after the scenario matrix at base
`e200a8a133a389181d52ac9668b09af076c0d73b`. The effective test state is commit
`5739cbdcf5a5dd02be636aca273525700d0b8aac`. The assertions use a loopback transport and SQLite
state. They do not call Gateway, AWS, PostgreSQL, Daytona, or either human-gated tool.

The observed command was:

```text
uv run --locked pytest tests/trueforge/test_remaining_transport_boundaries.py -q
... [100%]
3 passed in 0.86s
```

`uv run --locked ruff check tests/trueforge/test_remaining_transport_boundaries.py` and
`git diff --check` also passed.

## Scenario results

| ID | Local status | Exact assertion and evidence | Remaining connected or packaging assertion |
|---|---|---|---|
| N20 | LOCAL_VERIFIED | `test_n20_loopback_server_rejects_disallowed_host_and_origin` constructs the installed MCP SDK's Streamable HTTP app with the same `127.0.0.1` host used by Preflight. Host `attacker.invalid` receives 421, Origin `https://attacker.invalid` receives 403, the public `serve` wiring passes `host="127.0.0.1"`, and all state tables remain empty. | This proves the selected local SDK and application bind policy. Host firewall/security-group evidence for a deployed machine belongs to its connected deployment record. |
| N21 | HANDOFF; matrix remains PARTIAL pending the owning fix | The DB lane found that the real service path can serialize `get_run` behind the per-run call lock. A first test-double approach in this lane delayed the call before that production lock, so it was removed and is not evidence. | The root and DB owner are moving `get_run` to its correct read-only path and adding a real SQLite service regression. Their result, rather than a duplicate transport stub, must determine N21. |
| N22 | PARTIAL | `test_n22_incomplete_stream_and_partial_mutation_arguments_have_no_effect` proves the Responses probe decoder rejects completed delivery containing partial JSON with `TOOL_ARGUMENTS_INVALID`. It then submits partial inputs to every mutating business method and observes `INVALID_INPUT` with no changes to records, runs, events, idempotency rows, or apply attempts. | The probe decoder and service refusal are separate local boundaries. A real TrueForge interrupted business-tool stream that demonstrably never invokes MCP is still not observed, so this is not upgraded to LOCAL_VERIFIED. |
| N29 | PARTIAL | `test_n29_inventory_notices_and_public_claims_remain_qualified` checks every component has a version, every npm component has integrity, both lock digests are present, pglast remains `GPL-3.0-or-later`, TrueForge remains MIT, and the project remains `UNDECIDED`. It asserts the notice's preservation/review qualifications and the public documentation's explicit statement that the inventory is not legal clearance. | The repository does not contain a hashed, exhaustive copy of every upstream notice body for all 414 installed components. Metadata and public claims are verified; exhaustive redistribution-notice completeness still needs the final license review. |

## Connected evidence separation

The lead owns the real native Gateway and MCP compatibility evidence for `get_run` and
`get_source_status`; it was not replayed or copied into these local tests. Daytona remains
`BLOCKED_EXTERNAL` until authorized credentials and quota are available. None of those facts
changes the local classifications above, and this packet makes no saved-agent, Code Mode, RDS,
approval, or source-write claim.
