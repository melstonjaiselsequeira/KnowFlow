
from io import BytesIO
from xml.sax.saxutils import escape

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    KeepTogether,
)

from app.database import get_db
from app.models import Handover
from app.services.handover_generator import generate_handover

router = APIRouter(
    prefix="/handovers",
    tags=["Handovers"],
)


@router.post("/{handover_id}/generate")
def generate_handover_report(
    handover_id: int,
    db: Session = Depends(get_db),
):
    try:
        report = generate_handover(db, handover_id)

        return {
            "message": "Handover report generated successfully",
            "handover_id": handover_id,
            "report": report,
        }

    except ValueError as error:
        raise HTTPException(status_code=404, detail=str(error))

    except Exception as error:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate handover: {str(error)}",
        )


def safe_text(value):
    """Escape source text before adding it to a ReportLab paragraph."""
    if value is None or value == "":
        return "Not provided"

    return escape(str(value)).replace("\n", "<br/>")


def add_section(story, styles, heading, content):
    story.append(Paragraph(heading, styles["Heading2"]))
    story.append(Spacer(1, 5))

    if not content:
        story.append(Paragraph("No records available.", styles["BodyText"]))
    else:
        for item in content:
            title = safe_text(item.get("title"))
            item_type = safe_text(item.get("type"))
            description = safe_text(item.get("description"))
            owner = safe_text(item.get("owner"))
            status = safe_text(item.get("status"))

            block = [
                Paragraph(f"<b>{title}</b>", styles["BodyText"]),
                Paragraph(
                    f"Type: {item_type} | Status: {status}",
                    styles["SmallText"],
                ),
                Paragraph(f"Description: {description}", styles["SmallText"]),
                Paragraph(f"Owner: {owner}", styles["SmallText"]),
                Spacer(1, 8),
            ]
            story.append(KeepTogether(block))


