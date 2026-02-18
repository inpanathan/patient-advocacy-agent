# ADR-004: MedGemma for SOAP Generation and ICD Coding

**Status:** Accepted
**Date:** 2026-02-18
**Context:** Need a medical LLM for structured SOAP note generation with ICD code suggestions.

## Decision
Use MedGemma (Google's medical LLM) for SOAP note generation, ICD-10 coding, and patient-facing explanations. All outputs include mandatory disclaimers.

## Consequences
- Requires API access and GPU for production
- Mock implementation enables full development workflow
- Temperature kept low (0.3) for consistent medical outputs
- Never prescribes medication — only recommends seeking care
- Always includes "not a medical diagnosis" disclaimer
