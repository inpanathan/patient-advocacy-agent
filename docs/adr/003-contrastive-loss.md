# ADR-003: Contrastive Loss (NT-Xent) for Embedding Fine-Tuning

**Status:** Accepted
**Date:** 2026-02-18
**Context:** Need isotropic embeddings on the unit hypersphere for fair retrieval across skin types.

## Decision
Use NT-Xent (Normalized Temperature-scaled Cross-Entropy) contrastive loss for fine-tuning SigLIP-2 embeddings on SCIN data.

## Consequences
- Encourages isotropic embedding distribution (no cluster collapse)
- Temperature parameter controls hardness of negative mining
- Requires positive pairs from same diagnosis, negatives from different
- Margin variant available for additional separation
