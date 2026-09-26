# 07 — Native experience, demonstration and submission

## Positioning

**Name:** Preflight. **One-line promise:** “Rehearse the migration. Review the evidence. Approve the exact change.”

Opening explanation: “A migration can execute successfully and still change the wrong data. Preflight restores an isolated copy of our database, rehearses the exact SQL, checks what actually changed, and waits for an engineer before it can touch the source.” This is a statement of intended/implemented behavior, not an unsupported claim that the approach is unique or that outages have been eliminated.

The original PRD's main story is preserved: bad NOT NULL migration, corrected backfill migration, proof over 1,000 synthetic rows, denial, then an explicitly approved write. The extra wrong-data/drift cases make the validator credible. Keep the architecture comprehensible rather than displaying a cloud of decorative agents.

## 1. Presentation inside TrueForge, not a second app

Use TrueForge's existing chat, tool trace, approval panel and Markdown rendering. Improve the report and the agent's narration; don't spend the build creating another dashboard that hides the real gate. Verify what the installed UI can actually render before claiming custom components, downloadable attachments or expandable chips.

Recommended report order:

```text
PREFLIGHT — REHEARSAL PASSED / BLOCKED / INCOMPLETE
Current lifecycle: Awaiting approval / Not eligible / Applied / Needs attention

Target + exact candidate       source ID, database, candidate ID
Rehearsal provenance           snapshot ID, separate clone ID, captured timestamp
Artifact identity              migration SHA-256, contract SHA-256, report SHA-256

Check                            Before          After          Result
Customer rows                    1000            1000           PASS
Missing / extra primary keys     —               0 / 0          PASS
Changed protected rows           —               0              PASS
account_tier schema              absent          text NOT NULL  PASS
account_tier NULL count           absent          0              PASS
account_tier expected values      absent          all standard   PASS

Measured clone runtime          actual observed number, never a fixture constant
Recovery snapshot               actual available / unavailable state
Untested risks                  traffic, contention, application compatibility,
                                later drift, production performance
Next action                     Review before requesting the human apply gate
```

This is a **layout example**, not actual evidence. Before registration/validation no green state is displayed. A failure report keeps failed/not_run checks visible. Current source/apply state is a separate view or receipt; the immutable PASS report is not rewritten after apply.

Use restrained headings, compact tables, full terms and readable text. Show short hash prefixes in narration only when the full values remain available in the verified report/tool arguments. Never compare truncated hashes for security. Do not use a green checkmark for an unmeasured risk, a denied apply or a pending restore.

Language rules: “rehearsal passed” rather than “production safe”; “snapshot restore still pending” rather than a made-up percentage; “source apply denied; source unchanged” rather than “rollback succeeded”; “commit outcome unknown; do not retry” rather than “probably fine.”

## 2. Fixture specification

Create these files **during the allowed build**; the actual application/fixtures are not bundled as executed code in this starter.

The seed contains 1,000 reproducible rows in `public.customers`: integer primary-key `id`, synthetic `email` text and fixed UTC `created_at` timestamptz. Populate all rows explicitly; avoid unsupported generated/default expressions in this bounded fixture. An optional ordinary unique index on email is compatible with the single-row wrong-data case below. No external integrations, unreviewed triggers or real customer data.

Main bad candidate:

```sql
ALTER TABLE public.customers ADD COLUMN account_tier text NOT NULL;
```

Main good candidate:

```sql
ALTER TABLE public.customers ADD COLUMN account_tier text;
UPDATE public.customers SET account_tier = 'standard' WHERE account_tier IS NULL;
ALTER TABLE public.customers ALTER COLUMN account_tier SET NOT NULL;
```

Extra committed-but-wrong candidate, exercised on its own disposable baseline:

```sql
ALTER TABLE public.customers ADD COLUMN account_tier text;
UPDATE public.customers SET account_tier = 'standard' WHERE account_tier IS NULL;
ALTER TABLE public.customers ALTER COLUMN account_tier SET NOT NULL;
UPDATE public.customers SET email = 'changed@example.invalid' WHERE id = 1;
```

The last candidate can commit but changes one preserved row, so it must BLOCK. The synthetic email value is a declared migration literal, not a returned customer row. Its clone is dirty after the successful transaction; do not reuse it for good.sql as though rollback had occurred. Start a fresh disposable test/rehearsal. Main bad-to-good can reuse its clone only after confirmed rollback and unchanged baseline.

Use the same complete version-1.1 contract for the main bad/good pair. A changed acceptance contract requires a new rehearsal, preventing stale baseline maps or weaker checks from being substituted into an existing run. Snapshot restores are not assumed to finish during a short pitch; start the real job during the event and show its trace/time honestly.

## 3. Demonstration script

