
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models import (
    Handover,
    HandoverItem,
    ProjectItem,
    EvidenceChunk,
    Document,
)

router = APIRouter(
    prefix="/review",
    tags=["Human Evidence Review"]
)


# Request schema: attach evidence to a handover
class AttachEvidenceRequest(BaseModel):
    project_item_id: int = Field(gt=0)
    evidence_chunk_id: int = Field(gt=0)
    notes: Optional[str] = Field(default=None, max_length=2000)


# Request schema: review evidence
class ReviewDecisionRequest(BaseModel):
    is_verified: bool
    notes: Optional[str] = Field(default=None, max_length=2000)


# 1. Attach evidence to a handover item
@router.post("/handovers/{handover_id}/items")
def attach_evidence(
    handover_id: int,
    request: AttachEvidenceRequest
):
    db: Session = SessionLocal()

    try:
        # Check handover
        handover = db.query(Handover).filter(
            Handover.id == handover_id
        ).first()

        if not handover:
            raise HTTPException(
                status_code=404,
                detail="Handover not found"
            )

        # Check project item
        project_item = db.query(ProjectItem).filter(
            ProjectItem.id == request.project_item_id
        ).first()

        if not project_item:
            raise HTTPException(
                status_code=404,
                detail="Project item not found"
            )

        # Check evidence and its source document
        evidence = (
            db.query(EvidenceChunk)
            .join(
                Document,
                EvidenceChunk.document_id == Document.id
            )
            .filter(
                EvidenceChunk.id == request.evidence_chunk_id,
                Document.project_id == handover.project_id
            )
            .first()
        )

        if not evidence:
            raise HTTPException(
                status_code=404,
                detail="Evidence not found in this project's documents"
            )

        # Ensure the project item belongs to the handover's project
        if project_item.project_id != handover.project_id:
            raise HTTPException(
                status_code=400,
                detail="Project item does not belong to this handover's project"
            )

        # Prevent duplicate evidence attachment
        existing = db.query(HandoverItem).filter(
            HandoverItem.handover_id == handover_id,
            HandoverItem.project_item_id == request.project_item_id,
            HandoverItem.evidence_chunk_id == request.evidence_chunk_id
        ).first()

        if existing:
            raise HTTPException(
                status_code=409,
                detail="This evidence is already attached to this item"
            )

        handover_item = HandoverItem(
            handover_id=handover_id,
            project_item_id=request.project_item_id,
            evidence_chunk_id=request.evidence_chunk_id,
            notes=request.notes,
            is_verified=False
        )

        db.add(handover_item)
        db.commit()
        db.refresh(handover_item)

        return {
            "message": "Evidence attached successfully",
            "handover_item_id": handover_item.id,
            "handover_id": handover_item.handover_id,
            "project_item_id": handover_item.project_item_id,
            "evidence_chunk_id": handover_item.evidence_chunk_id,
            "is_verified": handover_item.is_verified,
            "review_status": "pending"
        }

    except HTTPException:
        db.rollback()
        raise

    except Exception as error:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Could not attach evidence: {str(error)}"
        )

    finally:
        db.close()


# 2. View all items and evidence in a handover
@router.get("/handovers/{handover_id}/items")
def get_handover_review_items(handover_id: int):

    db: Session = SessionLocal()

    try:
        handover = db.query(Handover).filter(
            Handover.id == handover_id
        ).first()

        if not handover:
            raise HTTPException(
                status_code=404,
                detail="Handover not found"
            )

        items = db.query(HandoverItem).filter(
            HandoverItem.handover_id == handover_id
        ).all()

        results = []

        for item in items:

            project_item = db.query(ProjectItem).filter(
                ProjectItem.id == item.project_item_id
            ).first()

            evidence_data = (
                db.query(EvidenceChunk, Document)
                .join(
                    Document,
                    EvidenceChunk.document_id == Document.id
                )
                .filter(
                    EvidenceChunk.id == item.evidence_chunk_id
                )
                .first()
            )

            evidence = evidence_data[0] if evidence_data else None
            document = evidence_data[1] if evidence_data else None

            results.append({
                "handover_item_id": item.id,
                "project_item": {
                    "id": project_item.id,
                    "type": project_item.item_type,
                    "title": project_item.title,
                    "description": project_item.description
                } if project_item else None,
                "evidence": {
                    "id": evidence.id,
                    "document_id": document.id,
                    "filename": document.filename,
                    "page_number": evidence.page_number,
                    "content": evidence.content
                } if evidence and document else None,
                "notes": item.notes,
                "is_verified": item.is_verified,
                "review_status": (
                    "verified" if item.is_verified else "not_verified"
                )
            })

        return {
            "handover_id": handover_id,
            "total_items": len(results),
            "verified_items": sum(
                1 for item in results if item["is_verified"]
            ),
            "items": results
        }

    except HTTPException:
        raise

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=f"Could not retrieve review items: {str(error)}"
        )

    finally:
        db.close()


# 3. Approve or mark evidence as not verified
@router.patch("/items/{handover_item_id}/decision")
def review_evidence(
    handover_item_id: int,
    request: ReviewDecisionRequest
):

    db: Session = SessionLocal()

    try:
        item = db.query(HandoverItem).filter(
            HandoverItem.id == handover_item_id
        ).first()

        if not item:
            raise HTTPException(
                status_code=404,
                detail="Handover item not found"
            )

        item.is_verified = request.is_verified

        if request.notes is not None:
            item.notes = request.notes

        db.commit()
        db.refresh(item)

        return {
            "message": (
                "Evidence approved successfully"
                if item.is_verified
                else "Evidence marked as not verified"
            ),
            "handover_item_id": item.id,
            "is_verified": item.is_verified,
            "review_status": (
                "verified" if item.is_verified else "not_verified"
            ),
            "notes": item.notes
        }

    except HTTPException:
        db.rollback()
        raise

    except Exception as error:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Could not update review decision: {str(error)}"
        )

    finally:
        db.close()
