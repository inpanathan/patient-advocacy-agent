# ADR-005: In-Memory Vector Index with ChromaDB Migration Path

**Status:** Accepted
**Date:** 2026-02-18
**Context:** Need nearest-neighbor search for RAG retrieval from SCIN embeddings.

## Decision
Implement an in-memory vector index using numpy for cosine similarity search. Plan migration to ChromaDB for production persistence.

## Consequences
- In-memory is fast and simple for development
- No persistence across restarts (acceptable for dev)
- ChromaDB migration path clear: same add/search interface
- Caching layer in RAGRetriever reduces redundant searches
