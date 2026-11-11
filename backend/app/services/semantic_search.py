
import numpy as np

from app.database import SessionLocal
from app.models import EvidenceChunk, Document
from app.services.embedding_service import generate_embedding


def cosine_similarity(vector_a, vector_b):
    a = np.array(vector_a, dtype=float)
    b = np.array(vector_b, dtype=float)

    denominator = np.linalg.norm(a) * np.linalg.norm(b)

    if denominator == 0:
        return 0.0

    return float(np.dot(a, b) / denominator)


def search_evidence(query: str, project_id: int, top_k: int = 5):
    db = SessionLocal()

    try:
        query_embedding = generate_embedding(query)

        evidence_chunks = (
            db.query(EvidenceChunk)
            .join(Document, EvidenceChunk.document_id == Document.id)
            .filter(Document.project_id == project_id)
            .all()
        )

        results = []

        for chunk in evidence_chunks:
            metadata = chunk.metadata_json or {}
            stored_embedding = metadata.get("embedding")

            if not stored_embedding:
                continue

            similarity = cosine_similarity(
                query_embedding,
                stored_embedding
            )

            results.append({
                "evidence_id": chunk.id,
                "document_id": chunk.document_id,
                "page_number": chunk.page_number,
                "content": chunk.content,
                "similarity": round(similarity, 4)
            })

        # Sort by relevance
        results.sort(
            key=lambda item: item["similarity"],
            reverse=True
        )

        # Initial relevance threshold.
        # This value will be calibrated using more test documents.
        MIN_SIMILARITY = 0.25

        relevant_results = [
            result for result in results
            if result["similarity"] >= MIN_SIMILARITY
        ]

        return relevant_results[:top_k]

    finally:
        db.close()