The following is a rehearsal format, **not an independently verified official pitch duration**. Adapt its pacing to the organizer's actual slot without dropping the causal proof.

| Beat | What the operator does | What the judge should see |
|---|---|---|
| Establish the real system | Show source ID and current schema; explain synthetic ownership | `account_tier` absent; no real customer data exposed |
| Establish the real copy | Show recorded agent start, snapshot, separate private clone and actual status | Matching AWS IDs/tags/time, not a fake progress screen |
| Catch the failure | Ask Preflight to rehearse the bad payload | Real PostgreSQL failure, BLOCK report, source unchanged |
| Register the correction | Authorize the pre-supplied good payload | New SQL hash; prior failure report retained; rollback/baseline proof before reuse |
| Prove correctness | Execute/validate good candidate | 1,000 rows retained, unchanged keys/protected hashes, new text NOT NULL column, no nulls and expected values |
| Prove human control | Request apply; engineer selects Deny | Actual gate, no source writer call, no schema change |
| Perform the approved action | Explicitly request again; engineer selects Allow | Same exact candidate/report target, fresh guards, source transaction and receipt |
| Verify and conclude | Read source status and show report/receipt link | New column present only after allowed apply; replay refused; recovery snapshot retained |

Narration example at the failure: “This migration is syntactically allowed, but the populated clone rejects it. The source has not changed. Preflight is reporting an observed database failure, not guessing from the SQL.”

Narration example at the gate: “The rehearsal result is tied to these exact SQL and report hashes. Even after a PASS, the agent cannot apply through this workflow without the human decision, and the service will still refuse stale data or changed artifacts.”

Narration example at the end: “We showed a real restore, a real blocked migration, preserved rows and a real approved write. This proves the rehearsed change against this snapshot; it does not prove production traffic or zero downtime.”

## 4. Strong expansion proof

Show the committed-but-wrong-data test report to answer “why not simply run SQL on a test DB?” One changed protected row produces BLOCK despite SQL success. Show the source-drift and replay-refusal results to answer “what prevents an old approval from applying the wrong thing?” Label backend and date: an executed local PostgreSQL adversarial test is useful evidence but must not be described as an AWS live run.

A judge asking for a fresh source apply after the main one has already completed needs a new explicitly prepared synthetic baseline/run. Do not click the same button and hope it reruns, secretly reset the source, or present a stale report as new. The replay refusal itself is a feature worth showing.

## 5. Judge questions and defensible answers

| Question | Answer to demonstrate |
|---|---|
| “Is this just a chatbot around SQL?” | The agent executes a real AWS restore and sequences sandboxed tool calls; the service measures row/schema changes and enforces a real approval boundary. Show the trace. |
| “Why use a model?” | It interprets the requested migration, proposes check coverage, writes bounded orchestration code and explains outcomes. Deterministic code owns correctness and permissions. |
| “Why not just an empty test database?” | The clone contains the populated snapshot state, so constraints/data changes are exercised against actual synthetic rows. Show bad.sql failure. |
| “What happens if SQL succeeds but is wrong?” | The protected-data/schema checks still block. Show the wrong-data test. |
| “Can production change after rehearsal?” | Yes. This static-demo version freshly compares full existing data/schema under locks and refuses drift. It does not solve general online production migration safety. |
| “Can it retry after a crash?” | It can reconcile infrastructure. A source commit with unknown outcome is never automatically replayed. Show durable intent/recovery tests. |
| “Is approval enterprise-secure?” | It is a real private TrueForge UI gate plus service checks. Production needs authenticated, server-verifiable, single-use authorization; this demo does not claim that. |
| “Can you undo the successful migration instantly?” | No. Failed supported transactions roll back; successful data changes may need restore and traffic cutover. Recovery snapshots are retained. |
| “Why RDS and TrueForge local sandbox both?” | RDS holds the database clone; TrueForge local sandbox runs generated agent code. They are separate boundaries and secrets never go to TrueForge local sandbox. |
| “What is production-ready today?” | The evidence shown is the owned synthetic controlled demo. Customer-data use needs additional authorization, identity, concurrency, drift, recovery and security work. |

Do not invent a competitor benchmark or market percentage in answers. Make any future enterprise feature clearly future, not a checkbox the hackathon already delivered.

## 6. Contingency without a fake demo

If restore is pending, display the actual persisted state and earlier real trace. Show live read-only resource/status checks and the local validator tests with explicit backend labels; finish live clone actions only once it is ready. If venue network/provider access fails, use the recorded real walkthrough labeled with its original time/run IDs. Never relabel a recording as live or locally simulated resources as AWS.

Record a complete real run during the event before final submission and inspect it for secrets. The recording is evidence and contingency, not a substitute for implementing the required integrations. A screenshot or JSON fixture is not an acceptable stand-in for an action that never happened.

