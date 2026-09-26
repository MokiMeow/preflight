# Preflight hackathon walkthrough — 2:58 master script

Target runtime: **178 seconds**. The browser recording remains at 1920×1080 and shows the native TrueForge UI continuously from 0:15 through 0:55. Historical approval actions are labeled as recorded evidence; they are not recreated for the camera. No credentials, private endpoints, raw rows or SQL text appear.

## Timed recording plan

| Time | Show | Narration |
|---|---|---|
| 0:00–0:15 | Title, one-line architecture, then the saved `preflight` TrueForge agent | “A database migration can execute successfully and still change the wrong data. Preflight rehearses the exact SQL artifact on a private snapshot-restored RDS clone, verifies the result deterministically, and keeps the owned synthetic source behind explicit approval.” |
| 0:15–0:55 | **Live native TrueForge UI.** The edited excerpt sends one read-only `get_run` request for run `7f1a627e-a6d0-4c9f-a5ce-58984b38d41e`, request `30366339-0a39-4a74-9c81-a4a1cd9eb380`. It shows `APPLIED`, cleanup `RETAINED_RECOVERY`, and another source apply ineligible. No `get_report` or Code Mode execution occurs in this excerpt. | “This is the saved TrueForge product agent on the verified Gateway route. The edited live excerpt makes one read-only run-status request. Bounded isolation canaries passed during prior connected verification. Here the service reports source APPLIED, recovery retained, and another apply ineligible. The service owns those facts; the model explains them, but it cannot redefine PASS, BLOCK or approval.” |
| 0:55–1:25 | Recorded connected rehearsal: bad candidate transaction, BLOCK report, corrected candidate transaction, PASS report | “Here is the completed connected rehearsal on the disposable clone. The 68-byte bad candidate rolled back with SQLSTATE 23502; the baseline stayed unchanged and the sealed verdict was BLOCK. A separately registered 183-byte corrected artifact committed. All 18 mandatory checks passed, including complete preservation and intended-change coverage. Its trusted report digest begins 6e0690.” |
| 1:25–1:55 | Recorded TrueForge source gate: Deny event and no-change verification, then the later fresh Allow request and APPLIED receipt | “These are historical human decisions captured in TrueForge. The first source request was denied, and the read-only check confirmed 1,000 rows and three columns: no source change. A later fresh request targeted the same reviewed candidate and report. After Allow, fresh server guards matched and the transaction committed once in 130 milliseconds. The source then had 1,000 rows, four columns, and zero intended-value violations.” |
| 1:55–2:20 | Recorded fresh replay request and its refusal | “Approval is not a reusable token. A new approved request tried to repeat the same source apply. Before SQL ran, the service returned SOURCE_APPLY_REPLAY_REJECTED, marked it non-retryable, and preserved the already applied state. Unknown outcomes are also never retried automatically.” |
| 2:20–2:43 | Recorded cleanup gate and final AWS observation | “Cleanup has its own human gate. The approved action deleted only the run-owned clone and explicitly retained the pre-apply recovery snapshot. The final AWS observation found the clone absent and the encrypted, run-tagged snapshot available. The source and host remain active; this is deliberate clone-only cleanup, not broad teardown.” |
| 2:43–2:58 | Final proof card: source APPLIED, replay refused, clone ABSENT, snapshot AVAILABLE, local regression result | “The source is APPLIED, replay is refused, the clone is absent, and recovery evidence is retained. The local gate also passed 668 tests with no failures, errors or skips. This proves the recorded owned-synthetic run; it does not claim every environment or every remaining adversarial scenario.” |

## Capture rules

- Keep the native TrueForge UI visible for the full 40-second 0:15–0:55 segment.
- The live segment is the successful `get_run` excerpt described above. It does not show report retrieval or Code Mode execution.
- Before that excerpt, two preliminary read-only source queries omitted required fields and were rejected. A third full-schema read-only query verified 1,000 rows and four columns. These setup corrections are omitted from the 40-second edit but remain in the raw capture; the edit does not represent them as successful calls.
- Do not create a run, apply SQL, request cleanup, or recreate approval events for the recording.
- Present Deny, Allow, replay refusal and cleanup as **recorded completed evidence**. The historical approval records show that the coding agent clicked no gate.
- Show only short identifiers or sanitized evidence panels. Never show credentials, connection strings, private endpoints, raw rows, SQL comments, provider settings or browser storage.
- Do not claim all project scenarios complete. The closing sentence is the required scope limitation.

## Evidence anchors used by this script

- Run: `7f1a627e-a6d0-4c9f-a5ce-58984b38d41e`
- Live read-only request: `30366339-0a39-4a74-9c81-a4a1cd9eb380`; result `APPLIED`; cleanup `RETAINED_RECOVERY`; another apply ineligible
- Bad candidate: `d77e7d74-7b9f-47fa-af03-5fc64cdc50d8`; rollback; SQLSTATE `23502`; report `c6332b9c…`; verdict `BLOCK`
- Corrected candidate: `a09bf95e-30e3-4bd2-95e9-f62fa2551be7`; 183 bytes; report `6e069069…`; verdict `PASS`; 18 mandatory checks
- Source receipt: `375f73b2-f60f-418a-9061-ed03d3019f9d`; committed once; 130 ms; precheck `MATCH`
- Replay result: `SOURCE_APPLY_REPLAY_REJECTED`; retryable `false`
- Cleanup receipt: `5767be8c-b435-4edb-84aa-63990d936111`; clone-only deletion; snapshot retained
- Final resources: clone `ABSENT`; encrypted owned run-matching snapshot `available`; cleanup `RETAINED_RECOVERY`
- Local regression: 668 passed; zero failures, errors or skips; 248.38 seconds at revision `5c2a56d`