@router.get("/{handover_id}/pdf")
def download_handover_pdf(
    handover_id: int,
    db: Session = Depends(get_db),
):
    handover = (
        db.query(Handover)
        .filter(Handover.id == handover_id)
        .first()
    )

    if not handover:
        raise HTTPException(status_code=404, detail="Handover not found")

    report = handover.content

    if not report:
        raise HTTPException(
            status_code=400,
            detail="Generate the handover JSON report before downloading the PDF.",
        )

    if not isinstance(report, dict):
        raise HTTPException(
            status_code=500,
            detail="Saved handover report has an unexpected format.",
        )

    buffer = BytesIO()

    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=18 * mm,
        leftMargin=18 * mm,
        topMargin=18 * mm,
        bottomMargin=18 * mm,
        title="KnowFlow Project Handover",
        author="KnowFlow",
    )

    styles = getSampleStyleSheet()

    styles.add(ParagraphStyle(
        name="ReportTitle",
        parent=styles["Title"],
        alignment=TA_CENTER,
        textColor=colors.HexColor("#17365D"),
        fontSize=21,
        spaceAfter=12,
    ))

    styles.add(ParagraphStyle(
        name="SmallText",
        parent=styles["BodyText"],
        fontSize=8,
        leading=11,
    ))

    story = []

    project = report.get("project", {})
    summary = report.get("summary", {})
    handover_info = report.get("handover", {})
    evidence = report.get("evidence", {})

    story.append(Paragraph("KNOWFLOW", styles["ReportTitle"]))
    story.append(Paragraph("PROJECT KNOWLEDGE HANDOVER REPORT", styles["Heading2"]))
    story.append(Spacer(1, 12))

    story.append(Paragraph(
        f"<b>Project:</b> {safe_text(project.get('name'))}",
        styles["BodyText"],
    ))
    story.append(Paragraph(
        f"<b>Handover:</b> {safe_text(handover_info.get('title'))}",
        styles["BodyText"],
    ))
    story.append(Paragraph(
        f"<b>Project status:</b> {safe_text(project.get('status'))}",
        styles["BodyText"],
    ))
    story.append(Paragraph(
        f"<b>Generated:</b> {safe_text(report.get('generated_at'))}",
        styles["SmallText"],
    ))
    story.append(Spacer(1, 15))

    story.append(Paragraph("1. Executive Summary", styles["Heading1"]))

    story.append(Paragraph(
        safe_text(project.get("description")),
        styles["BodyText"],
    ))
    story.append(Spacer(1, 10))

    summary_data = [
        ["Metric", "Count"],
        ["Project items", str(summary.get("total_project_items", 0))],
        ["Evidence links", str(summary.get("total_evidence_links", 0))],
        ["Verified evidence", str(summary.get("verified_evidence_count", 0))],
        ["Pending evidence", str(summary.get("pending_evidence_count", 0))],
        ["Items without evidence", str(summary.get("items_without_linked_evidence", 0))],
    ]

    summary_table = Table(summary_data, colWidths=[110 * mm, 45 * mm])
    summary_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#17365D")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("PADDING", (0, 0), (-1, -1), 7),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))
    story.append(summary_table)
    story.append(Spacer(1, 15))

    story.append(Paragraph("2. Project Decisions", styles["Heading1"]))
    add_section(story, styles, "Decisions", report.get("decisions", []))

    story.append(Paragraph("3. Risks and Blockers", styles["Heading1"]))
    add_section(story, styles, "Identified Risks", report.get("risks_and_blockers", []))

    story.append(Paragraph("4. Next Actions", styles["Heading1"]))
    add_section(story, styles, "Outstanding Project Items", report.get("next_actions", []))

    story.append(Paragraph("5. Evidence and Verification", styles["Heading1"]))

    for heading, evidence_list in [
        ("Human-verified evidence", evidence.get("verified", [])),
        ("Pending review evidence", evidence.get("pending_review", [])),
    ]:
        story.append(Paragraph(heading, styles["Heading2"]))

        if not evidence_list:
            story.append(Paragraph("No records available.", styles["BodyText"]))

        for entry in evidence_list:
            source = entry.get("evidence") or {}
            linked_item = entry.get("project_item") or {}

            story.append(Paragraph(
                f"<b>Project item:</b> {safe_text(linked_item.get('title'))}",
                styles["BodyText"],
            ))
            story.append(Paragraph(
                f"<b>Source:</b> {safe_text(source.get('filename'))}",
                styles["SmallText"],
            ))
            story.append(Paragraph(
                f"<b>Page:</b> {safe_text(source.get('page_number'))}",
                styles["SmallText"],
            ))
            story.append(Paragraph(
                f"<b>Review status:</b> {safe_text(entry.get('review_status'))}",
                styles["SmallText"],
            ))
            story.append(Paragraph(
                f"<b>Reviewer notes:</b> {safe_text(entry.get('notes'))}",
                styles["SmallText"],
            ))
            story.append(Spacer(1, 8))

    missing = report.get("missing_information", {})
    missing_items = missing.get("project_items_without_linked_evidence", [])

    story.append(Paragraph("6. Missing Information", styles["Heading1"]))

    if missing_items:
        for item in missing_items:
            story.append(Paragraph(
                safe_text(item.get("title")),
                styles["BodyText"],
            ))
    else:
        story.append(Paragraph(
            "No project items are currently missing linked evidence.",
            styles["BodyText"],
        ))

    story.append(Spacer(1, 12))
    story.append(Paragraph("7. Report Limitations", styles["Heading1"]))

    for limitation in report.get("limitations", []):
        story.append(Paragraph(
            f"- {safe_text(limitation)}",
            styles["SmallText"],
        ))
        story.append(Spacer(1, 4))

    doc.build(story)
    buffer.seek(0)

    filename = f"KnowFlow_Handover_{handover_id}.pdf"

    return StreamingResponse(
        buffer,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"'
        },
    )
