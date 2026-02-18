# ADR-002: SCIN Database for RAG Reference

**Status:** Accepted
**Date:** 2026-02-18
**Context:** Need a dermatological reference dataset covering diverse skin tones.

## Decision
Use the Harvard SCIN (Skin Condition Image Network) database as the primary RAG knowledge base, indexed via SigLIP-2 embeddings.

## Consequences
- 2GB dataset requires efficient loading and indexing
- Covers Fitzpatrick types I-VI for equitable triage
- ICD-10 codes in L00-L99 dermatology range
- Requires quality checks and drift monitoring
