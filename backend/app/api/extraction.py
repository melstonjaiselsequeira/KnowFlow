
import re

from fastapi import APIRouter, HTTPException
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models import Document, EvidenceChunk
from app.services.document_extractor import extract_document_pages
from app.services.embedding_service import generate_embeddings

router = APIRouter(
    prefix="/extraction",
    tags=["Document Extraction"]
)


def split_text_into_chunks(text: str, max_chars: int = 1500) -> list:
    """
    Split text using paragraph and sentence boundaries.
    Hard-split only when a single sentence exceeds max_chars.
    """

    paragraphs = [
        re.sub(r"\s+", " ", paragraph).strip()
        for paragraph in re.split(r"\n\s*\n", text)
        if paragraph.strip()
    ]

    units = []

    for paragraph in paragraphs:

        if len(paragraph) <= max_chars:
            units.append((paragraph, "\n\n"))
            continue

        # Split long paragraphs into sentences
        sentences = re.split(r"(?<=[.!?])\s+", paragraph)

        for sentence in sentences:
            sentence = sentence.strip()

            if not sentence:
                continue

            # Handle exceptionally long sentences
            if len(sentence) > max_chars:
                for start in range(0, len(sentence), max_chars):
                    units.append((
                        sentence[start:start + max_chars],
                        " "
                    ))
            else:
                units.append((sentence, " "))

    chunks = []
    current_chunk = ""

    for unit, separator in units:

        if not current_chunk:
            current_chunk = unit

        elif len(current_chunk) + len(separator) + len(unit) <= max_chars:
            current_chunk += separator + unit

        else:
            chunks.append(current_chunk)
            current_chunk = unit

    if current_chunk:
        chunks.append(current_chunk)

    return chunks


@router.post("/{document_id}")
def extract_document_text(document_id: int):

    db: Session = SessionLocal()

    try:
        # 1. Find document
        document = db.query(Document).filter(
            Document.id == document_id
        ).first()

        if not document:
            raise HTTPException(
                status_code=404,
                detail="Document not found"
            )

        if not document.file_path:
            raise HTTPException(
                status_code=400,
                detail="Document file path is missing"
            )

        # 2. Extract page-aware content
        pages = extract_document_pages(document.file_path)

        if not pages:
            raise HTTPException(
                status_code=422,
                detail="No extractable text found."
            )

        # 3. Generate intelligent evidence chunks
        evidence_records = []
        total_characters = 0

        for page in pages:

            page_text = page["text"]
            page_number = page["page_number"]

            total_characters += len(page_text)

            chunks = split_text_into_chunks(
                page_text,
                max_chars=1500
            )

            for chunk in chunks:

                if not chunk.strip():
                    continue

                evidence_records.append(
                    EvidenceChunk(
                        document_id=document.id,
                        content=chunk,
                        page_number=page_number,
                        chunk_index=len(evidence_records),
                        metadata_json={
                            "source_filename": document.filename,
                            "extraction_method": "document_extractor",
                            "chunking_strategy": "sentence_paragraph_aware",
                            "max_chunk_size": 1500
                        }
                    )
                )

        if not evidence_records:
            raise HTTPException(
                status_code=422,
                detail="No evidence chunks could be generated."
            )


        # 4. Generate embeddings for all evidence chunks
        chunk_texts = [ record.content for record in evidence_records]
        embeddings = generate_embeddings(chunk_texts)

        # 5. Attach embeddings to evidence metadata
        for record, embedding in zip(evidence_records, embeddings):
            record.metadata_json = {
            **(record.metadata_json or {}),
                "embedding": embedding,
                "embedding_model": "all-MiniLM-L6-v2",
                "embedding_dimensions": len(embedding)
            }

        # 6. Replace previous evidence for this document
        db.query(EvidenceChunk).filter(
            EvidenceChunk.document_id == document.id    
        ).delete(synchronize_session=False)

        # 7. Save evidence and embeddings
        db.add_all(evidence_records)

        document.processing_status = "extracted"

        db.commit()

        return {
            "message": "Document extracted successfully",
            "document_id": document.id,
            "filename": document.filename,
            "total_characters": total_characters,
            "total_chunks": len(evidence_records),
            "page_count": len(pages),
            "chunking_strategy": "sentence_paragraph_aware",
            "status": document.processing_status
        }

    except HTTPException:
        db.rollback()
        raise

    except Exception as error:
        db.rollback()

        raise HTTPException(
            status_code=500,
            detail=f"Extraction failed: {str(error)}"
        )

    finally:
        db.close()