## 7. Submission README specification

The implementation README should contain: project name/one-line purpose; problem statement and actual event URL; architecture and separate sandbox roles; exact tested versions; prerequisites with secret handling; authorized AWS setup; local development/test commands; private deployment/SSH access; candidate intake and fixture instructions; complete bad/good/gate flow; report/receipt semantics; approval and production limitations; actual test/evidence results; resource cleanup/retention; AI-assistant disclosure; team/contribution details actually supplied by the team.

The AI disclosure should say what tools were used for **planning**, **implementation**, **review**, **testing assistance** and the **runtime product**. Use actual tools/models observed, not marketing names assumed from a subscription. A truthful template is:

> Planning used ChatGPT with the team's supplied PRD and current documentation research. Implementation and review used the coding assistants listed below. The runtime product uses the configured OpenAI model through TrueForge. The team reviewed changes and recorded the commands and integration checks actually performed.

Replace the implementation list with reality. This starter's source document is kept in `reference/Preflight-PRD.md`; explain the numbered amendments. Do not claim all code was handwritten or that AI use was absent.

Inspect the organizer's actual submission form for repository visibility, video link, presentation format and deadlines. Prepare the package but do not push to an unapproved public remote. Exclude local operator JSON, provider configs with keys, state databases, credentials, private SSH keys, raw logs and unreviewed video exports. Include source, dependency locks, config examples, tests and selected sanitized evidence.

## 8. Final handoff card

Before judging, the lead records: current source schema, which run/candidate is staged, whether the source was already applied, clone/snapshot readiness, immutable report hashes, where the real Deny/Allow recording is, the exact next safe action, and the human approver. If a fresh source reset is needed, it is an explicit synthetic setup action outside the recorded no-write interval.

After judging, retain or remove each resource deliberately. Snapshot retention is a recovery choice with a cost owner. Cleanup completion is an observed state, not a closing sentence. Keep the reports and receipts even after the clone disappears.


## 9. Published rubric mapped to inspectable evidence

The indexed official organizer page publishes the weights below; final instructions control. This is an evidence mapping, not a self-awarded score or promise of placement. Source: [08](08_RESEARCH.md), S03.

| Published dimension | Weight | What our demonstration must let judges inspect |
|---|---:|---|
| Harness doing real work | 30 | TrueForge session, meaningful generated TrueForge local sandbox program, real MCP calls and pending approval. |
| Actually runs | 25 | Actual source/snapshot/private clone IDs; bad/good reports; approved source result and reproducible repository. |
| Knows where to stop | 20 | Deny means no write; missing evidence cannot pass; drift/unknown outcomes halt mutation; cleanup is separately controlled. |
| Worthwhile job | 15 | A populated database migration whose SQL can fail—or succeed while corrupting protected values—and the engineer's decision before source apply. |
| Demo clarity | 10 | A readable evidence chain, short plain-language explanation, actual limitations and a coherent five-minute narrative. |

## 10. Five-minute stage cut

**0:00–0:35:** State the problem: “A migration can execute and still damage the data you intended to preserve. Preflight rehearses it and shows evidence before an engineer allows the source write.” Show the team-owned source and exact candidate hash.

**0:35–1:15:** Show the genuine snapshot/clone provenance and the TrueForge/TrueForge local sandbox/MCP trace. A restore may have completed earlier; say so rather than implying a full RDS restore fits inside the pitch.

**1:15–2:10:** Show the bad candidate's actual failure/BLOCK and unchanged source. Introduce the corrected candidate hash. Explain why a changed candidate is a new artifact, not an invisible model rewrite.

**2:10–3:05:** Show the actual passing schema and row evidence. Use the wrong-data case as a short adjacent proof that SQL success alone is insufficient; it may be a clearly labeled recorded run. Show report provenance and untested concurrency limits.

**3:05–4:10:** Trigger the real approval pause. The designated human demonstrates Deny, then requests again and explicitly allows the exact eligible action when appropriate. Browser automation must not click for them. Check the source and receipt after the real approved transaction. Do not repeat an already-applied migration simply to restage the screen.

**4:10–5:00:** Show the evidence-chain/report, verified final state, explicit retained recovery resource and why production concurrency/identity would need further work. Close on the engineer's informed decision, not a fabricated “zero risk” or “exactly once under every failure” claim.

Prepare a separate clean owned synthetic source/run only when the operator has explicitly authorized it. D28 authorizes the planned live AWS result without a numeric ceiling, while singleton resource limits and exact-source controls remain. Otherwise use the existing current state plus clearly labeled recorded approval evidence; do not hide a reset. The pitch's timing is a script, not a guaranteed cloud-operation duration.

