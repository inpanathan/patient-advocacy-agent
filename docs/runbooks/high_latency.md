# Runbook: High Prediction Latency

**Alert:** `high_prediction_latency`
**Severity:** WARNING
**Threshold:** p95 > 2000ms

## Symptoms
- Patient interactions feel slow or unresponsive
- TTS output delayed
- Session timeouts increasing

## Root Causes
1. **Model inference bottleneck** — GPU memory exhaustion or model loading issues
2. **RAG retrieval slow** — Vector index too large or not cached
3. **Network latency** — STT/TTS API calls timing out
4. **Resource contention** — Too many concurrent sessions

## Immediate Actions
1. Check GPU memory usage: `nvidia-smi`
2. Check RAG retrieval latency in metrics dashboard
3. Review active session count
4. Check if model is loaded in memory

## Resolution Steps
1. If GPU memory full: Restart the model service, reduce batch size
2. If RAG slow: Check vector index size, rebuild index, increase cache TTL
3. If network: Check STT/TTS service health, verify API keys
4. If contention: Scale horizontally, add rate limiting

## Escalation
If latency persists after above steps, escalate to the platform team.
