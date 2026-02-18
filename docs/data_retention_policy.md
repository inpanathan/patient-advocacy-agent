# Data Retention and Deletion Policy

**Covers:** REQ-DAT-003, REQ-OBS-060

## Scope

This policy applies to all patient data processed by the Patient Advocacy Agent:
- Voice recordings (audio files from STT pipeline)
- Captured images (dermatological photos from WebRTC)
- Case histories (SOAP notes, ICD codes, physician reports)
- Session metadata (timestamps, language, device info)

## Retention Periods

| Data Type | Retention Period | Storage | Encryption |
|-----------|-----------------|---------|------------|
| Voice recordings | 72 hours | Temporary local storage | AES-256 at rest |
| Captured images | 30 days | Encrypted blob storage | AES-256 at rest |
| SOAP case histories | 1 year | Encrypted database | AES-256 at rest |
| Session metadata | 90 days | Application database | AES-256 at rest |
| Aggregated analytics | Indefinite (no PII) | Analytics store | N/A |
| Model training data (SCIN) | Indefinite (research data) | DVC-managed | At rest |

## Deletion Procedures

1. **Automated deletion:** A scheduled job runs daily to delete data past retention.
2. **Patient request:** Patients or authorized representatives can request deletion.
   Deletion completes within 48 hours of verified request.
3. **Audit trail:** Deletion events are logged (without PII) for compliance.

## PII/PHI Handling

- All patient identifiers are pseudonymized at ingestion.
- Logs never contain raw PII/PHI — all patient data is redacted before logging.
- Voice transcriptions are stored separately from speaker identity.
- Images are stored without filename-based patient identifiers.

## Access Controls

- Patient data access requires authenticated, authorized API calls.
- Access is logged with who, what, when, and why.
- Least-privilege principle: only services that need patient data can access it.

## Regulatory Compliance

This policy is provisional and must be reviewed against:
- Local medical data regulations in deployment countries
- HIPAA (if applicable to US-based physicians)
- GDPR (if applicable to EU data subjects)
