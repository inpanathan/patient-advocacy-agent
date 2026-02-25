# ADR-007: MedSigLIP-448 over SigLIP-2 for Medical Image Embeddings

## Status

Accepted

## Context

The Patient Advocacy Agent uses multimodal embeddings for RAG retrieval from the
Harvard SCIN dermatological database. The initial implementation used SigLIP-2
(`google/siglip-so400m-patch14-384`), a general-purpose vision-language model.

Google's Health AI Developer Foundations (HAI-DEF) program released MedSigLIP-448
(`google/medsiglip-448`), a variant of SigLIP fine-tuned on medical images across
four domains: dermatology, chest X-rays, pathology, and ophthalmology. Using
HAI-DEF certified models aligns with the MedGemma Impact Challenge requirements
and improves retrieval quality for medical use cases.

## Decision

Replace SigLIP-2 with MedSigLIP-448 as the embedding model for SCIN image
indexing and RAG retrieval.

### Changes

- `EmbeddingSettings.model_id` default: `google/medsiglip-448`
- `EmbeddingSettings.model_path` default: `models/medsiglip`
- `configs/dev.yaml`: explicit `embedding.model_id: google/medsiglip-448`
- Existing Qdrant collection must be dropped and re-indexed (`bash scripts/qdrant_index.sh --force`)
- Embedding dimension remains 1152 (same architecture base: SigLIP-SO400M)

### Why MedSigLIP over SigLIP-2

| Criterion | SigLIP-2 | MedSigLIP-448 |
|-----------|----------|---------------|
| Domain training | General web images | Derm, CXR, pathology, ophthalmology |
| HAI-DEF certified | No | Yes |
| Resolution | 384x384 | 448x448 |
| Parameters | ~400M | ~400M |
| Architecture | SiglipModel | SiglipModel (same) |
| API compatibility | AutoModel/AutoProcessor | AutoModel/AutoProcessor (same) |

## Consequences

### Positive

- Better retrieval quality for dermatological images (domain-specific training)
- HAI-DEF alignment for MedGemma Impact Challenge submission
- Higher resolution input (448 vs 384) captures more skin detail
- Drop-in replacement: same HuggingFace API, same embedding dimension

### Negative

- Requires re-indexing all SCIN embeddings (~5 min on GPU, ~30 min on CPU)
- MedSigLIP is a gated model requiring HuggingFace login and license acceptance
- Slightly higher VRAM usage due to larger input resolution

### Neutral

- No code changes needed in `local_embedding.py` (same AutoModel interface)
- Embedding dimension unchanged at 1152

**Provisional — awaiting stakeholder confirmation on medical embedding model choice.**
