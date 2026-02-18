# Product Requirements Document

**Patient Advocacy Agent — PRD/SRS Hybrid**

## 1. User Goals

### Primary User: Patient
- **Goal**: Get preliminary triage assessment for a skin condition
- **Context**: Illiterate, speaks local language, has phone with camera
- **Interaction**: Voice-only, with optional image capture via consent

### Secondary User: Physician
- **Goal**: Receive structured case history for remote review
- **Context**: At a healthcare facility, reviews SOAP notes and images
- **Interaction**: Reads CASE-{id} reports with ICD codes

## 2. Functional Requirements

### Voice Interaction
- System greets patient and identifies language
- Conducts interview via voice Q&A
- Extracts symptoms through conversational flow
- Generates spoken explanation of assessment

### Image Capture
- Requests explicit verbal consent before camera activation
- Captures image of affected area
- Embeds image for RAG retrieval
- Never captures without consent

### Medical Assessment
- Generates SOAP note from transcript + image + RAG context
- Suggests ICD-10 codes (L00-L99 dermatology range)
- Flags concerning cases for immediate physician review
- Never prescribes medication or claims to be a doctor

### Case History
- Formats structured report for physician review
- Includes SOAP note, ICD codes, confidence, escalation status
- Always includes disclaimer

## 3. Quality Attributes

| Attribute | Target |
|---|---|
| Response latency | < 2 seconds per turn |
| Concurrent sessions | 100+ |
| Availability | 99.5% |
| Fitzpatrick equity | Equal quality across all 6 types |
| Language support | Hindi, Bengali, Tamil, Swahili, English, Spanish |
| Escalation recall | 100% (never miss a malignancy) |
| PII protection | Zero leakage in logs |

## 4. Acceptance Criteria

- [ ] Patient can complete full triage in < 10 minutes
- [ ] SOAP note has all 4 sections populated
- [ ] ICD codes are in valid dermatology range
- [ ] Disclaimer present in all patient-facing output
- [ ] Escalation triggers for all malignancy keywords
- [ ] No prescription language in any output
- [ ] Consent always requested before image capture
- [ ] Case history delivered to physician in structured format

## 5. Dependencies

| Dependency | Status | Fallback |
|---|---|---|
| MedGemma API | External service | Mock implementation |
| SigLIP-2 model | External model | Mock embedding (SHA-256 based) |
| Whisper STT | External service | Mock transcription |
| TTS service | External service | Mock audio bytes |
| SCIN database | External dataset | Sample fixture data |
| ChromaDB | External service | In-memory vector index |