## 11. Explainability and submission completeness

Every team member should be able to explain: why a clone is separate from TrueForge local sandbox; what evidence actually determines PASS; why source drift is rechecked inside locks; what an immutable report hash covers; why lost commit acknowledgement cannot be retried; and where the human gate ends and the service guard begins. The Gateway/API protocol choice should also be explainable without exposing configuration secrets.

The README identifies the actual tested coding assistants/models and runtime provider/model/API route separately. Include setup, architecture, local tests, connected tests, reproduction evidence, limitations, dependency notices, private deployment instructions and deliberate retention/cleanup state. Public repository visibility must be explicitly authorized. A draft community post may link the final public repository after approval; do not auto-post, inflate usage statistics or state that judges endorsed the product.


## 12. V3 product-strengthening proof and market framing

### What to claim, and what not to claim

Preflight's differentiation is the **observed workflow**, not the invention of migration tests. [Atlas migration testing](https://atlasgo.io/testing/migrate) already executes migrations and assertions against a development database. [Flyway's dry-run tutorial](https://documentation.red-gate.com/flyway/reference/tutorials/tutorial-dry-runs), updated 24 September 2026, describes a read-only assessment that emits the SQL proposed for review. Those documented capabilities are useful baselines; this is not an exhaustive competitive benchmark or a claim those products cannot be extended.

| Evidence in our project | Judge-visible meaning | Boundary to state |
|---|---|---|
| Real snapshot and distinct private RDS clone | An agent performed actual infrastructure work, not a SQL-looking chat answer | A prepared restore is labeled; clone storage and runtime do not prove production downtime |
| Exact bytes, protected values and schema evidence | A runnable migration can still be wrong; original data is checked, not just row counts | Supported SQL/types/tables and scan limits remain explicit |
| Column coverage table | Intended value changes need a defined acceptance rule | Conditional/general transformations beyond supported rules remain WARN |
| Genuine Deny then deliberate Allow | The engineer retains final control over the same identified operation | Private UI gate is not enterprise authenticated approval proof |
| Known/unknown outcome handling and replay refusal | A dropped connection cannot silently execute SQL twice | Unknown outcomes require investigation, not an inferred rollback |
| Offline verifier against a separately kept digest | The report being inspected matches retained historical evidence | A self-hash alone does not authenticate the creator or current source state |

Suggested pitch sentence: **“Preflight rehearses your exact migration on an isolated RDS copy, checks what happened to the schema and protected values, and stops for your decision before touching the source.”** Do not say the project prevents all outages, guarantees zero downtime, provides a certified production release, or is the first tool to test data migrations. No invented savings, market-size figures or estimated judging points.

### The proof order

Use the existing five-minute cut as the default. Show the owned source and a traceable real restore, the failed migration, the explicitly corrected candidate, complete evidence, human denial, deliberate human approval and final outcome. Prepare these transitions with the actual run state, not another unannounced source reset. Move a brief committed-wrong-data or missing-coverage example into the stage cut only if the real format leaves room; otherwise it is a judge-question proof. The full implementation still includes it.

When showing the report, make **expected / observed / missing** readable as text and not just color. Keep a single comparison table inside the existing TrueForge presentation, evidence hashes available at normal readable size, and the approval clearly distinct from rehearsal success. No decorative nested dashboard, arbitrary “risk score,” percentage confidence or unearned green badge. Any accessibility/keyboard test of an approval control must leave the actual decision to the human.

For the offline-verification beat, retain the original report digest separately in a trusted demonstration note or already exported trace. Run the verifier on the genuine artifact, then on a local copied artifact that was edited/rehashed, using the same original expected digest. Do not mutate the live sealed report or ask the LLM to supply the trusted hash. Demonstrate integrity, not cryptographic proof of human approval.

### Rehearsal preparation that does not falsify execution

Before the stage: verify the exact integrated commit, source state, retained backup, clone identity, provider/TrueForge local sandbox access, runtime model and the prepared session. T27 must have preceded the first live source apply. Keep a genuinely recorded fallback of the same integration, with time/backend labels. Do not claim a recorded restore happened live. Keep a non-mutating read-only readiness command and the standalone report verifier ready for questions.

The engineer should be able to explain four distinctions without reading a model transcript: clone execution versus source execution; coverage versus correctness; artifact consistency versus trusted provenance; and confirmed rollback versus unknown commit. These are the substantive engineering decisions the demo is meant to make visible.

Operator amendment D26 replaces the original Daytona runtime with the installed native local Linux sandbox; historical upstream research and the immutable PRD retain their original scope. D28 supersedes D27's USD100 ceiling and authorizes the planned live AWS result without a numeric maximum. Singleton resource limits, exact-source controls and both literal human gates remain.
