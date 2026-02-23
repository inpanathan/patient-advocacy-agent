# ADR-005: Vector Index — Numpy to Qdrant Migration

**Status:** Superseded (was: Accepted)
**Date:** 2026-02-18, updated 2026-02-22
**Context:** Need nearest-neighbor search for RAG retrieval from SCIN embeddings.

## Original Decision (2026-02-18)
Implement an in-memory vector index using numpy for cosine similarity search. Plan migration to ChromaDB for production persistence.

## Revised Decision (2026-02-22)
Migrate from the in-memory numpy `VectorIndex` to **Qdrant** as the persistent
vector store backend. The numpy backend is retained as a fallback selectable via
`settings.vector_store.backend = "numpy"`.

### Rationale
- **Startup time**: Re-embedding ~4,776 SCIN images on every server restart took
  ~5 minutes. Qdrant persists embeddings across restarts, reducing startup to seconds.
- **Production-readiness**: Qdrant provides built-in HNSW indexing, horizontal scaling,
  filtering, and snapshot/backup capabilities.
- **Qdrant over ChromaDB**: Qdrant was already running in the dev environment. It has
  better gRPC support, more mature clustering, and a clearer path to distributed
  deployment. This is a provisional choice — see ADR principles.

### Implementation
- `src/models/vector_store.py` — `VectorIndexProtocol`, `QdrantVectorIndex`, factory
- `settings.vector_store.backend` — `"numpy"` (default) or `"qdrant"`
- `main.py` lifespan skips SCIN re-indexing when Qdrant already has data
- `index_embeddings.py` CLI gains `--force-reindex` for collection recreation
- Dashboard backward-compatible via `_embeddings`/`_metadata` properties that scroll from Qdrant

## Consequences
- Server startup drops from ~5 min to ~2 sec when Qdrant has data
- Qdrant becomes a runtime dependency (Docker container or cloud service)
- numpy fallback preserved for testing and environments without Qdrant
- Caching layer in RAGRetriever still reduces redundant searches

**Provisional — awaiting stakeholder confirmation on Qdrant vs other options.**
