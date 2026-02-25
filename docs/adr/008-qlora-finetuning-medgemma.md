# ADR-008: QLoRA Fine-Tuning Strategy for MedGemma

## Status

Accepted

## Context

MedGemma 4B IT is used as the core medical LLM for SOAP note generation and
ICD-10 coding. While the base model performs well on general medical tasks,
fine-tuning on domain-specific dermatological data (SCIN) can improve:

1. SOAP note quality for skin conditions
2. ICD-10 code accuracy for dermatological diagnoses
3. Severity assessment calibration
4. Clinical language consistency

Full fine-tuning of a 4B parameter model requires multiple GPUs and significant
VRAM. QLoRA (Quantized Low-Rank Adaptation) enables fine-tuning on a single
consumer GPU (RTX 3090 with 24GB VRAM).

## Decision

Fine-tune MedGemma 4B IT using QLoRA on SCIN dermatology records converted to
instruction-tuning format.

### Configuration

| Parameter | Value | Rationale |
|-----------|-------|-----------|
| Quantization | NF4 (4-bit) | Reduces model to ~3GB VRAM |
| LoRA rank (r) | 16 | Good balance of capacity vs efficiency |
| LoRA alpha | 32 | 2x rank for stable training |
| Target modules | q_proj, v_proj, k_proj, o_proj | Full attention adaptation |
| Dropout | 0.05 | Mild regularization |
| Epochs | 3 | Sufficient for small dataset |
| Learning rate | 2e-4 | Standard for LoRA fine-tuning |
| Batch size | 4 (effective 16) | With gradient accumulation of 4 |
| Max sequence length | 1024 | Covers full SOAP notes |

### Training Data

- Source: ~2,175 SCIN records converted to instruction-tuning pairs
- Input: Patient presentation description (diagnosis, body location, severity, Fitzpatrick type)
- Output: Complete SOAP note with ICD codes and confidence score
- Split: 90% train / 10% validation
- Format: JSONL with Gemma chat template (`<start_of_turn>user`/`<start_of_turn>model`)

### VRAM Budget (RTX 3090, 24GB)

| Component | VRAM |
|-----------|------|
| MedGemma 4B at NF4 | ~3GB |
| LoRA adapters | ~2GB |
| Training overhead | ~5GB |
| **Total** | **~10GB** |

### Inference Integration

- LoRA adapters saved to `models/medgemma-lora-derm/adapter/`
- Config: `settings.llm.lora_adapter_path` points to adapter directory
- At inference time, adapters are loaded via `PeftModel.from_pretrained()` and merged
- Merging produces a single model with no inference-time overhead

### Pipeline

```bash
bash scripts/finetune_medgemma.sh          # Full: prep → train → eval
bash scripts/finetune_medgemma.sh --prep-only   # Data prep only
bash scripts/finetune_medgemma.sh --train-only   # Training only
bash scripts/finetune_medgemma.sh --eval-only    # Evaluation only
```

## Consequences

### Positive

- Improved SOAP quality on dermatological cases
- Domain-specific ICD-10 code suggestions
- Fits on a single consumer GPU (10GB VRAM)
- Adapters are small (~50MB) and easy to version/deploy
- Base model weights unchanged (adapters are additive)

### Negative

- Training requires GPU (1-2 hours on RTX 3090)
- Small training set (2,175 records) limits generalization
- Risk of overfitting on SCIN-specific diagnoses
- Requires `peft`, `bitsandbytes`, `trl`, `datasets` dependencies

### Neutral

- LoRA adapters can be swapped without reloading the base model
- Evaluation pipeline compares base vs fine-tuned on held-out data
- Adapter path is optional — system works without fine-tuning

**Provisional — awaiting stakeholder confirmation on fine-tuning strategy.**
