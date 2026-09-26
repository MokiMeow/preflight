---
name: preflight-integration
description: Connect or debug Preflight MCP, TrueForge, AI Gateway, OpenAI tooling, Daytona or native reports.
---

# preflight-integration

Read the task-relevant sections of [05](../../../docs/05_TRUEFORGE_AGENT.md) · [01](../../../docs/01_ARCHITECTURE.md). Paths are relative to this skill file.

Probe the actual model API route before integrating: Astra needs Responses for tool calls; Sol reasoning tools also use Responses. TrueForge's compatible-provider path is not its OpenAI Responses adapter. Verify current installed schemas and wire-level interoperability, not SDK-major numerology. Exercise a harmless tool roundtrip before any product mutation; retain literal approvals on direct and Code Mode calls. Keep runtime secrets outside sandbox and config exports. No second frontend.

Do not load the other skills or the whole PRD unless the assignment crosses their boundary. Use `docs/09_BUILD_STATUS.md` only for current handoff context.

Use the assigned GPT-5.6 Sol/high builder lane and a tested Sol/high runtime. No runtime Astra. Implement the offline verifier using docs 02 section 12; unanchored self-consistency is not authenticity.
