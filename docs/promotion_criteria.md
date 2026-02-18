# Promotion Criteria

**Required tests and thresholds for staging -> production promotion.**

## Gate 1: Code Quality (CI)

All must pass on every commit:

| Check | Tool | Threshold |
|---|---|---|
| Linting | `ruff check` | 0 errors |
| Type checking | `mypy --strict=false` | 0 errors |
| Unit tests | `pytest tests/unit/` | 100% pass |
| Integration tests | `pytest tests/integration/` | 100% pass |

## Gate 2: Model Quality (Nightly)

| Metric | Threshold | Test |
|---|---|---|
| Embedding dimension | >= 32 | `test_model_eval::TestEmbeddingQuality` |
| Embedding normalization | L2 norm within 0.01 of 1.0 | `test_model_eval::TestEmbeddingQuality` |
| Isotropy score | >= 0.1 | `test_model_eval::TestEmbeddingQuality` |
| SOAP section completeness | All 4 sections non-empty | `test_model_eval::TestMedicalModelQuality` |
| ICD code validity | 100% in L00-L99 range | `test_model_eval::TestMedicalModelQuality` |
| Confidence score | 0.0 < score < 0.95 | `test_model_eval::TestMedicalModelQuality` |

## Gate 3: Safety (Pre-release)

| Check | Threshold | Test |
|---|---|---|
| Never prescribes medication | 0 prescription phrases | `test_regulatory::TestNeverPrescribes` |
| Never claims to be a doctor | 0 doctor-claim phrases | `test_regulatory::TestNeverClaimsDoctor` |
| Disclaimer always present | 100% of outputs | `test_regulatory::TestAlwaysIncludesDisclaimer` |
| Consent before image capture | 100% enforcement | `test_regulatory::TestImageConsentRequired` |
| Fitzpatrick equity | All 6 types handled | `test_bias_fairness::TestFitzpatrickTypeEquity` |
| Language equity | All supported languages | `test_bias_fairness::TestLanguageEquity` |
| Escalation fairness | No demographic bias | `test_bias_fairness::TestEscalationFairness` |

## Gate 4: Performance (Pre-release)

| Metric | Threshold | Test |
|---|---|---|
| Single embedding latency | < 100ms | `test_performance::TestEmbeddingPerformance` |
| Batch embedding (50) | < 500ms | `test_performance::TestEmbeddingPerformance` |
| Vector search (1000 items) | < 200ms | `test_performance::TestRetrievalPerformance` |
| Interview response | < 200ms | `test_performance::TestInterviewPerformance` |
| SOAP generation | < 300ms | `test_performance::TestSOAPPerformance` |
| 100 concurrent sessions | No errors | `test_performance::TestSessionScalability` |

## Gate 5: GenAI Regression (Pre-release)

| Check | Threshold | Test |
|---|---|---|
| Golden prompt stability | All golden tests pass | `test_genai_regression::TestGoldenPromptSuite` |
| Model response structure | All fields present | `test_genai_regression::TestModelResponseConsistency` |
| Escalation keywords stable | All trigger correctly | `test_genai_regression::TestEscalationRegression` |

## Promotion Process

1. **Developer** opens PR, CI runs Gate 1
2. **Nightly pipeline** runs Gate 2 + Gate 3
3. **Release candidate** triggers Gate 4 + Gate 5
4. All gates pass -> deploy to staging
5. Staging smoke test passes -> deploy to production
6. Any gate failure blocks promotion until resolved
