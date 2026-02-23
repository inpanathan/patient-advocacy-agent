# Demo Video Script — Patient Advocacy Agent

**Duration:** 3 minutes
**Format:** Screen recording with voiceover narration

---

## Scene 1: Problem Statement + Architecture (0:00 - 0:30)

### Visual
- Open on a title card: "Patient Advocacy Agent — Voice-Only Dermatological Triage"
- Transition to architecture diagram (Mermaid rendered) showing: Patient (voice) → STT → Interview Agent → MedSigLIP (image) → Qdrant RAG → MedGemma → SOAP Note → Doctor Portal
- Overlay key stats: "1 dermatologist per 1M people", "600M+ illiterate adults globally"

### Narration
"Hundreds of millions of people in the Global South lack access to dermatologists. Many are illiterate and cannot use text-based health applications. The Patient Advocacy Agent is a voice-only system that conducts dermatological triage interviews, captures skin images with explicit consent, and produces standardized SOAP notes for remote physicians — powered by MedGemma and MedSigLIP from Google's Health AI Developer Foundations."

---

## Scene 2: Patient Voice Session (0:30 - 1:30)

### Visual
- Open browser to http://localhost:5173 (patient interview page)
- Click "Start Session" → language detection activates
- System speaks greeting in detected language (Hindi demo)
- User responds with symptoms via microphone: "My arm has been itching for two weeks, there are red patches"
- System asks follow-up questions: location, duration, severity
- System asks: "May I take a photo of the affected area?" (consent gate shown)
- User grants consent → camera activates → image captured
- Show MedSigLIP processing indicator, RAG retrieval results appearing
- SOAP note generates on screen in real-time

### Narration
"The interview begins with automatic language detection. The agent conducts a structured clinical interview through speech — asking about symptoms, location, duration, and severity. Before capturing any image, it always asks for explicit consent. The captured image is embedded by MedSigLIP and matched against 2,175 cases in the Harvard SCIN database using Qdrant vector search. MedGemma then generates a complete SOAP note with ICD-10 codes."

---

## Scene 3: Doctor Portal (1:30 - 2:15)

### Visual
- Switch to doctor login (doctor1@test.com)
- Show case list with severity indicators
- Click into the case just created
- Show full SOAP note: Subjective, Objective, Assessment, Plan
- Highlight ICD codes, confidence score, similar cases panel
- Show "assigned doctor" field and case status workflow (open → in-review → resolved)

### Narration
"Remote physicians receive structured case histories in their portal. Each case includes a complete SOAP note with ICD-10 codes, a confidence score, and similar cases from the SCIN database for reference. Cases are automatically assigned to the least-loaded doctor. The physician can review, annotate, and resolve cases from anywhere."

---

## Scene 4: Monitoring Dashboard + Safety (2:15 - 2:45)

### Visual
- Navigate to http://localhost:8001/dashboard
- Show health overview panel (uptime, active sessions, model versions)
- Show safety metrics: 100% malignancy escalation rate, 0 prescription violations
- Show bias monitoring: Fitzpatrick type distribution, confidence parity across skin types
- Show vector space visualization (PCA scatter plot of SCIN embeddings)
- Briefly show log viewer with structured JSON logs (PII redacted)

### Narration
"The monitoring dashboard provides real-time visibility into system health, safety compliance, and fairness metrics. Malignancy escalation is enforced at one hundred percent — the system never misses a suspected cancer case. Bias metrics are tracked across all six Fitzpatrick skin types to ensure equitable performance. All patient data is PII-redacted in logs and encrypted at rest."

---

## Scene 5: Closing — Edge Deployment + Impact (2:45 - 3:00)

### Visual
- Return to architecture diagram
- Overlay: "Runs on RTX 3090 (MedGemma 4B at 4-bit)", "5 languages", "< 3 min per case"
- Show GitHub repo structure briefly
- End card: "Patient Advocacy Agent — Seeking professional medical help is always recommended"

### Narration
"The entire system runs locally on a single GPU. MedGemma 4B with QLoRA fine-tuning fits in under 5 gigabytes of VRAM. Five languages are supported today with more planned. Every interaction takes less than three minutes. And the system always reminds patients: seek professional medical help. Thank you."
