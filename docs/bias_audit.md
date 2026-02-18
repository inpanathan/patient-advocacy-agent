# Bias Audit Report

**Patient Advocacy Agent — Fairness Assessment**
**Date:** 2026-02-18

## 1. Scope

Assessment of equitable treatment across Fitzpatrick skin types (I-VI),
supported languages, and escalation/de-escalation decisions.

## 2. Fitzpatrick Type Equity

| Check | Status | Notes |
|---|---|---|
| All 6 types representable in schema | PASS | FitzpatrickType enum has I-VI |
| Records valid for all types | PASS | SCIN records created for each |
| Equal embedding dimensions | PASS | Same 768-dim vector for all types |
| RAG retrieval includes all types | PASS | Index returns results from all types |
| SOAP generated for all types | PASS | All 4 sections populated regardless of type |

## 3. Language Equity

| Language | Greeting | Interview | Language Detection |
|---|---|---|---|
| English (en) | PASS | PASS | PASS |
| Hindi (hi) | PASS | PASS | PASS |
| Tamil (ta) | PASS | PASS | PASS |
| Telugu (te) | PASS | PASS | PASS |
| Bengali (bn) | PASS | PASS | PASS |
| Kannada (kn) | PASS | PASS | PASS |

## 4. Escalation Fairness

| Check | Status | Notes |
|---|---|---|
| Escalation triggers for all Fitzpatrick types | PASS | Keywords apply uniformly |
| No demographic-based escalation | PASS | Only medical keywords trigger |
| Benign conditions don't escalate | PASS | Eczema, dermatitis pass cleanly |
| De-escalation consistent | PASS | Paint, tattoo, henna all de-escalate |

## 5. Known Limitations

1. **Mock model bias**: Current mock model returns identical SOAP notes regardless of
   skin type. Real MedGemma may exhibit different behavior — requires re-audit after
   production model integration.

2. **Language quality**: STT/TTS quality may vary by language in production. Requires
   real-world testing with native speakers.

3. **Geographic context**: Current tests don't cover geographic-specific conditions.
   Needs expansion for tropical/subtropical dermatological presentations.

## 6. Recommendations

1. Re-run bias audit after integrating production MedGemma model
2. Add per-Fitzpatrick-type confidence score tracking in production metrics
3. Monitor escalation rate by language in production dashboards
4. Expand test dataset with real patient scenarios across geographies
