
from datetime import datetime, timezone

from app.models import (
    Project,
    ProjectItem,
    Handover,
    HandoverItem,
    EvidenceChunk,
    Document,
)


def _date_to_string(value):
    """Convert database dates to JSON-safe strings."""
    if value is None:
        return None

    if hasattr(value, "isoformat"):
        return value.isoformat()

    return str(value)


def generate_handover(db, handover_id: int):
    """
    Generate a structured, evidence-linked handover.

    Verified evidence is kept separate from pending/unverified evidence.
    This function does not use an LLM or invent missing project information.
    """

    # 1. Find the handover
    handover = (
        db.query(Handover)
        .filter(Handover.id == handover_id)
        .first()
    )

    if not handover:
        raise ValueError("Handover not found")

    # 2. Find the project
    project = (
        db.query(Project)
        .filter(Project.id == handover.project_id)
        .first()
    )

    if not project:
        raise ValueError("Project associated with this handover was not found")

    # 3. Get all project items
    project_items = (
        db.query(ProjectItem)
        .filter(ProjectItem.project_id == project.id)
        .order_by(ProjectItem.id)
        .all()
    )

    items_by_type = {}
    next_actions = []
    risks_and_blockers = []
    decisions = []
    structured_items = []

    for item in project_items:
        item_data = {
            "id": item.id,
            "type": item.item_type,
            "title": item.title,
            "description": item.description,
            "owner": item.owner,
            "status": item.status,
            "priority": item.priority,
            "due_date": _date_to_string(item.due_date),
            "confidence": item.confidence,
        }

        structured_items.append(item_data)

        item_type = (item.item_type or "other").lower()

        items_by_type.setdefault(item_type, []).append(item_data)

        if item_type == "decision":
            decisions.append(item_data)

        if "risk" in item_type or "blocker" in item_type:
            risks_and_blockers.append(item_data)

        if (item.status or "").lower() not in {
            "completed",
            "complete",
            "closed",
            "done",
        }:
            next_actions.append(item_data)

    # 4. Get evidence attached to this handover
    handover_items = (
        db.query(HandoverItem)
        .filter(HandoverItem.handover_id == handover.id)
        .order_by(HandoverItem.id)
        .all()
    )

    verified_evidence = []
    pending_evidence = []
    linked_project_item_ids = set()

    for handover_item in handover_items:
        project_item = None
        evidence = None
        document = None

        if handover_item.project_item_id:
            project_item = (
                db.query(ProjectItem)
                .filter(
                    ProjectItem.id == handover_item.project_item_id
                )
                .first()
            )

            if project_item:
                linked_project_item_ids.add(project_item.id)

        if handover_item.evidence_chunk_id:
            evidence = (
                db.query(EvidenceChunk)
                .filter(
                    EvidenceChunk.id == handover_item.evidence_chunk_id
                )
                .first()
            )

            if evidence:
                document = (
                    db.query(Document)
                    .filter(Document.id == evidence.document_id)
                    .first()
                )

        evidence_data = {
            "handover_item_id": handover_item.id,
            "project_item": (
                {
                    "id": project_item.id,
                    "title": project_item.title,
                    "type": project_item.item_type,
                }
                if project_item
                else None
            ),
            "evidence": (
                {
                    "id": evidence.id,
                    "document_id": evidence.document_id,
                    "filename": document.filename if document else None,
                    "page_number": evidence.page_number,
                    "content": evidence.content,
                }
                if evidence
                else None
            ),
            "notes": handover_item.notes,
            "verified": bool(handover_item.is_verified),
            "review_status": (
                "verified"
                if handover_item.is_verified
                else "pending_review"
            ),
        }

        if handover_item.is_verified:
            verified_evidence.append(evidence_data)
        else:
            pending_evidence.append(evidence_data)

    # 5. Identify project items without linked evidence
    items_without_evidence = [
        {
            "id": item.id,
            "title": item.title,
            "type": item.item_type,
        }
        for item in project_items
        if item.id not in linked_project_item_ids
    ]

    # 6. Build the final report
    report = {
        "report_type": "project_handover",
        "generated_at": datetime.now(timezone.utc).isoformat(),

        "handover": {
            "id": handover.id,
            "title": handover.title,
            "status": handover.status,
        },

        "project": {
            "id": project.id,
            "name": project.name,
            "description": project.description,
            "status": project.status,
        },

        "summary": {
            "total_project_items": len(project_items),
            "total_evidence_links": len(handover_items),
            "verified_evidence_count": len(verified_evidence),
            "pending_evidence_count": len(pending_evidence),
            "items_without_linked_evidence": len(items_without_evidence),
        },

        "project_items": structured_items,
        "items_by_type": items_by_type,
        "decisions": decisions,
        "risks_and_blockers": risks_and_blockers,
        "next_actions": next_actions,

        "evidence": {
            "verified": verified_evidence,
            "pending_review": pending_evidence,
        },

        "missing_information": {
            "project_items_without_linked_evidence": items_without_evidence,
        },

        "limitations": [
            "This report is generated from information stored in the project database.",
            "Pending evidence has not been approved by a human reviewer.",
            "Missing owners, due dates, and other fields are not inferred.",
            "Similarity scores are not treated as evidence approval.",
        ],
    }

    # 7. Save the generated report in the Handover JSON column
    handover.content = report
    db.commit()
    db.refresh(handover)

    return report
