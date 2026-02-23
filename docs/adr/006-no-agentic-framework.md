# ADR-006: Hand-Rolled Agent Over Agentic Frameworks

**Status:** Accepted
**Date:** 2026-02-22
**Context:** Evaluated whether to adopt an agentic framework (Claude Agent SDK, LangGraph, CrewAI, AutoGen) for the patient interview and SOAP generation pipelines.

## Decision

Keep the hand-rolled state-machine agent (`PatientInterviewAgent`) and direct LLM calls. Do not adopt an agentic framework.

### Alternatives Considered

| Framework | Strength | Why rejected |
|-----------|----------|-------------|
| Claude Agent SDK | Tool use, structured output | Interview is a fixed checklist, not open-ended tool selection |
| LangGraph | Stateful multi-step workflows | State machine is simpler and more predictable for a fixed flow |
| CrewAI | Multi-agent coordination | Only one agent exists; no multi-agent need |
| LlamaIndex | RAG pipeline orchestration | RAG pipeline is only 2 steps (embed + search); framework is overkill |
| AutoGen | Multi-agent conversation | Not applicable to patient-facing voice interface |

### Rationale

1. **Medical safety demands predictability.** The interview follows a rigid stage progression (GREETING -> INTERVIEW -> IMAGE_CONSENT -> IMAGE_CAPTURE -> SOAP). An agentic loop that lets the LLM decide next steps introduces unpredictability in a safety-critical context where the system must never skip consent, miss escalation, or go off-script.

2. **Voice latency is critical.** Patients interact via voice in real-time. Every added layer (tool dispatch, output parsing, retry logic, chain-of-thought) increases response time. The current pattern (STT -> one LLM call -> TTS) minimizes latency. Agentic frameworks add overhead per step that degrades the conversational experience.

3. **The workflow is not dynamic.** Agentic frameworks excel when the task requires planning: choosing tools, deciding order, handling open-ended problems. This interview is a fixed 5-topic checklist with deterministic transitions. A state machine is the correct abstraction.

4. **Auditability for medical compliance.** The current code is straightforward to audit: each stage has explicit logic, prompts are traceable, escalation keywords are enumerated. Frameworks add indirection (chains, callbacks, middleware) that makes safety review harder.

5. **Minimal tool orchestration.** The system calls two tools: the medical model and the RAG retriever. There is no dynamic tool selection. Wrapping two direct calls in a framework adds complexity without benefit.

## Consequences

### Positive

- Simple, auditable code path from patient utterance to agent response
- Minimal latency for voice conversations (~200ms LLM call, no framework overhead)
- Easy to reason about safety properties (escalation always checked, consent always gated)
- No external framework dependency to track, upgrade, or debug
- State transitions are explicit and testable

### Negative

- If the interview becomes multi-specialty (cardiology, ophthalmology, etc.), the manual state machine will need refactoring
- No built-in observability (tracing, token counting) that frameworks provide out of the box — mitigated by existing structlog instrumentation
- Structured output parsing is manual — mitigated by the medical model protocol abstraction

### Neutral

- The decision does not prevent future adoption; the `PatientInterviewAgent` could be wrapped in a framework later if requirements change
- The protocol-based model abstraction (`src/models/protocols/`) already provides the same interface boundary that a framework would

## Reassess When

- The system needs to dynamically select between multiple interview protocols based on patient symptoms
- A doctor-facing AI assistant is added that requires open-ended reasoning over case histories
- The LLM needs to autonomously decide which tools to invoke (e.g., "should I run image analysis or ask more questions?")
- Multi-agent coordination becomes necessary (e.g., triage agent + specialist agent)
