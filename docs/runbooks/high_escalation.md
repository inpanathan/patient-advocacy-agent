# Runbook: High Escalation Rate

**Alert:** `high_escalation_rate`
**Severity:** CRITICAL
**Threshold:** > 50% of sessions escalated

## Symptoms
- Unusually high proportion of cases flagged for immediate physician review
- Possible model drift or adversarial inputs

## Root Causes
1. **Model drift** — Underlying model generating more concerning assessments
2. **Data drift** — Input population has shifted
3. **Prompt injection** — Adversarial patients triggering escalation keywords
4. **Configuration error** — Escalation keywords too broad

## Immediate Actions
1. Review recent escalated sessions for patterns
2. Check model version — was it recently updated?
3. Review escalation keyword list for overly broad matches
4. Check data drift dashboard for population shifts

## Resolution Steps
1. If model drift: Roll back to previous model version
2. If data drift: Update baseline stats, re-evaluate thresholds
3. If adversarial: Add input sanitization, review red-team scenarios
4. If config: Narrow escalation keywords, require multiple keyword matches

## Escalation
Escalate to medical advisor and platform team immediately for CRITICAL alerts.
