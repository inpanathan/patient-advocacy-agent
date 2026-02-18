# Runbook: Low Prediction Confidence

**Alert:** `low_prediction_confidence`
**Severity:** WARNING
**Threshold:** Average confidence < 0.3

## Symptoms
- SOAP notes with low confidence scores
- Vague or generic assessments
- Increased "unknown" ICD codes

## Root Causes
1. **Out-of-distribution inputs** — Conditions not well-represented in training data
2. **Poor RAG retrieval** — Vector index not returning relevant matches
3. **Transcript quality** — STT errors producing garbled input
4. **Model degradation** — Model weights corrupted or API issues

## Immediate Actions
1. Review recent low-confidence predictions
2. Check STT transcription accuracy
3. Check RAG retrieval scores for these sessions
4. Verify model is responding correctly

## Resolution Steps
1. If OOD: Expand training data, add cases for underrepresented conditions
2. If RAG: Rebuild vector index, check embedding model health
3. If STT: Check audio quality, verify language detection
4. If model: Restart model service, verify API connectivity

## Escalation
If confidence remains low after above steps, escalate to ML team.
