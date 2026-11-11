
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.database import SessionLocal
from app.models import Project, Document, EvidenceChunk
from app.services.semantic_search import search_evidence

router = APIRouter(
    prefix="/verification",
    tags=["Evidence Verification"]
)


class EvidenceSearchRequest(BaseModel):
    project_id: int = Field(gt=0)
    item_type: str = Field(min_length=2, max_length=50)
    title: str = Field(min_length=3, max_length=255)
    description: str = Field(default="", max_length=2000)
    top_k: int = Field(default=5, ge=1, le=10)


@router.post("/search")
def find_supporting_evidence(request: EvidenceSearchRequest):
    """
    Find evidence that may support a project item.

    Similarity indicates relevance, not factual verification.
    All returned evidence requires human review.
    """

    db = SessionLocal()

    try:
        # 1. Check whether the project exists
        project = db.query(Project).filter(
            Project.id == request.project_id
        ).first()

        if not project:
            raise HTTPException(
                status_code=404,
                detail="Project not found"
            )

        # 2. Build a search query from the project item
        query_parts = [
            request.item_type,
            request.title,
            request.description
        ]

        query = " ".join(
            part.strip()
            for part in query_parts
            if part and part.strip()
        )

        # 3. Retrieve relevant evidence
        results = search_evidence(
            query=query,
            project_id=request.project_id,
            top_k=request.top_k
        )

        verified_candidates = []

        # 4. Attach source document information
        for result in results:

            evidence = db.query(EvidenceChunk).filter(
                EvidenceChunk.id == result["evidence_id"]
            ).first()

            if not evidence:
                continue

            document = db.query(Document).filter(
                Document.id == evidence.document_id,
                Document.project_id == request.project_id
            ).first()

            if not document:
                continue

            similarity = result["similarity"]

            if similarity >= 0.55:
                match_strength = "strong"
            elif similarity >= 0.35:
                match_strength = "possible"
            else:
                match_strength = "weak"

            verified_candidates.append({
                "evidence_id": evidence.id,
                "document_id": document.id,
                "filename": document.filename,
                "page_number": evidence.page_number,
                "chunk_index": evidence.chunk_index,
                "content": evidence.content,
                "similarity": similarity,
                "match_strength": match_strength,
                "verification_status": "needs_review",
                "review_required": True
            })

        # 5. Return results
        return {
            "message": "Evidence search completed",
            "project_id": request.project_id,
            "item": {
                "item_type": request.item_type,
                "title": request.title
            },
            "total_candidates": len(verified_candidates),
            "verification_note": (
                "Similarity measures relevance only. "
                "It does not establish that a claim is true. "
                "Human verification is required."
            ),
            "results": verified_candidates
        }

    except HTTPException:
        raise

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=f"Evidence verification search failed: {str(error)}"
        )

    finally:
        db.close()
